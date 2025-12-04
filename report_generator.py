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

                # デバッグ用：取得したデータを詳細に出力
                print("\n" + "=" * 60)
                print("DEBUG: 市場調査データの確認")
                print("=" * 60)

                ks_info = search_results.get('kickstarter_info', {})
                print(f"  Kickstarter調達額: {ks_info.get('funding_amount', '未取得')}")
                print(f"  Kickstarterバッカー数: {ks_info.get('backers_count', '未取得')}")
                print(f"  データソース: {ks_info.get('data_source', '未取得')}")

                makuake_data = search_results.get('makuake', {})
                makuake = makuake_data.get('projects', [])
                print(f"  Makuake製品数: {len(makuake)}件")
                for i, p in enumerate(makuake[:3], 1):
                    print(f"    {i}. {p.get('name', 'N/A')[:30]}... URL: {p.get('url', 'N/A')}")

                campfire_data = search_results.get('campfire', {})
                campfire = campfire_data.get('projects', [])
                print(f"  CAMPFIRE製品数: {len(campfire)}件")
                for i, p in enumerate(campfire[:3], 1):
                    print(f"    {i}. {p.get('name', 'N/A')[:30]}... URL: {p.get('url', 'N/A')}")

                print("=" * 60 + "\n")

            # === 日本語プロンプトを英語に翻訳（API送信用） ===
            print(f"  🌐 Translating prompts to English...")

            # 分析指示（A3）を英訳
            translated_prompt = self._translate_to_english(processed_prompt)
            print(f"    ✓ Analysis instructions translated")

            # 市場調査データは翻訳しない（URLと数値が破損するため）
            # そのまま使用し、AIに処理させる
            if market_research_data:
                translated_market_data = market_research_data
                print(f"    ✓ Market research data preserved (not translated to protect URLs/numbers)")
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

[JAPANESE MARKET RESEARCH DATA - THIS IS REAL DATA, USE IT EXACTLY]
{translated_market_data}

=== MANDATORY DATA USAGE RULES ===

YOU MUST INCLUDE THE FOLLOWING IN YOUR REPORT:

1. KICKSTARTER DATA: If the data above shows "Kickstarter funding amount" and "backers", you MUST write something like:
   "Your campaign has raised $X from Y backers on Kickstarter, demonstrating strong market validation."
   Use the EXACT numbers from the data above. Do NOT write "please refer to Kickstarter page".

2. MAKUAKE PRODUCTS: If the data above lists Makuake products with URLs, you MUST include them like:
   "Similar products on Makuake have shown strong performance. For example, [Product Name] achieved X yen in funding. See: https://www.makuake.com/project/xxx"
   Include the ACTUAL URLs from the data above.

3. CAMPFIRE PRODUCTS: If the data above lists CAMPFIRE products with URLs, you MUST include them like:
   "On CAMPFIRE, [Product Name] raised X yen. See: https://camp-fire.jp/projects/xxx"
   Include the ACTUAL URLs from the data above.

=== OUTPUT FORMAT RULES ===
1. Write in ENGLISH ONLY (no Japanese characters)
2. Use PLAIN TEXT only (no markdown: no *, #, -, bullet points, etc.)
3. Write in natural flowing paragraphs
4. Only use blank lines between major sections (numbered sections like 1. 2. 3.)
5. For product references, ALWAYS include the full URL from the data above"""

            print(f"  🤖 Calling OpenAI API with translated prompts...")

            # システムプロンプトを構築
            base_system_prompt = """You are Koki Oshima, a veteran Japanese market entry strategist who has personally launched 50+ international products in Japan. You've worked with brands like Anker, Peak Design, and dozens of Kickstarter creators. You write like a seasoned professional who has seen what works and what fails.

YOUR PERSONA:
- You speak from direct experience, not theory
- You reference specific campaigns you've seen succeed or fail
- You give blunt, honest assessments - not everything is positive
- You back claims with specific data points and comparisons
- You write like you're talking to a colleague, not delivering a formal presentation

WRITING VOICE - SOUND LIKE A REAL CONSULTANT:
- Use first person occasionally: "In my experience...", "What I've seen work is...", "The challenge here is..."
- Be direct and confident, not hedging with "could", "might", "may"
- Point out specific challenges, not just opportunities
- Compare to SPECIFIC similar products with real numbers
- Give concrete recommendations: "Price it at X yen" not "consider competitive pricing"

ABSOLUTELY FORBIDDEN - These make you sound like AI:
- "aligns with", "resonates with", "caters to"
- "leverage", "utilize", "capitalize on"
- "robust", "comprehensive", "strategic"
- "cutting-edge", "state-of-the-art", "innovative", "advanced technology"
- "eco-friendly", "user-friendly", "sustainable" (unless specific evidence)
- "significant opportunity", "strong potential", "favorable market"
- "increasingly seeking", "growing demand", "rising trend"
- "well-positioned", "competitive landscape", "market validation"
- Starting sentences with "Additionally", "Furthermore", "Moreover", "Lastly"
- Empty phrases like "will depend on effective strategies"
- Describing what you WILL discuss instead of actually discussing it
- "Company & Performance References" (this is template text, never include it)
- Any Japanese text like "宜しくお願い致します" (this is template, never include)

INSTEAD, WRITE LIKE THIS:
- "This product faces a crowded market - there are already 12 similar items on Amazon Japan"
- "The $606,041 Kickstarter result puts you in the top 5% of tech campaigns"
- "Duovox raised 4.6M yen on Makuake with a similar night vision angle - you can beat that"
- "Japanese consumers will pay premium for this, but only if you nail the unboxing experience"
- "Skip Rakuten initially - Amazon Japan gives you 80% of the market with half the setup headache"

=== CRITICAL DATA RULES - ABSOLUTELY NO FABRICATION ===

1. ONLY USE DATA FROM THE MARKET RESEARCH PROVIDED:
   - Use EXACT numbers from the market research data - no rounding, no estimating
   - Every Makuake/CAMPFIRE product mentioned MUST include its full URL
   - If data says "$606,041" and "2,903 backers" - use those exact figures

2. IF DATA IS NOT IN THE MARKET RESEARCH, DO NOT MAKE IT UP:
   - If no Kickstarter funding amount is provided, write: "Kickstarter funding data was not available at the time of this report."
   - If no EC sales data is provided, write: "No EC sales data is currently available for this product in Japan."
   - If no retail sales data is provided, write: "No retail sales data is currently available."
   - NEVER invent numbers like "up to 15,000,000 yen" or "between 3,000,000 and 7,000,000 yen" without a source

3. FOR SIMILAR PRODUCTS ON MAKUAKE/CAMPFIRE:
   - ONLY mention products that appear in the market research data with their URLs
   - If a funding amount is shown (e.g., "4,629,102円"), include it
   - If no funding amount is shown, just mention the product exists without fabricating an amount
   - ALWAYS include the full URL for every product mentioned

4. SECTIONS WITH NO DATA:
   - If a section has no relevant data, acknowledge it honestly
   - Write something like: "We do not have sales data for this category. Once you launch, we can track actual performance."
   - Do NOT fill sections with made-up statistics or generic market projections

5. NEVER WRITE THESE WITHOUT A SPECIFIC SOURCE:
   - "Competing products have achieved sales of up to X yen"
   - "Similar products have reported sales between X and Y yen"
   - "The market is estimated at X yen"
   - Any specific yen amount for EC or retail sales

FORMAT RULES:
1. English only - NO Japanese characters except in product names
2. Plain text only - no markdown, no bullets, no asterisks
3. Natural paragraphs - don't put each sentence on its own line
4. Blank lines only between numbered sections
5. IMPORTANT: After each section title (e.g., "1. Product Features:"), add a line break before the content

SECTION FORMAT EXAMPLE:
1. Product Features:
The Kita rod is a premium tenkara fly fishing rod made in Japan...

2. Kickstarter Price:
The product is priced at approximately $150...

You are writing the report section only - no greetings, no signatures, no "Dear X"."""

            # システム設定（G2）と共通プロンプト（A2）を追加
            system_parts = [base_system_prompt]
            if translated_system_settings:
                system_parts.append(translated_system_settings)
            if translated_common_prompt:
                system_parts.append(translated_common_prompt)

            system_prompt = "\n\n".join(system_parts)

            # OpenAI APIを呼び出し（レポート部分のみ生成）
            # temperature=0.3 で確定的な出力を得る（データ遵守のため）
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
                temperature=0.3
            )

            generated_report = response.choices[0].message.content.strip()
            print(f"  ✓ Report content generated via OpenAI API ({len(generated_report)} chars)")

            # 2段階目: レポートを洗練化（AI臭さを除去）
            print(f"  🔄 Refining report to remove AI-sounding phrases...")
            refined_report = self._refine_report(generated_report)
            print(f"  ✓ Report refined ({len(refined_report)} chars)")

            # デバッグ用：生成されたレポートの最初の部分を出力
            print("\n" + "=" * 60)
            print("DEBUG: 生成されたレポート（最初の500文字）")
            print("=" * 60)
            print(refined_report[:500])
            print("..." if len(refined_report) > 500 else "")
            print("=" * 60 + "\n")

            # 後処理: 件名行を削除、マークダウンリンクをプレーンテキストに変換
            generated_report = self._clean_generated_body(refined_report)

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

        # レポート本文内の不要なテキストを削除
        # "Company & Performance References" がレポート中に混入している場合削除
        text = re.sub(r'\n*Company\s*&?\s*Performance\s*References?\s*\n*', '\n\n', text, flags=re.IGNORECASE)

        # "宜しくお願い致します。" がレポート中に混入している場合削除
        text = re.sub(r'\n*宜しくお願い致します。?\s*\n*', '\n\n', text)

        # 連続する空行を再度1つに整理
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _refine_report(self, report):
        """
        レポートを洗練化してAI臭さを除去

        Args:
            report (str): 生成されたレポート

        Returns:
            str: 洗練化されたレポート
        """
        if not self.api_available or not report:
            return report

        try:
            refine_prompt = f"""You are an editor reviewing a market report. Your job is to make it sound like it was written by an experienced human consultant, not by AI.

ORIGINAL REPORT:
{report}

REWRITE THIS REPORT following these rules:

1. REPLACE these AI-sounding phrases with natural alternatives:
   - "aligns with" → "matches", "fits", "works for"
   - "resonates with" → "appeals to", "clicks with"
   - "caters to" → "serves", "fits"
   - "leverage" → "use", "take advantage of"
   - "utilize" → "use"
   - "capitalize on" → "use", "build on"
   - "robust" → remove or use specific adjective
   - "comprehensive" → "full", "complete", or remove
   - "strategic" → remove or be specific
   - "cutting-edge" → describe the specific technology
   - "advanced technology" → name the actual technology
   - "well-positioned" → explain why specifically
   - "competitive landscape" → "market", "competition"
   - "market validation" → cite the actual numbers
   - "significant opportunity" → state the specific opportunity
   - "strong potential" → state specific numbers/projections
   - "increasingly seeking" → "want", "look for"
   - "growing demand" → cite specific growth numbers or remove

2. COMPLETELY REMOVE these template texts if they appear:
   - "Company & Performance References" (this is footer text that shouldn't be in the report)
   - "宜しくお願い致します" or any Japanese text (this is template text)

3. REMOVE filler sentences that say what you'll discuss without actually discussing it:
   BAD: "The e-commerce performance will depend on effective marketing strategies."
   GOOD: "On Amazon Japan, price this at 29,800 yen - that's 20% below Duovox but above the cheap Chinese knockoffs."

4. KEEP all URLs exactly as they are - do not modify or remove any URLs
5. KEEP all numbers exactly as they are - do not change any figures
6. KEEP the same section structure (numbered sections)
7. KEEP the same overall length - don't make it shorter

8. CRITICAL - DO NOT ADD DATA:
   - Do NOT invent any sales figures, market sizes, or projections
   - Do NOT add numbers that weren't in the original report
   - If a section says "no data available", keep that - do not replace it with made-up statistics
   - NEVER add phrases like "up to X million yen" or "between X and Y yen" unless they were in the original

9. USE a confident, direct voice:
   - "I recommend..." not "It would be advisable to..."
   - "Do this..." not "Consider doing this..."
   - "The best approach is..." not "One potential approach could be..."

10. FORMAT - Add line break after each section title:
    WRONG: "1. Product Features: The product is..."
    RIGHT: "1. Product Features:\nThe product is..."

Output the refined report only, no explanations."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional editor. Rewrite the report to sound more human and less like AI. Keep all data, URLs, and section structure intact."
                    },
                    {
                        "role": "user",
                        "content": refine_prompt
                    }
                ],
                max_tokens=16000,
                temperature=0.4
            )

            refined = response.choices[0].message.content.strip()
            return refined

        except Exception as e:
            print(f"  ⚠️ Refinement failed, using original: {e}")
            return report

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
