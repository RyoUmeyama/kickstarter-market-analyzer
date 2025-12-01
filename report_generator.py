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
            combined_prompt = f"""以下は、英語の本文テンプレートと日本語の分析指示、および実際の市場調査データです。

【Email Body Template (English)】
{processed_body_template}

【Analysis Instructions (Japanese)】
{processed_prompt}

{market_research_data}

IMPORTANT INSTRUCTIONS:
- Generate the COMPLETE email body in ENGLISH ONLY
- Insert the analysis results into the template where {{{{レポート}}}} appears
- Keep the entire template structure in English
- Replace ONLY the {{{{レポート}}}} section with the analysis results
- Do NOT include Subject: line - output email body only
- Use plain text URLs (https://...), NOT markdown links [text](url)
- Output must be ready for copy-paste into an email client
- ONLY use the product data provided in the market research section above
- If no similar products were found, mention this positively (new market opportunity)
- NEVER invent or fabricate any product names, URLs, or funding amounts

OUTPUT LANGUAGE: ENGLISH ONLY (英語のみで出力してください)"""

            print(f"  🤖 Calling OpenAI API with template + prompt to generate complete English body...")

            # システムプロンプトを構築（共通プロンプト + デフォルト指示）
            default_system_prompt = """You are a professional market research analyst specializing in the Japanese market.

=== MOST IMPORTANT: DATA ACCURACY (MUST FOLLOW) ===

1. ONLY USE REAL DATA from the "市場調査結果" (Market Research Results) section
   - Product names, URLs, funding amounts, and backer counts MUST come from the provided data
   - NEVER invent, fabricate, or guess any product information
   - If data is not provided, DO NOT include it

2. WHEN NO SIMILAR PRODUCTS WERE FOUND:
   - Clearly state: "No similar products were found on Japanese crowdfunding platforms"
   - Present this as a market opportunity (first mover advantage)
   - DO NOT fabricate fictional products to fill the gap

3. PREDICTIONS AND ANALYSIS must be based on real data:
   - If similar products exist: base predictions on their actual performance
     Example: "Based on Product A achieving ¥5,000,000 with 500 backers, we estimate..."
   - If no similar products: state "Due to lack of comparable data, specific predictions are difficult"
   - Always cite the source data for any prediction

4. INFORMATION SOURCES:
   - Only include URLs that appear in the market research data
   - List all referenced URLs at the end under "Information Sources"
   - The Kickstarter URL is the only exception (always include it)

5. FORBIDDEN:
   - Fabricating product names that don't exist in the data
   - Making up funding amounts or backer numbers
   - Inventing URLs (especially Amazon, Makuake, or any other site)
   - Claiming EC site sales data without source

=== FORMATTING RULES ===

1. Use numbered sections: "1. Title", "2. Title", "3. Title"
2. Use "■" for sub-section headers
3. Use "・" for bullet points
4. NO Markdown: no **, ##, -, or []() links
5. URLs must be plain text
6. Convert USD to JPY (e.g., $49 = approximately ¥7,300)

=== OUTPUT ===

- Language: ENGLISH ONLY
- Insert analysis where {{レポート}} appears
- Output email body only (no subject line)
- Be professional and honest about data limitations"""

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
