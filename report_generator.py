#!/usr/bin/env python3
"""
レポート生成モジュール
テンプレート + OpenAI API対応
ウェブ検索による実在データ取得機能付き

V2対応: ⑤テンプレート選択時は詳細分析レポート（analyzer_v2）を使用
"""

import os
from openai import OpenAI
from market_search import MarketSearcher

# V2 Analyzer imports
from data_collector import DataCollector
from calculation_engine import CalculationEngine
from report_generator_v2 import ReportGeneratorV2
from web_researcher import WebResearcher
from industry_analyzer import IndustryAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from strict_evaluator import StrictEvaluator


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

    def reset_browser(self):
        """
        ブラウザセッションをリセット（Kickstarterのボット検出回避用）
        各商品処理後に呼び出すことで、新しいセッションで次の商品を取得できる
        """
        if self.market_searcher:
            self.market_searcher.reset_browser()

    def _generate_v2_report(self, kickstarter_url):
        """
        V2 Analyzerを使用して詳細分析レポートを生成

        Args:
            kickstarter_url (str): Kickstarter URL

        Returns:
            str: 生成された詳細レポート（日本語）
        """
        print("\n" + "=" * 60)
        print("🚀 V2 詳細分析レポート生成開始")
        print("=" * 60)

        try:
            # Phase 1: データ収集
            print("\n📥 Phase 1: データ収集")
            collector = DataCollector()
            raw_data = collector.collect_all(kickstarter_url)

            if not raw_data or raw_data.get('error'):
                error_msg = raw_data.get('error', 'データ収集に失敗しました') if raw_data else 'データ収集に失敗しました'
                print(f"  ❌ {error_msg}")
                return f"エラー: {error_msg}"

            # Phase 1.5: Web調査
            print("\n🔍 Phase 1.5: Web調査（詳細情報収集）")
            researcher = WebResearcher(api_key=self.api_key)
            # raw_dataからプロダクト名と説明を取得
            product_name = raw_data.get('kickstarter', {}).get('title', '')
            product_description = raw_data.get('kickstarter', {}).get('description', '')
            web_research = researcher.research_product(kickstarter_url, product_name, product_description)
            raw_data['web_research'] = web_research

            # Phase 2: 収支計算
            print("\n📊 Phase 2: 収支計算")
            calc_engine = CalculationEngine()
            calculations = calc_engine.calculate(raw_data)

            # Phase 2.5: 業界分析
            print("\n🏭 Phase 2.5: 業界分析")
            industry_analyzer = IndustryAnalyzer(api_key=self.api_key)
            industry_analysis = industry_analyzer.analyze(raw_data, calculations)

            # Phase 2.6: 競合分析
            print("\n🎯 Phase 2.6: 競合分析")
            competitor_analyzer = CompetitorAnalyzer(api_key=self.api_key)
            competitor_analysis = competitor_analyzer.analyze(raw_data, calculations, industry_analysis)

            # Phase 2.7: 厳格評価
            print("\n⚠️ Phase 2.7: 厳格評価")
            strict_evaluator = StrictEvaluator(api_key=self.api_key)
            strict_evaluation = strict_evaluator.evaluate(raw_data, calculations, industry_analysis, competitor_analysis)

            # Phase 3: レポート生成
            print("\n📝 Phase 3: レポート生成")
            report_gen = ReportGeneratorV2(api_key=self.api_key)
            report_text = report_gen.generate(
                raw_data,
                calculations,
                industry_analysis,
                competitor_analysis,
                strict_evaluation
            )

            print("\n✅ V2詳細分析レポート生成完了")
            print(f"  レポート長: {len(report_text):,}文字")

            return report_text

        except Exception as e:
            import traceback
            print(f"\n❌ V2レポート生成エラー: {e}")
            traceback.print_exc()
            return f"V2レポート生成エラー: {str(e)}"

    def _generate_v2_email(self, template, kickstarter_url, product_name):
        """
        ⑤テンプレート用: V2詳細レポートをテンプレートに埋め込んでメールを生成

        Args:
            template (dict): テンプレート設定
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            dict: 生成されたレポート（jp_subject, en_subject, jp_body, en_body）
        """
        # 件名のプレースホルダーを置換
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

        # V2詳細レポートを生成
        v2_report = self._generate_v2_report(kickstarter_url)

        # テンプレート本文を取得
        jp_body_template = self._replace_placeholders(
            template.get('jp_body', ''),
            kickstarter_url,
            product_name
        )

        # {{レポート}}プレースホルダーにV2レポートを挿入
        report_placeholder = '{{レポート}}'
        if report_placeholder in jp_body_template:
            jp_body = jp_body_template.replace(report_placeholder, v2_report)
            print(f"  ✓ V2レポートをテンプレートに挿入しました")
        else:
            # プレースホルダーがない場合はテンプレート末尾に追加
            jp_body = jp_body_template + "\n\n" + v2_report
            print(f"  ⚠️ {{{{レポート}}}}プレースホルダーが見つかりません。末尾に追加しました")

        # 英語本文を生成（日本語から翻訳）
        print(f"\n🌐 英語版を生成中...")
        en_body_template = self._replace_placeholders(
            template.get('en_body', ''),
            kickstarter_url,
            product_name
        )

        # V2レポートを英語に翻訳
        print(f"  → V2レポートを英語に翻訳中（{len(v2_report):,}文字）...")
        v2_report_en = self._translate_to_english(v2_report)

        # 英語テンプレートに挿入
        if report_placeholder in en_body_template:
            en_body = en_body_template.replace(report_placeholder, v2_report_en)
        else:
            en_body = en_body_template + "\n\n" + v2_report_en

        print(f"  ✓ 英語版生成完了（{len(en_body):,}文字）")

        return {
            'jp_subject': jp_subject,
            'en_subject': en_subject,
            'jp_body': jp_body,
            'en_body': en_body
        }

    def _contains_japanese(self, text):
        """
        テキストに日本語文字が含まれているかチェック

        Args:
            text (str): チェックするテキスト

        Returns:
            bool: 日本語が含まれている場合True
        """
        import re
        # ひらがな、カタカナ、漢字をチェック
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
        return bool(re.search(japanese_pattern, text))

    def _extract_section_count(self, prompt):
        """
        プロンプトから分析項目数を抽出
        丸数字の最大値をセクション数として認識（重複する丸数字は無視）

        Args:
            prompt (str): テンプレートのプロンプト（A3）

        Returns:
            int: 分析項目数（抽出できない場合は0）
        """
        import re
        # ①②③④などの丸数字を検出（通常の丸数字 + Dingbat丸数字）
        # 通常: ①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮ (U+2460-U+246E)
        # Dingbat: ➀➁➂➃➄➅➆➇➈➉ (U+2780-U+2789) - sans-serif
        # Dingbat: ➊➋➌➍➎➏➐➑➒➓ (U+278A-U+2793) - negative circled

        # 丸数字と対応する数値のマッピング
        circled_to_number = {
            '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
            '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
            '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15,
            '➀': 1, '➁': 2, '➂': 3, '➃': 4, '➄': 5,
            '➅': 6, '➆': 7, '➇': 8, '➈': 9, '➉': 10,
            '➊': 1, '➋': 2, '➌': 3, '➍': 4, '➎': 5,
            '➏': 6, '➐': 7, '➑': 8, '➒': 9, '➓': 10,
        }

        circled_numbers = re.findall(r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮➀➁➂➃➄➅➆➇➈➉➊➋➌➍➎➏➐➑➒➓]', prompt)
        if circled_numbers:
            # 丸数字を数値に変換し、最大値を取得（セクション数として認識）
            max_section = max(circled_to_number.get(c, 0) for c in circled_numbers)
            return max_section

        # 1. 2. 3. などの番号付きリストを検出
        numbered_items = re.findall(r'^\s*(\d+)\s*[.．、）\)]', prompt, re.MULTILINE)
        if numbered_items:
            # 最大値を取得
            return max(int(n) for n in numbered_items)

        return 0

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

    def generate_report(self, template, kickstarter_url, product_name='', common_prompt='', system_settings='', translation_rules='', output_format_rules='', industry_data=''):
        """
        テンプレートに基づいてレポートを生成

        仕様:
        - A1（en_subject）とB1（jp_subject）はGOOGLETRANSLATE関数で連動
        - A2（en_body）とB2（jp_body）もGOOGLETRANSLATE関数で連動
        - A3（プロンプト、日本語）がある場合のみOpenAI APIを使用
          → 英語でレポートを生成 → Google Sheetsで日本語に翻訳
        - ⑤テンプレートの場合: V2 Analyzerで詳細レポートを生成

        主要な設定（設定シートから読み込み）:
        - A2: 共通プロンプト（レポートの質・文体 - お客様編集可能）
        - G2: システム設定（テンプレート保持ルール、データ正確性ルール - 変更不可）
        - L列: 業界データ（市場統計）

        Args:
            template (dict): テンプレート設定
            kickstarter_url (str): Kickstarter URL
            product_name (str, optional): 製品名/メーカー名
            common_prompt (str, optional): 共通プロンプト（設定シートA2から読み込み）
            system_settings (str, optional): システム設定（設定シートG2から読み込み）
            translation_rules (str, optional): 翻訳ルール（設定シートH2から読み込み）
            output_format_rules (str, optional): 出力形式ルール（設定シートI2から読み込み）
            industry_data (str, optional): 業界データ（設定シートL列から読み込み）

        Returns:
            dict: 生成されたレポート
        """
        # 翻訳ルールを保存（_translate_to_english で使用）
        self._translation_rules = translation_rules
        self._output_format_rules = output_format_rules

        # テンプレート名を取得
        template_name = template.get('name', '')

        # ⑤テンプレートの場合はV2詳細分析レポートを使用
        if '⑤' in template_name:
            print(f"\n📋 テンプレート⑤検出: V2詳細分析レポートを生成します")
            return self._generate_v2_email(template, kickstarter_url, product_name)

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
                system_settings,  # システム設定（設定シートG2）
                industry_data  # 業界データ（設定シートL列）
            )
            # 日本語本文は空文字列（Google SheetsのGOOGLETRANSLATE関数で翻訳、名前はSUBSTITUTEで英語に戻す）
            jp_body = ''

        return {
            'jp_subject': jp_subject,
            'en_subject': en_subject,
            'jp_body': jp_body,
            'en_body': en_body
        }

    def _generate_from_prompt(self, prompt, body_template, kickstarter_url, product_name, common_prompt='', system_settings='', industry_data=''):
        """
        日本語プロンプト + 本文テンプレートからOpenAI APIで完全な英語本文を生成

        Args:
            prompt (str): プロンプト（日本語、A3）
            body_template (str): 本文テンプレート（英語、A2）
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名
            common_prompt (str, optional): 共通プロンプト（設定シートA2から読み込み）
            system_settings (str, optional): システム設定（設定シートG2から読み込み）
            industry_data (str, optional): 業界データ（設定シートL列から読み込み）

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

            # テンプレートからセクション数を抽出
            section_count = self._extract_section_count(prompt)
            if section_count > 0:
                print(f"  📊 Template requires exactly {section_count} sections")
            else:
                print(f"  ⚠️ Could not detect section count from template")

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
            # 最適化: 日本語文字が含まれている場合のみ翻訳
            print(f"  🌐 Checking if translation is needed...")
            if template_before and template_before.strip() and self._contains_japanese(template_before):
                template_before = self._translate_to_english(template_before)
                print(f"    ✓ Template before placeholder translated")
            else:
                print(f"    ✓ Template before placeholder: no translation needed")
            if template_after and template_after.strip() and self._contains_japanese(template_after):
                template_after = self._translate_to_english(template_after)
                print(f"    ✓ Template after placeholder translated")
            else:
                print(f"    ✓ Template after placeholder: no translation needed")

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
            # 最適化: 日本語が含まれている場合のみ翻訳API呼び出し
            print(f"  🌐 Checking prompts for translation needs...")

            # 分析指示（A3）を英訳（日本語が含まれている場合のみ）
            if self._contains_japanese(processed_prompt):
                translated_prompt = self._translate_to_english(processed_prompt)
                print(f"    ✓ Analysis instructions translated")
            else:
                translated_prompt = processed_prompt
                print(f"    ✓ Analysis instructions: no translation needed")

            # 市場調査データは翻訳しない（URLと数値が破損するため）
            # そのまま使用し、AIに処理させる
            if market_research_data:
                translated_market_data = market_research_data
                print(f"    ✓ Market research data preserved (not translated to protect URLs/numbers)")
            else:
                translated_market_data = ""

            # システム設定（G2）を英訳（日本語が含まれている場合のみ）
            if system_settings and system_settings.strip():
                if self._contains_japanese(system_settings):
                    translated_system_settings = self._translate_to_english(system_settings)
                    print(f"    ✓ System settings translated")
                else:
                    translated_system_settings = system_settings
                    print(f"    ✓ System settings: no translation needed")
            else:
                translated_system_settings = ""

            # 共通プロンプト（A2）を英訳（日本語が含まれている場合のみ）
            if common_prompt and common_prompt.strip():
                if self._contains_japanese(common_prompt):
                    translated_common_prompt = self._translate_to_english(common_prompt)
                    print(f"    ✓ Common prompt translated")
                else:
                    translated_common_prompt = common_prompt
                    print(f"    ✓ Common prompt: no translation needed")
            else:
                translated_common_prompt = ""

            # 業界データセクションを構築
            industry_data_section = ""
            if industry_data:
                industry_data_section = f"""

[VERIFIED INDUSTRY STATISTICS - USE THESE AS REFERENCE]
{industry_data}

These are verified industry statistics with sources. You may reference these when discussing market context.
Always cite the source when using these statistics."""

            # セクション数制限の指示を構築
            section_limit_instruction = ""
            if section_count > 0:
                section_limit_instruction = f"""
=== CRITICAL: SECTION COUNT LIMIT (ABSOLUTE RULE) ===
**YOU MUST GENERATE EXACTLY {section_count} SECTIONS**

The template specifies {section_count} analysis items (①②③④ = sections 1, 2, 3, 4).
- Generate sections numbered 1. through {section_count}. ONLY
- DO NOT generate section {section_count + 1}. or higher - this will cause IMMEDIATE REJECTION
- Each section should address ONE item from the template
- If the template has items ①②③④, your output is:
  1. [Topic from ①]
  2. [Topic from ②]
  3. [Topic from ③]
  4. [Topic from ④]
  STOP HERE - no section 5 or beyond

FORBIDDEN EXTRA SECTIONS (DO NOT GENERATE):
- PSE認証/PSE Certification (unless specifically requested in template items)
- 独占販売契約/Exclusive Sales Agreement
- 卸売りの可能性/Wholesale Potential
- Any topic NOT in the original {section_count} template items

"""

            # Kickstarterデータを明示的に抽出（search_resultsはmarket_searcherから取得済み）
            ks_info = search_results.get('kickstarter_info', {}) if search_results else {}
            ks_funding = ks_info.get('funding_amount', '')
            ks_backers = ks_info.get('backers_count', 0)
            ks_goal = ks_info.get('goal_amount', '')
            ks_percent = ks_info.get('percent_funded', 0)
            ks_days_left = ks_info.get('days_left', '')
            ks_data_source = ks_info.get('data_source', '')
            ks_rewards = ks_info.get('rewards', [])

            # 価格情報のセクション（常に「取得不可」として扱う - 汎用性を優先）
            # 注意: Kickstarterのページ構造は頻繁に変更されるため、
            # 価格情報の自動抽出は信頼性が低く、数百のURLを処理する際に問題となる。
            # そのため、価格情報は常にKickstarterページへの参照を促す方針とする。
            rewards_section = """REWARD/PRICE DATA: NOT AUTOMATICALLY EXTRACTED
- Pricing information varies by campaign and reward tier
- DO NOT INVENT specific prices like "$150", "$199", or "Early Bird $XXX"
- For Section 2 (Pricing), write: "For detailed pricing and reward tiers, please visit the Kickstarter page: [include the URL]"
- This ensures accuracy as prices may change during the campaign"""

            # Kickstarterデータの明示的なセクションを構築
            if ks_funding and ks_funding.strip():
                # 取得できたデータのみをリストアップ
                ks_data_lines = [
                    f"FUNDING AMOUNT: {ks_funding}",
                    f"BACKERS COUNT: {ks_backers}",
                ]
                # goal_amount, percent_funded, days_leftは取得できた場合のみ追加
                if ks_goal and ks_goal.strip():
                    ks_data_lines.append(f"GOAL AMOUNT: {ks_goal}")
                if ks_percent and ks_percent > 0:
                    ks_data_lines.append(f"PERCENT FUNDED: {ks_percent}%")
                if ks_days_left and ks_days_left.strip():
                    ks_data_lines.append(f"DAYS LEFT: {ks_days_left}")
                ks_data_lines.append(f"DATA SOURCE: {ks_data_source}")

                ks_data_text = "\n".join(ks_data_lines)

                kickstarter_data_section = f"""
=== KICKSTARTER DATA (USE EXACTLY AS SHOWN - NO ESTIMATION ALLOWED) ===
{ks_data_text}

{rewards_section}

ABSOLUTE RULES FOR SECTION 3 (TOTAL FUNDING):
- Use ONLY the data shown above - NOTHING MORE
- If FUNDING AMOUNT is shown: use that EXACT number
- If BACKERS COUNT is shown: use that EXACT number
- If GOAL AMOUNT is NOT shown above: DO NOT WRITE ANY GOAL AMOUNT - it was not retrieved
- If PERCENT FUNDED is NOT shown above: DO NOT WRITE ANY PERCENTAGE - it was not retrieved
- If DAYS LEFT is NOT shown above: DO NOT WRITE ANY DAYS REMAINING - it was not retrieved
- NEVER ESTIMATE OR GUESS missing data - if it's not listed above, DO NOT INCLUDE IT
- Do NOT convert dollars to yen
- Do NOT round or estimate numbers

VIOLATION EXAMPLES (WILL BE REJECTED):
- Writing "funding goal was $50,000" when GOAL AMOUNT is not listed above = REJECTED
- Writing "300% funded" when PERCENT FUNDED is not listed above = REJECTED
- Writing "10 days remaining" when DAYS LEFT is not listed above = REJECTED
- Writing "campaign is ongoing" or "campaign period is ongoing" when campaign status is unknown = REJECTED
- Writing "campaign has ended" when campaign status is unknown = REJECTED
- ANY number or status not explicitly shown in the data above = REJECTED

IMPORTANT: Do NOT write anything about campaign status (ongoing/ended/days remaining).
Simply state the funding amount and backer count, then reference the Kickstarter URL for current status.
"""
            else:
                kickstarter_data_section = f"""
=== KICKSTARTER DATA (NOT AVAILABLE) ===
Campaign data could not be retrieved automatically.

{rewards_section}

FOR SECTIONS 2 AND 3:
- Section 2 (Price): Write "For pricing details, please refer to the Kickstarter page directly"
- Section 3 (Total Funding): Write "Please check the campaign page for current funding figures"

DO NOT INVENT ANY NUMBERS OR PRICES.
"""

            # ユーザープロンプト（レポート部分のみ生成を依頼）
            combined_prompt = f"""[PRODUCT ANALYSIS REQUEST]
{translated_prompt}
{section_limit_instruction}
{kickstarter_data_section}

[JAPANESE MARKET RESEARCH DATA - THIS IS THE ONLY SOURCE OF TRUTH]
{translated_market_data}
{industry_data_section}

=== CRITICAL: DATA INTEGRITY RULES (VIOLATION = IMMEDIATE REJECTION) ===

**STEP 1: READ ALL DATA FIRST**
Before writing ANY section, you MUST read and understand ALL the market research data above.
Specifically, check if Makuake/CAMPFIRE products exist - if they do, you MUST use them as basis for Section 4 estimates.

**ABSOLUTE RULE: ONLY USE DATA EXPLICITLY PROVIDED ABOVE - NO ESTIMATION OR GUESSING**

The market research data above contains REAL numbers retrieved from actual websites.
You MUST use these EXACT numbers - do not round, estimate, or convert them.
If data is NOT shown above, it means it was NOT retrieved - DO NOT INVENT IT.

1. KICKSTARTER DATA (MOST IMPORTANT):
   - The KICKSTARTER DATA section above shows ONLY the data that was successfully retrieved
   - Use ONLY the exact values shown - nothing more, nothing less
   - If "FUNDING AMOUNT" is shown: use that EXACT number
   - If "BACKERS COUNT" is shown: use that EXACT number
   - If "GOAL AMOUNT" is NOT shown: DO NOT WRITE ANY GOAL - it was not retrieved
   - If "PERCENT FUNDED" is NOT shown: DO NOT WRITE ANY PERCENTAGE - it was not retrieved
   - If "DAYS LEFT" is NOT shown: DO NOT WRITE ANY REMAINING TIME - it was not retrieved
   - Do NOT convert dollars to yen
   - Do NOT round numbers
   - Do NOT estimate or approximate ANYTHING

2. PRICING DATA (CRITICAL FOR SECTION 2):
   - Price information is NOT automatically extracted from Kickstarter
   - DO NOT write specific prices like "Early Bird $150" or "$199 USD"
   - DO NOT invent or guess any pricing figures
   - ALWAYS write: "For detailed pricing and reward tiers, please visit the Kickstarter page: [URL]"
   - This ensures accuracy as Kickstarter prices vary by tier and may change

3. WHAT HAPPENS IF YOU INVENT DATA:
   - Writing any GOAL AMOUNT when it's not listed above = REJECTED
   - Writing any PERCENTAGE when it's not listed above = REJECTED
   - Writing any DAYS REMAINING when it's not listed above = REJECTED
   - Writing "Early Bird $199" when no reward data exists = REJECTED
   - Writing "¥15,000" as a price when no price data exists = REJECTED
   - ANY number or data not explicitly shown in the data above = REJECTED

4. MAKUAKE/CAMPFIRE DATA:
   - ONLY mention products that appear in the data above with their FULL URLs
   - If a funding amount is shown (e.g., "4,629,102円"), use that EXACT number WITH the URL
   - If no funding amount is shown, do NOT guess - just mention the product exists with its URL

5. INDUSTRY STATISTICS:
   - You may use statistics from the [VERIFIED INDUSTRY STATISTICS] section above
   - ALWAYS cite the source when using these statistics (e.g., "According to PR TIMES 2024...")
   - Do NOT invent industry statistics - only use what is provided

6. ESTIMATES AND PROJECTIONS (ABSOLUTE RULE - VIOLATION = REJECTION):
   - ALL estimates MUST be based on concrete data provided above
   - IMPORTANT: Check the MARKET RESEARCH DATA section for Makuake/CAMPFIRE products BEFORE writing Section 4
   - For crowdfunding targets in Section 4:
     * If Makuake/CAMPFIRE product data EXISTS in the market research above:
       Write: "Based on [Product Name]'s [exact amount] yen success (URL), we estimate a target of [similar or higher amount] yen"
       Example: If Duovox raised 4,629,102 yen, write "Based on Duovox Ultra Pro's 4,629,102 yen success, we estimate a target of approximately 5,000,000 yen"
     * If NO Makuake/CAMPFIRE product data exists above:
       Write: "The specific fundraising target will be determined after detailed market research, as no directly comparable products were found in Japanese crowdfunding"
   - NEVER write generic amounts like "¥10,000,000" without citing a specific product from the data above
   - For wholesale prices: Do NOT estimate specific prices - write "wholesale pricing will be discussed separately based on volume"
   - For sales projections: Only use ratios/percentages based on similar product performance with citation
   - If no similar product data exists in the MARKET RESEARCH DATA above, you MUST write "specific estimates require further market research" - do NOT invent numbers

=== OUTPUT FORMAT RULES ===
1. Write in ENGLISH ONLY (no Japanese characters)
2. Use PLAIN TEXT only (no markdown: no *, #, -, bullet points, etc.)
3. Write in natural flowing paragraphs
4. Only use blank lines between major sections (numbered sections like 1. 2. 3.)
5. For product references, ALWAYS include the full URL from the data above
6. After each section title, add a line break before the content
7. When citing industry statistics, include the source in parentheses"""

            print(f"  🤖 Calling OpenAI API with translated prompts...")

            # システムプロンプトを構築
            # 設定シートの内容を主に使用し、コードからのデフォルトは最小限にする

            # 最小限の基本ルール（設定シートで上書き可能）
            base_system_prompt = """You are a professional Japanese market entry consultant writing a report.

BASIC OUTPUT RULES:
1. Write in English only (no Japanese characters except in product names)
2. Plain text only - no markdown formatting
3. Each section title must be followed by a line break
4. You are writing the report section only - no greetings, no signatures"""

            # システムプロンプトを結合：基本ルール → システム設定（G2）→ 共通プロンプト（A2）
            system_parts = [base_system_prompt]
            if translated_system_settings:
                print(f"  📋 Using system settings from G2 ({len(translated_system_settings)} chars)")
                system_parts.append(translated_system_settings)
            if translated_common_prompt:
                print(f"  📋 Using common prompt from A2 ({len(translated_common_prompt)} chars)")
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

            # セクション数を強制的に制限（AIが指示を守らない場合のバックアップ）
            if section_count > 0:
                generated_report = self._enforce_section_limit(generated_report, section_count)

            # 最適化: リファインと検証のAPI呼び出しを削除（処理時間を大幅に短縮）
            # 以前は3段階（生成→リファイン→検証）だったが、1段階（生成のみ）に変更
            # 品質はシステムプロンプトで担保
            validated_report = generated_report
            print(f"  ⚡ Skipping refine/validate steps for speed optimization")

            # デバッグ用：生成されたレポートの最初の部分を出力
            print("\n" + "=" * 60)
            print("DEBUG: 生成されたレポート（最初の500文字）")
            print("=" * 60)
            print(validated_report[:500])
            print("..." if len(validated_report) > 500 else "")
            print("=" * 60 + "\n")

            # 後処理: 件名行を削除、マークダウンリンクをプレーンテキストに変換
            generated_report = self._clean_generated_body(validated_report)

            # 最終URL修正
            generated_report = self._fix_urls(generated_report)

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

            # 最終的なURL修正（結合後）
            final_body = self._fix_urls(final_body)

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
            refine_prompt = f"""You are an editor reviewing a market report. Your ONLY job is to improve the writing style - NOT to change any data.

ORIGINAL REPORT:
{report}

EDIT THIS REPORT following these rules:

=== ABSOLUTE RESTRICTION - DATA INTEGRITY ===
You MUST NOT change ANY numbers, amounts, or figures in this report.
- If the report says "$606,041" - keep it as "$606,041"
- If the report says "2,903 backers" - keep it as "2,903 backers"
- If the report says "4,629,102円" - keep it as "4,629,102円"
- DO NOT convert currencies (don't turn dollars into yen)
- DO NOT invent new numbers
- DO NOT add prices, funding amounts, or statistics that aren't in the original

=== STYLE IMPROVEMENTS (what you CAN do) ===
1. Replace AI-sounding phrases with natural alternatives:
   - "aligns with" → "matches", "fits"
   - "leverage" → "use"
   - "utilize" → "use"
   - "robust", "comprehensive", "strategic" → remove or be specific

2. Remove template texts:
   - "Company & Performance References"
   - "宜しくお願い致します"

3. Make the voice more direct:
   - "I recommend..." not "It would be advisable to..."

4. Add line break after section titles:
   WRONG: "1. Product Features: The product is..."
   RIGHT: "1. Product Features:\nThe product is..."

=== KEEP UNCHANGED ===
- ALL URLs - do not modify any URL
- ALL numbers, amounts, currencies, figures
- ALL product names
- Section structure

Output the edited report only, no explanations."""

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

    def _validate_and_fix_report(self, report, market_data):
        """
        レポートの品質を検証し、問題があれば修正

        Args:
            report (str): 生成されたレポート
            market_data (str): 市場調査データ

        Returns:
            str: 検証・修正されたレポート
        """
        if not self.api_available or not report:
            return report

        import re

        print(f"  🔍 Validating report quality...")

        # 問題点を検出
        issues = []

        # 1. URL形式の問題を検出
        # https://が欠落しているURL
        broken_urls = re.findall(r'(?<![/:])((?:www\.)?(?:kickstarter\.com|makuake\.com|camp-fire\.jp)[^\s<>"]*)', report)
        if broken_urls:
            issues.append(f"Broken URLs found (missing https://): {broken_urls[:3]}")

        # 2. 「No data available」が不適切なセクションにあるか検出
        # 分析・考察セクション（データ不要）で「No data available」は不適切
        analysis_sections = [
            (r'7\.\s*(?:Challenges|課題)[^:]*:\s*\n?\s*No data available', 'Section 7 (Challenges) should have analysis, not "No data available"'),
            (r'10\.\s*(?:Potential|可能性)[^:]*:\s*\n?\s*No data available', 'Section 10 (Potential) should have analysis, not "No data available"'),
            (r'13\.\s*(?:Potential|可能性)[^:]*:\s*\n?\s*No data available', 'Section 13 (Potential for Wholesale) should have analysis'),
            (r'14\.\s*(?:Necessity|必要性)[^:]*Exclusive[^:]*:\s*\n?\s*No data available', 'Section 14 (Exclusive Sales) should explain the concept'),
            (r'15\.\s*(?:Necessity|必要性)[^:]*PSE[^:]*:\s*\n?\s*No data available', 'Section 15 (PSE) should explain certification requirements'),
        ]

        for pattern, issue_desc in analysis_sections:
            if re.search(pattern, report, re.IGNORECASE):
                issues.append(issue_desc)

        # 3. セクション内容が極端に短い（3文未満）
        sections = re.split(r'\n\d+\.\s+', report)
        for i, section in enumerate(sections[1:], 1):  # 最初の空要素をスキップ
            sentences = [s.strip() for s in re.split(r'[.!?。！？]', section) if s.strip() and len(s.strip()) > 10]
            if len(sentences) < 2 and 'No data available' not in section:
                issues.append(f"Section {i} is too short (less than 2 sentences)")

        if not issues:
            print(f"  ✓ Report validation passed")
            # URLの修正だけ行う
            report = self._fix_urls(report)
            return report

        print(f"  ⚠️ Found {len(issues)} issues, requesting fix...")
        for issue in issues[:5]:
            print(f"    - {issue}")

        # 問題を修正するためのAPI呼び出し
        try:
            fix_prompt = f"""You are reviewing a market analysis report that has quality issues.

CURRENT REPORT:
{report}

MARKET RESEARCH DATA AVAILABLE:
{market_data}

ISSUES FOUND:
{chr(10).join(f'- {issue}' for issue in issues)}

=== FIX INSTRUCTIONS ===

1. FOR ANALYSIS/STRATEGY SECTIONS (7, 10, 13, 14, 15):
   These sections require ANALYSIS and EXPLANATION, not just data.
   - Section 7 (Challenges): Analyze potential challenges in the Japanese market
   - Section 10 (E-commerce Potential): Explain factors that could lead to success
   - Section 13 (Wholesale Potential): Explain how to approach Japanese retailers
   - Section 14 (Exclusive Sales): Explain why exclusive agreements matter in Japan
   - Section 15 (PSE Certification): Explain PSE requirements for this product category

   DO NOT write "No data available" for these sections.
   Instead, provide thoughtful analysis based on the product type and Japanese market knowledge.

2. FOR DATA-DEPENDENT SECTIONS (5, 6, 8, 9, 11, 12):
   If no data is available, it's OK to say "Currently no data available."
   But if data exists in MARKET RESEARCH DATA, use it with URLs.

3. SHORT SECTIONS:
   Each section should have at least 3-5 sentences of meaningful content.

4. URL FORMAT:
   All URLs must start with https://
   Fix any URLs that are missing the protocol.

5. CONSISTENCY:
   Both products should have the same level of detail and quality.
   If one product has detailed analysis, the other should too.

=== OUTPUT ===
Output the COMPLETE fixed report. Keep all section numbers and structure intact.
Write in English only. No markdown formatting."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quality assurance editor for business reports. Fix the identified issues while maintaining data integrity."
                    },
                    {
                        "role": "user",
                        "content": fix_prompt
                    }
                ],
                max_tokens=16000,
                temperature=0.3
            )

            fixed_report = response.choices[0].message.content.strip()
            print(f"  ✓ Report issues fixed ({len(fixed_report)} chars)")

            # URL形式の最終修正
            fixed_report = self._fix_urls(fixed_report)

            return fixed_report

        except Exception as e:
            print(f"  ⚠️ Fix failed, using original with URL fixes: {e}")
            return self._fix_urls(report)

    def _enforce_section_limit(self, report, max_sections):
        """
        レポートのセクション数を強制的に制限

        Args:
            report (str): 生成されたレポート
            max_sections (int): 最大セクション数

        Returns:
            str: セクション数が制限されたレポート
        """
        import re

        # セクションの開始位置を検出（1. 2. 3. などのパターン）
        # 行頭または空白の後に数字+ピリオドが来るパターン
        section_pattern = r'(?:^|\n)(\d+)\.\s+'
        matches = list(re.finditer(section_pattern, report))

        if not matches:
            print(f"  ⚠️ No numbered sections found in report")
            return report

        # 現在のセクション数をカウント
        section_numbers = [int(m.group(1)) for m in matches]
        current_sections = max(section_numbers) if section_numbers else 0

        print(f"  📊 Found {len(matches)} section markers, max section number: {current_sections}")

        if current_sections <= max_sections:
            print(f"  ✓ Section count OK ({current_sections} <= {max_sections})")
            return report

        # 制限を超えるセクションを削除
        print(f"  ⚠️ Trimming sections: {current_sections} -> {max_sections}")

        # max_sections + 1 以降のセクションの開始位置を見つける
        cutoff_position = None
        for match in matches:
            section_num = int(match.group(1))
            if section_num > max_sections:
                cutoff_position = match.start()
                # 改行の前の位置を取得
                if report[cutoff_position] == '\n':
                    cutoff_position += 0  # そのまま
                break

        if cutoff_position is not None:
            trimmed_report = report[:cutoff_position].rstrip()
            print(f"  ✓ Report trimmed from {len(report)} to {len(trimmed_report)} chars")
            return trimmed_report

        return report

    def _fix_urls(self, text):
        """
        URLの形式を修正

        Args:
            text (str): テキスト

        Returns:
            str: URL修正後のテキスト
        """
        import re

        # https://が欠落しているURLを包括的に修正
        # 否定先読みでhttps://やhttp://が既にある場合はスキップ

        # kickstarter.com → https://www.kickstarter.com
        # www.kickstarter.com → https://www.kickstarter.com
        text = re.sub(
            r'(?<!https://)(?<!http://)(?<!/)(?:www\.)?kickstarter\.com(/[^\s<>"\']*)?',
            r'https://www.kickstarter.com\1',
            text
        )

        # makuake.com → https://www.makuake.com
        # www.makuake.com → https://www.makuake.com
        text = re.sub(
            r'(?<!https://)(?<!http://)(?<!/)(?:www\.)?makuake\.com(/[^\s<>"\']*)?',
            r'https://www.makuake.com\1',
            text
        )

        # camp-fire.jp → https://camp-fire.jp
        text = re.sub(
            r'(?<!https://)(?<!http://)(?<!/)camp-fire\.jp(/[^\s<>"\']*)?',
            r'https://camp-fire.jp\1',
            text
        )

        # 重複したhttps://を修正
        text = re.sub(r'https://https://', r'https://', text)
        text = re.sub(r'https://www\.https://', r'https://', text)

        # URLの末尾のピリオドやカンマを削除
        text = re.sub(r'(https://[^\s<>"\']+)[.,](?=[\s<>"\']|$)', r'\1', text)

        # 余分なwww.www.を修正
        text = re.sub(r'https://www\.www\.', r'https://www.', text)

        return text

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
