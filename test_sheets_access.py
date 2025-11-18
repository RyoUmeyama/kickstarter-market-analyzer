#!/usr/bin/env python3
"""
Google Sheets アクセステスト
既存のスプレッドシートに新しいシート（タブ）を追加してアクセスできるか確認
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

def test_sheets_access():
    """
    Google Sheetsへのアクセスをテスト
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("Google Sheets アクセステスト")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheet Name: {sheet_name}\n")

    try:
        # Google Sheetsクライアントを初期化（認証が実行される）
        print("認証中...")
        client = GoogleSheetsClient(spreadsheet_id, sheet_name)
        print("✓ 認証成功！\n")

        # 全行を読み取り
        print(f"シート '{sheet_name}' からデータを読み取り中...")
        rows = client.read_rows()
        print(f"✓ {len(rows)} 行を読み取りました\n")

        # ヘッダー行を表示
        if len(rows) > 0:
            print("ヘッダー行（1行目）:")
            headers = rows[0]
            for i, header in enumerate(headers, 1):
                col_letter = chr(64 + i)
                print(f"  {col_letter}列: {header}")
            print()

        # 未処理行を取得
        print("未処理の行を検索中...")
        unprocessed = client.get_unprocessed_rows()
        print(f"✓ {len(unprocessed)} 件の未処理URLを発見\n")

        if unprocessed:
            print("未処理URL（最初の5件）:")
            for i, item in enumerate(unprocessed[:5], 1):
                print(f"  {i}. Row {item['row_number']}: {item['url'][:60]}...")
        else:
            print("未処理のURLはありません。")
            print("\n次の手順:")
            print("1. スプレッドシートのB列（product_url）にKickstarter URLを追加")
            print("2. 再度このスクリプトを実行")

        print("\n" + "=" * 80)
        print("✅ テスト成功！Google Sheetsにアクセスできました")
        print("=" * 80)
        return True

    except FileNotFoundError as e:
        print(f"\n❌ エラー: {e}")
        print("\n次の手順:")
        print("1. setup_auth_quick.md の手順に従って credentials.json を取得")
        print("2. credentials.json をこのディレクトリに配置")
        print("3. 再度このスクリプトを実行")
        return False

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        return False


if __name__ == '__main__':
    success = test_sheets_access()
    exit(0 if success else 1)
