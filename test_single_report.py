#!/usr/bin/env python3
"""
単一製品のレポート生成テスト
ワークフローを実行せずにローカルでレポート品質を確認
"""

import os
import json
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

from data_collector import DataCollector
from calculation_engine import CalculationEngine
from report_generator_v2 import ReportGeneratorV2
from web_researcher import WebResearcher
from industry_analyzer import IndustryAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from strict_evaluator import StrictEvaluator


def test_single_report(kickstarter_url):
    """単一製品のレポートを生成してテスト"""

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEYが設定されていません")
        return None

    print("=" * 60)
    print("🧪 単一製品レポート生成テスト")
    print("=" * 60)
    print(f"URL: {kickstarter_url}")
    print()

    try:
        # Phase 1: データ収集
        print("📥 Phase 1: データ収集...")
        collector = DataCollector()
        raw_data = collector.collect_all(kickstarter_url)

        if not raw_data or raw_data.get('error'):
            error_msg = raw_data.get('error', 'データ収集に失敗') if raw_data else 'データ収集に失敗'
            print(f"  ❌ {error_msg}")
            return None

        # Phase 1.5: Web調査
        print("🔍 Phase 1.5: Web調査...")
        researcher = WebResearcher(api_key=api_key)
        product_name = raw_data.get('kickstarter', {}).get('title', '')
        product_description = raw_data.get('kickstarter', {}).get('description', '')
        web_research = researcher.research_product(kickstarter_url, product_name, product_description)
        raw_data['web_research'] = web_research

        # Phase 2: 収支計算
        print("📊 Phase 2: 収支計算...")
        calc_engine = CalculationEngine(raw_data)
        calculations = calc_engine.calculate_all()

        # Phase 2.5: 業界分析
        print("🏭 Phase 2.5: 業界分析...")
        industry_analyzer = IndustryAnalyzer(api_key=api_key)
        industry_analysis = industry_analyzer.analyze(web_research, raw_data)

        # Phase 2.6: 競合分析
        print("🎯 Phase 2.6: 競合分析...")
        competitor_analyzer = CompetitorAnalyzer(api_key=api_key)
        competitor_analysis = competitor_analyzer.analyze(web_research, calculations)

        # Phase 2.7: 厳格評価
        print("⚠️ Phase 2.7: 厳格評価...")
        strict_evaluator = StrictEvaluator(api_key=api_key)
        strict_evaluation = strict_evaluator.evaluate(web_research, calculations, industry_analysis, competitor_analysis)

        # Phase 3: レポート生成
        print("📝 Phase 3: レポート生成...")
        report_gen = ReportGeneratorV2(api_key=api_key)
        report_text = report_gen.generate_report(raw_data, calculations)

        print()
        print("=" * 60)
        print("✅ レポート生成完了")
        print("=" * 60)
        print(f"レポート長: {len(report_text):,}文字")
        print()

        # レポートの品質チェック
        print("=" * 60)
        print("🔍 品質チェック")
        print("=" * 60)

        issues = []

        # エグゼクティブサマリーの確認
        if "【エグゼクティブサマリー】" in report_text:
            print("✅ エグゼクティブサマリー: あり")
        else:
            print("❌ エグゼクティブサマリー: なし")
            issues.append("エグゼクティブサマリーがありません")

        # セクション番号の確認
        for i in range(1, 17):
            section_marker = f"① ② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨ ⑩ ⑪ ⑫ ⑬ ⑭ ⑮ ⑯".split()[i-1]
            if section_marker in report_text:
                print(f"✅ セクション{section_marker}: あり")
            else:
                print(f"❌ セクション{section_marker}: なし")
                issues.append(f"セクション{section_marker}がありません")

        # 達成率0%の確認
        if "達成率: 0%" in report_text or "達成率0%" in report_text:
            print("⚠️ 達成率0%が含まれています（要確認）")
            issues.append("達成率0%が含まれています")
        else:
            print("✅ 達成率0%問題: なし")

        # エラーメッセージの確認
        error_phrases = ["目標額データ取得失敗", "海外IP制限", "データ取得失敗"]
        for phrase in error_phrases:
            if phrase in report_text:
                print(f"❌ エラーメッセージ検出: {phrase}")
                issues.append(f"エラーメッセージ「{phrase}」が含まれています")

        print()
        if issues:
            print(f"⚠️ {len(issues)}件の問題が検出されました")
        else:
            print("✅ 品質チェック完了（問題なし）")

        # レポート内容を出力
        print()
        print("=" * 60)
        print("📄 生成されたレポート（最初の3000文字）")
        print("=" * 60)
        print(report_text[:3000])
        if len(report_text) > 3000:
            print(f"\n... (残り {len(report_text) - 3000:,}文字)")

        # レポートをファイルに保存
        output_file = "/tmp/test_report_output.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"\n📁 完全なレポートを保存: {output_file}")

        return report_text

    except Exception as e:
        import traceback
        print(f"❌ エラー: {e}")
        traceback.print_exc()
        return None


if __name__ == '__main__':
    import sys

    # テスト用URL（引数があればそれを使用）
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        # デフォルトのテストURL
        test_url = "https://www.kickstarter.com/projects/akaso/sight-300-the-most-advanced-ai-night-vision"

    test_single_report(test_url)
