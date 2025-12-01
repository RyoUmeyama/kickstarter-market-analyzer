#!/usr/bin/env python3
"""
レポート生成モジュール
テンプレート + OpenAI API対応
ウェブ検索による実在データ取得機能付き
"""

import os
from openai import OpenAI
from market_search import MarketSearcher


class ReportGenerator:
    """レポート生成クラス"""

    def __init__(self, api_key=None, model='gpt-4o-mini'):
        """
        Args:
            api_key (str, optional): OpenAI API key
            model (str, optional): モデル名（デフォルト: gpt-4o-mini）
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        # API keyがある場合のみOpenAIクライアントを初期化
        if self.api_key and self.api_key != 'your-openai-api-key-here':
            self.client = OpenAI(api_key=self.api_key)
            self.api_available = True
            # 市場検索クライアントを初期化
            self.market_searcher = MarketSearcher(api_key=self.api_key, model=self.model)
        else:
            self.client = None
            self.api_available = False
            self.market_searcher = None

    def generate_report(self, template, kickstarter_url, product_name='', common_prompt=''):
        """
        テンプレートに基づいてレポートを生成

        仕様:
        - A1（en_subject）とB1（jp_subject）はGOOGLETRANSLATE関数で連動
        - A2（en_body）とB2（jp_body）もGOOGLETRANSLATE関数で連動
        - A3（プロンプト、日本語）がある場合のみOpenAI APIを使用
          → 英語でレポートを生成 → Google Sheetsで日本語に翻訳

        Args:
            template (dict): テンプレート設定
                {
                    'jp_subject': 日本語件名（GOOGLETRANSLATE関数）,
                    'en_subject': 英語件名,
                    'jp_body': 日本語本文（GOOGLETRANSLATE関数）,
                    'en_body': 英語本文,
                    'jp_prompt': （未使用、B3は空のはず）,
                    'en_prompt': A3のプロンプト（日本語で記載）
                }
            kickstarter_url (str): Kickstarter URL
            product_name (str, optional): 製品名/メーカー名
            common_prompt (str, optional): 共通プロンプト（設定シートから読み込み）

        Returns:
            dict: 生成されたレポート
                {
                    'jp_subject': 日本語件名（GOOGLETRANSLATE関数の結果）,
                    'en_subject': 英語件名,
                    'jp_body': 日本語本文（GOOGLETRANSLATE関数の結果 or 空文字列）,
                    'en_body': 英語本文
                }
        """
        # 件名のプレースホルダーを置換（GOOGLETRANSLATE関数の結果がそのまま入っている）
        en_subject = self._replace_placeholders(
            template['en_subject'],
            kickstarter_url,
            product_name
        )
        jp_subject = self._replace_placeholders(
            template['jp_subject'],
            kickstarter_url,
            product_name
        )

        # A3（en_prompt）にプロンプトがあるかチェック
        prompt = template.get('en_prompt', '')

        if not prompt or not prompt.strip():
            # プロンプトがない場合: テンプレートの本文をそのまま使用
            en_body = self._replace_placeholders(
                template['en_body'],
                kickstarter_url,
                product_name
            )
            jp_body = self._replace_placeholders(
                template['jp_body'],
                kickstarter_url,
                product_name
            )

            # プロンプトなしの場合もマークダウンリンクをクリーンアップ
            en_body = self._clean_generated_body(en_body)
            jp_body = self._clean_generated_body(jp_body)
        else:
            # プロンプトがある場合: A2の本文テンプレート + A3のプロンプトをOpenAI APIに投げる
            # → 完全な英語本文（レポート込み）を生成
            en_body = self._generate_from_prompt(
                prompt,
                template['en_body'],  # A2の本文テンプレート
                kickstarter_url,
                product_name,
                common_prompt  # 共通プロンプトを追加
            )
            # 日本語本文は空文字列（Google SheetsのGOOGLETRANSLATE関数で翻訳）
            jp_body = ''

        return {
            'jp_subject': jp_subject,
            'en_subject': en_subject,
            'jp_body': jp_body,
            'en_body': en_body
        }

    def _generate_from_prompt(self, prompt, body_template, kickstarter_url, product_name, common_prompt=''):
        """
        日本語プロンプト + 本文テンプレートからOpenAI APIで完全な英語本文を生成

        Args:
            prompt (str): プロンプト（日本語、A3）
            body_template (str): 本文テンプレート（英語、A2）
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名
            common_prompt (str, optional): 共通プロンプト（設定シートから読み込み）

        Returns:
            str: 生成された完全な英語本文（レポート込み）
        """
        if not self.api_available:
            print(f"  ⚠️  OpenAI API key not configured. Cannot generate report from prompt.")
            return "Error: OpenAI API key not configured"

        try:
            # プロンプトと本文テンプレートのプレースホルダーを置換
            processed_prompt = self._replace_placeholders(prompt, kickstarter_url, product_name)
            processed_body_template = self._replace_placeholders(body_template, kickstarter_url, product_name)

            # 市場調査：類似製品を検索
            market_research_data = ""
            if self.market_searcher:
                search_results = self.market_searcher.search_similar_products(kickstarter_url, product_name)
                market_research_data = self.market_searcher.format_for_prompt(search_results)

            # プロンプト + 本文テンプレート + 市場調査データを組み合わせる
            combined_prompt = f"""あなたの仕事は、以下の【メール本文テンプレート】をベースにして、【分析指示】に従ってレポート部分を生成し、完成したメール本文を出力することです。

=== 最重要ルール ===
1. 【メール本文テンプレート】の文章構造・文面を必ず維持すること
2. テンプレート内の {{{{レポート}}}} または {{{{レポ―ト}}}} の部分のみを、生成したレポートで置き換えること
3. テンプレートの挨拶文、署名、その他の部分は一切変更しないこと
4. テンプレートにない文章を勝手に追加しないこと

【メール本文テンプレート（これをベースにする）】
{processed_body_template}

【分析指示（レポート生成用）】
{processed_prompt}

{market_research_data}

=== 出力ルール ===
- テンプレートの構造を完全に保持し、{{{{レポート}}}} 部分のみを置き換える
- 出力は英語のみ（ENGLISH ONLY）
- Subject行は含めない - メール本文のみ出力
- URLはプレーンテキストで記載（マークダウンリンク禁止）
- 市場調査データに記載された実データのみ使用
- 架空の製品名・URL・金額は絶対に生成しない

=== フォーマット（必須） ===
- レポートの各セクションは必ず番号付き: 「1. タイトル」「2. タイトル」「3. タイトル」
- □や■などの記号は使用禁止
- サブ項目には「・」を使用

OUTPUT LANGUAGE: ENGLISH ONLY"""

            print(f"  🤖 Calling OpenAI API with template + prompt to generate complete English body...")

            # システムプロンプトを構築（共通プロンプト + デフォルト指示）
            default_system_prompt = """You are a professional email composer. Your task is to complete an email by filling in the report section while preserving the original template structure.

=== CRITICAL: TEMPLATE PRESERVATION ===

1. The email template provided is the BASE STRUCTURE - you MUST preserve it exactly
2. Only replace the {{レポート}} or {{レポ―ト}} placeholder with the generated report
3. DO NOT modify, remove, or rearrange any other parts of the template
4. Keep all greetings, signatures, and other template text unchanged
5. DO NOT add new sections that don't exist in the template

=== DATA ACCURACY ===

1. ONLY USE REAL DATA from the "市場調査結果" (Market Research Results) section
   - Product names, URLs, funding amounts MUST come from provided data
   - NEVER fabricate any product information

2. WHEN NO SIMILAR PRODUCTS WERE FOUND:
   - State clearly: "No similar products were found"
   - Present as market opportunity
   - DO NOT make up fictional products

3. PREDICTIONS must be based on real data with citations

4. FORBIDDEN:
   - Fabricating product names, URLs, or funding amounts
   - Adding content not in the template structure

=== FORMATTING (MUST FOLLOW) ===

1. MAIN SECTIONS must use numbered format: "1. Title", "2. Title", "3. Title"
   - Example: "1. Product Features", "2. Kickstarter Price", "3. Market Analysis"
   - NEVER use bullets (・, -, □, ■) for main section titles
2. Sub-items within sections: use "・" for bullet points
3. NO Markdown symbols: no **, ##, -, □, or []()
4. URLs as plain text only
5. Convert USD to JPY (e.g., $49 = approximately ¥7,300)

=== OUTPUT ===

- ENGLISH ONLY
- Preserve template structure completely
- Replace only {{レポート}} section
- No subject line"""

            # 共通プロンプトがある場合は先頭に追加
            if common_prompt and common_prompt.strip():
                system_prompt = f"""{common_prompt}

---

{default_system_prompt}"""
                print(f"  📋 共通プロンプトを適用しました")
            else:
                system_prompt = default_system_prompt

            # OpenAI APIを呼び出し（日本語プロンプト + 英語テンプレート → 完全な英語本文）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": combined_prompt
                    }
                ],
                max_tokens=8000,
                temperature=0.5
            )

            generated_body = response.choices[0].message.content.strip()
            print(f"  ✓ Complete English body generated via OpenAI API")

            # 後処理: 件名行を削除、マークダウンリンクをプレーンテキストに変換
            generated_body = self._clean_generated_body(generated_body)

            return generated_body

        except Exception as e:
            print(f"  ❌ Error calling OpenAI API: {e}")
            return f"Error: Failed to generate report from prompt ({str(e)})"

    def _generate_body(self, body_template, prompt_template, kickstarter_url, product_name, language='Japanese'):
        """
        本文を生成

        Args:
            body_template (str): 本文テンプレート
            prompt_template (str): プロンプトテンプレート（空の場合はbody_templateをそのまま使用）
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名
            language (str): 言語（Japanese or English）

        Returns:
            str: 生成された本文
        """
        # プロンプトが空の場合は、本文テンプレートのプレースホルダーを置換してそのまま返す
        if not prompt_template or not prompt_template.strip():
            return self._replace_placeholders(body_template, kickstarter_url, product_name)

        # プロンプトがある場合は、OpenAI APIで生成
        if not self.api_available:
            print(f"  ⚠️  OpenAI API key not configured. Using template body as-is.")
            return self._replace_placeholders(body_template, kickstarter_url, product_name)

        try:
            # プロンプトのプレースホルダーを置換
            prompt = self._replace_placeholders(prompt_template, kickstarter_url, product_name)

            print(f"  🤖 Calling OpenAI API for {language} report...")

            # OpenAI APIを呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional business consultant specializing in market analysis for product launches in Japan. Respond in {language}."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.7
            )

            generated_body = response.choices[0].message.content.strip()
            print(f"  ✓ {language} report generated via OpenAI API")

            return generated_body

        except Exception as e:
            print(f"  ❌ Error calling OpenAI API: {e}")
            print(f"  ⚠️  Falling back to template body")
            return self._replace_placeholders(body_template, kickstarter_url, product_name)

    def _clean_generated_body(self, text):
        """
        生成された本文をクリーンアップ
        - 件名行（Subject:）を削除
        - マークダウンリンク [text](url) をプレーンテキスト url に変換

        Args:
            text (str): 生成された本文

        Returns:
            str: クリーンアップされた本文
        """
        import re

        # 件名行を削除（Subject: で始まる行とその後の空行）
        lines = text.split('\n')
        cleaned_lines = []
        skip_next_empty = False

        for line in lines:
            # Subject: で始まる行をスキップ
            if line.strip().startswith('Subject:'):
                skip_next_empty = True
                continue

            # Subject: の後の空行をスキップ
            if skip_next_empty and line.strip() == '':
                skip_next_empty = False
                continue

            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # マークダウンリンク [text](url) を url に変換
        # 例: [Life Support](https://lifeupjp.com) → https://lifeupjp.com
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\2', text)

        return text.strip()

    def _replace_placeholders(self, text, kickstarter_url, product_name):
        """
        プレースホルダーを置換

        Args:
            text (str): テキスト
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            str: 置換後のテキスト
        """
        if not text:
            return ''

        # {{URL}}を置換
        text = text.replace('{{URL}}', kickstarter_url)
        text = text.replace('{{url}}', kickstarter_url)

        # {{name}}を置換
        if product_name:
            text = text.replace('{{name}}', product_name)
        else:
            text = text.replace('{{name}}', 'Manufacturer')

        return text
