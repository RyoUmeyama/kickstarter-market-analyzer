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
            system_content = """You are a professional translator. Translate the following Japanese text to English.

RULES:
1. Keep the same paragraph structure - do not add extra line breaks
2. Keep all company names and product names in their original form (do NOT translate proper nouns)
3. Preserve all numbering - circled numbers (①②③) can be converted to regular numbers (1. 2. 3.) but NEVER remove them
4. Keep all URLs exactly as they are - do NOT modify or shorten them
5. Write URLs naturally in sentences, not on separate lines
6. Do NOT use any markdown formatting (no *, **, #, -, etc.)
7. Output plain text only
8. Only output the translation, nothing else."""

            response = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": text}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            translated = response.choices[0].message.content.strip()
            # 後処理（正規表現によるクリーンアップ）
            translated = self._clean_generated_body(translated)
            return translated
        except Exception as e:
            print(f"  ⚠️ Translation failed, using original text: {e}")
            return text

    def generate_report(self, template, kickstarter_url, product_name='', common_prompt='', system_settings='', translation_rules='', output_format_rules=''):
        """
        テンプレートに基づいてレポートを生成

        仕様:
        - A1（en_subject）とB1（jp_subject）はGOOGLETRANSLATE関数で連動
        - A2（en_body）とB2（jp_body）もGOOGLETRANSLATE関数で連動
        - A3（プロンプト、日本語）がある場合のみOpenAI APIを使用
          → 英語でレポートを生成 → Google Sheetsで日本語に翻訳

        Args:
            template (dict): テンプレート設定
            kickstarter_url (str): Kickstarter URL
            product_name (str, optional): 製品名/メーカー名
            common_prompt (str, optional): 共通プロンプト（設定シートA2から読み込み）
            system_settings (str, optional): システム設定（設定シートG2から読み込み）
            translation_rules (str, optional): 翻訳ルール（設定シートH2から読み込み）
            output_format_rules (str, optional): 出力形式ルール（設定シートI2から読み込み）

        Returns:
            dict: 生成されたレポート
        """
        # 翻訳ルールを保存（_translate_to_english で使用）
        self._translation_rules = translation_rules
        self._output_format_rules = output_format_rules
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

            # テンプレート部分を英語に翻訳（日本語が含まれている場合）
            print(f"  🌐 Translating template parts to English...")
            if template_before and template_before.strip():
                template_before = self._translate_to_english(template_before)
                print(f"    ✓ Template before placeholder translated")
            if template_after and template_after.strip():
                template_after = self._translate_to_english(template_after)
                print(f"    ✓ Template after placeholder translated")

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
            combined_prompt = f"""[PRODUCT ANALYSIS REQUEST]
{translated_prompt}

[JAPANESE MARKET RESEARCH DATA - USE THIS REAL DATA]
{translated_market_data}

IMPORTANT INSTRUCTIONS:
1. Analyze THIS SPECIFIC product based on its features, target audience, and market positioning
2. Use the ACTUAL market research data above - cite real product names, URLs, and funding amounts
3. Provide CONCRETE strategies tailored to this product's characteristics
4. Calculate realistic sales projections based on similar products' performance
5. Explain WHY this product would succeed in Japan (specific reasons, not generic)
6. Recommend specific launch timing, pricing strategy, and marketing channels

OUTPUT FORMAT RULES:
1. Write in ENGLISH ONLY (no Japanese characters)
2. Use PLAIN TEXT only (no markdown: no *, #, -, bullet points, etc.)
3. Write in natural flowing paragraphs - do NOT put each sentence on a separate line
4. Only use blank lines between major sections (numbered sections like 1. 2. 3.)
5. Within each section, write continuous paragraphs without extra line breaks
6. For product references, write naturally: "Product Name achieved X yen in funding. See: URL"
7. Do NOT output "URL:" without an actual URL after it"""

            print(f"  🤖 Calling OpenAI API with translated prompts...")

            # システムプロンプトを構築
            base_system_prompt = """You are a senior marketing consultant with 15+ years of experience helping international products succeed in the Japanese market. You specialize in crowdfunding launches and e-commerce expansion in Japan.

YOUR ROLE:
- Analyze the specific Kickstarter product and identify its unique selling points for Japanese consumers
- Provide concrete, actionable strategies based on REAL market data from similar products
- Focus on HOW to succeed in Japan, not generic advice
- Use actual funding amounts and success stories from Japanese crowdfunding platforms (Makuake, etc.)
- Write persuasively to convince the creator that expanding to Japan is a valuable opportunity

WRITING STYLE:
- Be specific and data-driven (use actual numbers from market research)
- Focus on actionable recommendations, not general information
- Highlight the product's competitive advantages in the Japanese market
- Show concrete success potential with realistic projections
- Write as a professional proposal, not a generic report

CRITICAL DATA RULES - MUST FOLLOW:
1. If Kickstarter funding amount is provided in the data, you MUST cite it exactly (e.g., "Your product raised $252,364 from 1,295 backers")
2. If Makuake similar products are provided, you MUST cite their exact names, URLs, and funding amounts
3. NEVER write "Please refer to the Kickstarter page" or "Please check the Kickstarter page" - this is FORBIDDEN
4. NEVER write vague statements like "For pricing information, see the page" - either cite the actual data or skip that topic
5. If specific data is NOT provided, do NOT mention that topic at all - skip it entirely
6. Do NOT invent or estimate numbers that are not in the provided data
7. Only write about topics for which you have actual data

CRITICAL FORMAT RULES:
1. Write in ENGLISH ONLY - absolutely NO Japanese characters
2. Use PLAIN TEXT only - NO markdown (no *, **, #, -, bullet points)
3. Write in natural flowing paragraphs - each section should have continuous text
4. Only insert blank lines between numbered sections (1. 2. 3.)
5. Do NOT put each sentence on a separate line - keep paragraphs together
6. For URLs, write naturally in sentences: "Product Name achieved X yen. See: https://..."
7. NEVER output "URL:" by itself without an actual URL
8. NEVER generate fake URLs like www.example.com or placeholder URLs
9. ONLY use real URLs from the market research data provided - if no URL is available, do not mention a URL at all

Do NOT include email greetings, signatures, or template text."""

            # システム設定（G2）と共通プロンプト（A2）を追加
            system_parts = [base_system_prompt]
            if translated_system_settings:
                system_parts.append(translated_system_settings)
            if translated_common_prompt:
                system_parts.append(translated_common_prompt)

            system_prompt = "\n\n".join(system_parts)

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
            # 各部分の間に適切な改行を追加
            parts = []
            if template_before and template_before.strip():
                parts.append(template_before.rstrip())
            if generated_report and generated_report.strip():
                parts.append(generated_report.strip())
            if template_after and template_after.strip():
                parts.append(template_after.lstrip())

            final_body = '\n\n'.join(parts)
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
        - マークダウン記法を削除（*, **, #, - など）
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

        # マークダウン記法を削除
        # **太字** → 太字
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        # *斜体* → 斜体（ただしURL内の*は除外するため、単語境界を使用）
        text = re.sub(r'(?<!\w)\*([^*\n]+)\*(?!\w)', r'\1', text)
        # __太字__ → 太字
        text = re.sub(r'__([^_]+)__', r'\1', text)
        # _斜体_ → 斜体
        text = re.sub(r'(?<!\w)_([^_\n]+)_(?!\w)', r'\1', text)
        # # ヘッダー → ヘッダー（行頭の#を削除）
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # 行頭の - や * のリストマーカーを削除（ただし本文に含まれる場合は残す）
        text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)

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

        # 括弧で囲まれたURLを修正（括弧を削除してスペースで区切る）
        # 半角括弧: (https://...) → スペース + URL
        text = re.sub(r'\s*\(\s*(https?://[^\s\)]+)\s*\)', r' \1', text)
        # 全角括弧: （https://...） → スペース + URL
        text = re.sub(r'\s*（\s*(https?://[^\s）]+)\s*）', r' \1', text)

        # 「URL：」や「URL:」で始まるが後にURLがない行を削除
        text = re.sub(r'\n\s*URL[：:]?\s*\n', '\n', text)
        text = re.sub(r'\n\s*URL[：:]?\s*$', '', text)

        # 「URL：」や「URL:」プレフィックスを整理（URLがある場合）
        text = re.sub(r'URL[：:]\s*(https?://)', r'\1', text)

        # 偽URLやプレースホルダーURLを削除
        # www.example.com, example.com, placeholder.com などを含む文を削除
        fake_url_patterns = [
            r'[^.]*www\.example\.com[^.]*\.',
            r'[^.]*example\.com[^.]*\.',
            r'[^.]*placeholder\.com[^.]*\.',
            r'[^.]*yourwebsite\.com[^.]*\.',
            r'For (further |more )?details,? please visit[^.]+\.',
            r'Please visit[^.]+for (more |further )?details\.',
        ]
        for pattern in fake_url_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 連続する空行を1つに整理
        text = re.sub(r'\n{3,}', '\n\n', text)

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
