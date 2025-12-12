#!/usr/bin/env python3
"""
Kickstarter Market Analyzer V2 - 統合スクリプト

Phase 1: データ収集（DataCollector）
Phase 2: 収支計算（CalculationEngine）
Phase 3: レポート生成（ReportGeneratorV2）

使用方法:
    python analyzer_v2.py <kickstarter_url>
    python analyzer_v2.py --test  # テストモード
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

from data_collector import DataCollector
from calculation_engine import CalculationEngine
from report_generator_v2 import ReportGeneratorV2


class KickstarterAnalyzerV2:
    """
    Kickstarter製品の日本市場参入分析

    3フェーズで処理:
    1. データ収集: Kickstarter, Kicktraq, BackerKit, Amazon, Makuake, CAMPFIRE
    2. 収支計算: FOB推定、シミュレーション、損益分岐点
    3. レポート生成: 15項目評価レポート
    """

    def __init__(self, openai_api_key=None):
        """
        Args:
            openai_api_key: OpenAI APIキー
        """
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')

        # モジュール初期化
        self.collector = DataCollector(openai_api_key=self.openai_api_key)
        self.report_generator = ReportGeneratorV2(
            api_key=self.openai_api_key,
            model='gpt-4o'  # 高品質なレポート生成のためgpt-4oを使用
        )

        # 結果格納
        self.collected_data = None
        self.calculation_results = None
        self.report = None

    def analyze(self, kickstarter_url, product_keywords=None, output_dir=None):
        """
        完全分析を実行

        Args:
            kickstarter_url: KickstarterのURL
            product_keywords: 検索キーワード（Noneの場合は自動抽出）
            output_dir: 出力ディレクトリ（Noneの場合はカレント）

        Returns:
            str: 生成されたレポート
        """
        print("\n" + "=" * 70)
        print("🚀 Kickstarter Market Analyzer V2")
        print("=" * 70)
        print(f"URL: {kickstarter_url}")
        print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Phase 1: データ収集
        print("\n" + "=" * 70)
        print("📥 Phase 1: データ収集")
        print("=" * 70)
        self.collected_data = self.collector.collect_all(
            kickstarter_url,
            product_keywords=product_keywords
        )

        # 収集結果サマリー
        print("\n【収集結果サマリー】")
        for key, value in self.collector.get_summary().items():
            print(f"  {key}: {value}")

        # Phase 2: 収支計算
        print("\n" + "=" * 70)
        print("🧮 Phase 2: 収支計算")
        print("=" * 70)
        calc_engine = CalculationEngine(self.collected_data)
        self.calculation_results = calc_engine.calculate_all()

        # Phase 3: レポート生成
        print("\n" + "=" * 70)
        print("📝 Phase 3: レポート生成")
        print("=" * 70)
        self.report = self.report_generator.generate_report(
            self.collected_data,
            self.calculation_results
        )

        # 結果出力
        if output_dir:
            self._save_results(output_dir, kickstarter_url)

        print("\n" + "=" * 70)
        print("✅ 分析完了")
        print("=" * 70)
        print(f"終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return self.report

    def _save_results(self, output_dir, kickstarter_url):
        """結果をファイルに保存"""
        os.makedirs(output_dir, exist_ok=True)

        # タイムスタンプ
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # プロジェクト名を抽出
        project_name = kickstarter_url.split('/')[-1][:30].replace('-', '_')

        # 収集データ（JSON）
        collected_path = os.path.join(output_dir, f"{timestamp}_{project_name}_data.json")
        with open(collected_path, 'w', encoding='utf-8') as f:
            json.dump(self.collected_data, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 収集データ: {collected_path}")

        # 計算結果（JSON）
        calc_path = os.path.join(output_dir, f"{timestamp}_{project_name}_calc.json")
        with open(calc_path, 'w', encoding='utf-8') as f:
            json.dump(self.calculation_results, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 計算結果: {calc_path}")

        # レポート（TXT）
        report_path = os.path.join(output_dir, f"{timestamp}_{project_name}_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.report)
        print(f"  ✓ レポート: {report_path}")


def main():
    """メイン関数"""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='Kickstarter製品の日本市場参入分析ツール V2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 単一URL分析
  python analyzer_v2.py https://www.kickstarter.com/projects/xxx/product-name

  # キーワード指定
  python analyzer_v2.py https://www.kickstarter.com/projects/xxx/product-name --keywords "MAXPRO" "fitness"

  # 出力ディレクトリ指定
  python analyzer_v2.py https://www.kickstarter.com/projects/xxx/product-name --output ./reports

  # テストモード
  python analyzer_v2.py --test
        """
    )
    parser.add_argument('url', nargs='?', help='Kickstarter URL')
    parser.add_argument('--keywords', '-k', nargs='+', help='検索キーワード（指定しない場合は自動抽出）')
    parser.add_argument('--output', '-o', help='出力ディレクトリ', default='./analysis_results')
    parser.add_argument('--test', '-t', action='store_true', help='テストモード（サンプルURLで実行）')
    parser.add_argument('--no-save', action='store_true', help='ファイル保存をスキップ')

    args = parser.parse_args()

    # テストモード
    if args.test:
        args.url = "https://www.kickstarter.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear"
        # キーワードは自動抽出（Kickstarterの製品名を使用）
        args.keywords = None
        print("🧪 テストモード: MAXPROプロジェクトで実行（キーワード自動抽出）")

    # URL必須チェック
    if not args.url:
        parser.print_help()
        print("\n❌ エラー: Kickstarter URLを指定してください")
        sys.exit(1)

    # API keyチェック
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️ 警告: OPENAI_API_KEY が設定されていません")
        print("   レポート生成にはAPIキーが必要です")

    # 分析実行
    analyzer = KickstarterAnalyzerV2()

    try:
        report = analyzer.analyze(
            kickstarter_url=args.url,
            product_keywords=args.keywords,
            output_dir=None if args.no_save else args.output
        )

        # レポート表示（最初の部分）
        print("\n" + "=" * 70)
        print("【生成レポート（プレビュー）】")
        print("=" * 70)
        preview_length = 5000
        if len(report) > preview_length:
            print(report[:preview_length])
            print(f"\n... (以下省略、全{len(report):,}文字)")
        else:
            print(report)

    except KeyboardInterrupt:
        print("\n\n⚠️ 中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
