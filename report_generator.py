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

    def _translate_to_english(self, text):
        """
        日本語テキストを英語に翻訳（API送信用）

        Args:
            text (str): 翻訳するテキスト

        Returns:
            str: 英訳されたテキスト
        """
        if not text or not text.strip():
            return text

        if not self.api_available:
            return text

        try:
            response = self.client.chat.completions.create(
                model='gpt-4o-mini',  # 翻訳は軽量モデルで十分
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate the following Japanese text to English. Keep the same formatting (bullet points, sections, etc.). Only output the translation, nothing else."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                max_tokens=4000,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  ⚠️ Translation failed, using original text: {e}")
            return text

    def _translate_body_to_japanese(self, english_body, product_name=''):
        """
        英語本文を日本語に翻訳（会社名・製品名は英語のまま保持）

        Args:
            english_body (str): 英語本文
            product_name (str): 製品名/メーカー名（英語のまま保持）

        Returns:
            str: 日本語本文（名前は英語のまま）
        """
        if not english_body or not english_body.strip():
            return english_body

        if not self.api_available:
            return ''  # APIがない場合は空文字（GOOGLETRANSLATEにフォールバック）

        try:
            print(f"  🇯🇵 Translating body to Japanese (keeping names in English)...")

            response = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional English to Japanese translator for business emails.

CRITICAL RULES:
1. Translate the text to natural, polite Japanese (敬語)
2. Keep ALL company names, product names, and proper nouns in English (do NOT translate them)
   - Example: "Dear Tenkara Rod Co.," → "Tenkara Rod Co. 様"
   - Example: "AKASO" stays as "AKASO"
   - Example: "Life Support Co., Ltd." stays as "Life Support Co., Ltd."
3. Keep all URLs exactly as they are
4. Keep the same formatting (line breaks, sections, bullet points)
5. Output ONLY the Japanese translation, nothing else"""
                    },
                    {
                        "role": "user",
                        "content": english_body
                    }
                ],
                max_tokens=16000,
                temperature=0.3
            )

            jp_body = response.choices[0].message.content.strip()
            print(f"  ✓ Japanese body generated ({len(jp_body)} chars)")

            return jp_body

        except Exception as e:
            print(f"  ⚠️ Japanese translation failed: {e}")
            return ''  # 失敗時は空文字（GOOGLETRANSLATEにフォールバック）

    def generate_report(self, template, kickstarter_url, product_name='', common_prompt='', system_settings=''):
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
            common_prompt (str, optional): 共通プロンプト（設定シートA2から読み込み）
            system_settings (str, optional): システム設定（設定シートG2から読み込み）

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
                common_prompt,  # 共通プロンプト（設定シートA2）
                system_settings  # システム設定（設定シートG2）
            )
            # 日本語本文は空文字列（Google SheetsのGOOGLETRANSLATE関数で翻訳、名前はSUBSTITUTEで英語に戻す）
            jp_body = ''

        return {
            'jp_subject': jp_subject,
            'en_subject': en_subject,
            'jp_body': jp_body,
            'en_body': en_body
        }

    def _generate_from_prompt(self, prompt, body_template, kickstarter_url, product_name, common_prompt='', system_settings=''):
        """
        日本語プロンプト + 本文テンプレートからOpenAI APIで完全な英語本文を生成

        Args:
            prompt (str): プロンプト（日本語、A3）
            body_template (str): 本文テンプレート（英語、A2）
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名
            common_prompt (str, optional): 共通プロンプト（設定シートA2から読み込み）
            system_settings (str, optional): システム設定（設定シートG2から読み込み）

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

            # テンプレートを{{レポート}}で分割（前半と後半を保持）
            report_placeholder = '{{レポート}}'
            if report_placeholder in processed_body_template:
                template_parts = processed_body_template.split(report_placeholder, 1)
                template_before = template_parts[0]
                template_after = template_parts[1] if len(template_parts) > 1 else ''
                print(f"  📝 Template split: {len(template_before)} chars before, {len(template_after)} chars after placeholder")
            else:
                # プレースホルダーがない場合は全体を前半として扱う
                template_before = processed_body_template
                template_after = ''
                print(f"  ⚠️ No {{{{レポート}}}} placeholder found in template")

            # 市場調査：類似製品を検索
            market_research_data = ""
            if self.market_searcher:
                search_results = self.market_searcher.search_similar_products(kickstarter_url, product_name)
                market_research_data = self.market_searcher.format_for_prompt(search_results)

            # === 日本語プロンプトを英語に翻訳（API送信用） ===
            print(f"  🌐 Translating prompts to English...")

            # 分析指示（A3）を英訳
            translated_prompt = self._translate_to_english(processed_prompt)
            print(f"    ✓ Analysis instructions translated")

            # 市場調査データを英訳
            if market_research_data:
                translated_market_data = self._translate_to_english(market_research_data)
                print(f"    ✓ Market research data translated")
            else:
                translated_market_data = ""

            # システム設定（G2）を英訳
            if system_settings and system_settings.strip():
                translated_system_settings = self._translate_to_english(system_settings)
                print(f"    ✓ System settings translated")
            else:
                translated_system_settings = ""

            # 共通プロンプト（A2）を英訳
            if common_prompt and common_prompt.strip():
                translated_common_prompt = self._translate_to_english(common_prompt)
                print(f"    ✓ Common prompt translated")
            else:
                translated_common_prompt = ""

            # ユーザープロンプト（レポート部分のみ生成を依頼）
            combined_prompt = f"""[ANALYSIS INSTRUCTIONS]
{translated_prompt}

{translated_market_data}

=== OUTPUT FORMAT ===
- Output in ENGLISH ONLY
- Generate ONLY the report content (the part that replaces the placeholder)
- Do NOT include email greetings, signatures, or other template parts
- Use plain text URLs (no markdown links)
- Include URLs INLINE with product names using parentheses (do NOT use "URL:" prefix)
  Correct: "Product ABC" (https://www.makuake.com/project/xxx) raised 1,234,567 yen
  Wrong: "Product ABC", URL: https://...
- NEVER create a "Sources", "Information Sources", "情報源", or "References" section at the end
- URLs are already inline, so listing them again at the end is redundant and prohibited
- Keep all company names and product names in their original English form (do NOT translate proper nouns)"""

            print(f"  🤖 Calling OpenAI API with translated prompts...")

            # システムプロンプトを構築（英語）
            base_system_prompt = """You are a professional business consultant. Generate the market analysis report in ENGLISH ONLY.

IMPORTANT: Generate ONLY the report content itself. Do NOT include:
- Email greetings (Dear..., etc.)
- Signatures
- Company references sections
- Any template text

Just output the market analysis report content that will be inserted into the email template."""

            # 英訳されたシステム設定を追加
            if translated_system_settings:
                system_prompt = f"""{base_system_prompt}

{translated_system_settings}"""
            else:
                system_prompt = base_system_prompt

            # 英訳された共通プロンプトを追加
            if translated_common_prompt:
                system_prompt = f"""{system_prompt}

{translated_common_prompt}"""

            # OpenAI APIを呼び出し（レポート部分のみ生成）
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
                max_tokens=16000,
                temperature=0.7
            )

            generated_report = response.choices[0].message.content.strip()
            print(f"  ✓ Report content generated via OpenAI API ({len(generated_report)} chars)")

            # 後処理: 件名行を削除、マークダウンリンクをプレーンテキストに変換
            generated_report = self._clean_generated_body(generated_report)

            # テンプレートの前半 + 生成されたレポート + テンプレートの後半を結合
            final_body = template_before + generated_report + template_after
            print(f"  ✓ Final body assembled ({len(final_body)} chars)")

            return final_body

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
        - 末尾の情報源/Sources/Referencesセクションを削除
        - URL: プレフィックスを括弧形式に変換

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

        # 末尾の情報源/Sources/Referencesセクションを削除
        # パターン: "情報源" または "Sources" または "References" で始まる行から末尾のURL一覧を削除
        sources_patterns = [
            r'\n+\s*情報源\s*:?\s*\n+(https?://[^\s]+\s*\n*)+',
            r'\n+\s*Sources?\s*:?\s*\n+(https?://[^\s]+\s*\n*)+',
            r'\n+\s*References?\s*:?\s*\n+(https?://[^\s]+\s*\n*)+',
            r'\n+\s*Information Sources?\s*:?\s*\n+(https?://[^\s]+\s*\n*)+',
        ]
        for pattern in sources_patterns:
            text = re.sub(pattern, '\n', text, flags=re.IGNORECASE)

        # 「URL：」や「URL:」プレフィックスを括弧形式に変換
        # 例: 「製品名」、URL：https://... → 「製品名」(https://...)
        text = re.sub(r'[、,]\s*URL[：:]\s*(https?://[^\s]+)', r' (\1)', text)

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
