#!/usr/bin/env python3
"""
Kickstarter市場分析レポート自動生成
テンプレートシート + OpenAI API対応版
"""

import os
import time
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient
from report_generator import ReportGenerator

# .envファイルを読み込み
load_dotenv()

def main():
    """
    メイン処理
    1. Google Sheetsから未処理の行を取得
    2. 各行のテンプレートを読み込み
    3. テンプレートに基づいてレポート生成（プロンプトがあればOpenAI API使用）
    4. Google Sheetsに書き込み
    """
    # 環境変数を取得
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return

    print("=" * 80)
    print("Kickstarter市場分析レポート自動生成")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheet Name: {sheet_name}\n")

    # Google Sheetsクライアントを初期化
    print("Google Sheets認証中...")
    sheets_client = GoogleSheetsClient(spreadsheet_id, sheet_name)
    print("✓ 認証成功！\n")

    # レポート生成器を初期化
    print("レポート生成器を初期化中...")
    report_generator = ReportGenerator(api_key=openai_api_key)
    if report_generator.api_available:
        print(f"✓ OpenAI API利用可能（モデル: {report_generator.model}）")
    else:
        print("⚠️  OpenAI APIキーが未設定 - テンプレート本文をそのまま使用します")
    print()

    # 共通プロンプトとシステム設定を取得
    # 主要な設定: A2（共通プロンプト）、G2（システム設定）、L列（業界データ）
    print("設定を読み込み中...")
    common_prompt = sheets_client.get_common_prompt()
    system_settings = sheets_client.get_system_settings()
    translation_rules = sheets_client.get_translation_rules()
    output_format_rules = sheets_client.get_output_format_rules()
    industry_data = sheets_client.get_industry_data()
    print()

    # 未処理の行を取得
    print("未処理の行を検索中...")
    unprocessed_rows = sheets_client.get_unprocessed_rows()
    print(f"✓ {len(unprocessed_rows)} 件の未処理URLを発見\n")

    if not unprocessed_rows:
        print("未処理のURLはありません。")
        print("\n次の手順:")
        print("1. スプレッドシートのB列（product_url）にKickstarter URLを追加")
        print("2. C列（template）からテンプレートを選択")
        print("3. 再度このスクリプトを実行")
        return

    # 各行を処理
    for i, row_data in enumerate(unprocessed_rows, 1):
        # 2番目以降のアイテムを処理する前に遅延を入れる（念のため）
        # ブラウザリセットで主な対策済みだが、安全マージンとして10秒待機
        if i > 1:
            delay_seconds = 10
            print(f"\n⏳ 次の処理まで {delay_seconds} 秒待機中...")
            time.sleep(delay_seconds)

        print("\n" + "=" * 80)
        print(f"処理中 ({i}/{len(unprocessed_rows)})")
        print("=" * 80)
        print(f"行番号: {row_data['row_number']}")
        print(f"URL: {row_data['url']}")
        print(f"テンプレート: {row_data['template']}")

        # テンプレートが選択されているか確認
        if not row_data['template']:
            print("⚠️  テンプレートが選択されていません。スキップします。")
            continue

        try:
            # テンプレートを読み込み
            template = sheets_client.read_template(row_data['template'])

            if not template:
                print(f"❌ テンプレート '{row_data['template']}' の読み込みに失敗しました。")
                continue

            # レポート生成
            report = report_generator.generate_report(
                template,
                row_data['url'],
                product_name=row_data.get('name', ''),
                common_prompt=common_prompt,
                system_settings=system_settings,
                translation_rules=translation_rules,
                output_format_rules=output_format_rules,
                industry_data=industry_data
            )

            # Google Sheetsに書き込み
            print(f"\n📝 Google Sheetsに書き込み中...")
            sheets_client.write_report(
                row_data['row_number'],
                jp_subject=report['jp_subject'],
                en_subject=report['en_subject'],
                japanese_body=report['jp_body'],
                english_body=report['en_body']
            )
            print(f"✓ 書き込み完了！")

            # Kickstarterのボット検出を回避するため、ブラウザセッションをリセット
            # 同一セッションでの連続アクセスがブロックされるため、各商品処理後にリセットする
            report_generator.reset_browser()

        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

            # エラー状態を記録
            try:
                sheets_client.write_report(
                    row_data['row_number'],
                    jp_subject=f"エラー",
                    en_subject=f"Error",
                    japanese_body=f"エラー: {str(e)}",
                    english_body=f"Error: {str(e)}"
                )
            except:
                pass

            # エラー時もブラウザをリセット
            report_generator.reset_browser()

            continue

    print("\n" + "=" * 80)
    print("✅ 全ての処理が完了しました！")
    print("=" * 80)

if __name__ == '__main__':
    main()
