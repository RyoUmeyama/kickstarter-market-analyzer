#!/usr/bin/env python3
"""
kickstarterシートの列名を更新
jp_report, en_report → jp_body, en_body
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

def update_column_names():
    """
    kickstarterシートのヘッダー行を更新
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("kickstarterシート列名更新")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheet Name: {sheet_name}\n")

    try:
        # Google Sheetsクライアントを初期化
        print("認証中...")
        client = GoogleSheetsClient(spreadsheet_id, sheet_name)
        print("✓ 認証成功！\n")

        # 新しいヘッダー行
        new_headers = [
            'NO',           # A
            'product_url',  # B
            'template',     # C
            'name',         # D
            'to_email',     # E
            'jp_subject',   # F
            'en_subject',   # G
            'status',       # H
            'jp_body',      # I（変更: jp_report → jp_body）
            'en_body'       # J（変更: en_report → en_body）
        ]

        print("新しいヘッダー行:")
        for i, header in enumerate(new_headers):
            col_letter = chr(65 + i)
            print(f"  {col_letter}列: {header}")
        print()

        # ヘッダー行を更新
        print("ヘッダー行を更新中...")

        # A1:J1の範囲にヘッダーを書き込み
        range_name = f'{sheet_name}!A1:J1'
        body = {
            'values': [new_headers]
        }

        client.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        print("✓ ヘッダー行の更新が完了しました！\n")

        print("=" * 80)
        print("✅ 完了！")
        print("=" * 80)
        print("\n変更内容:")
        print("  I列: jp_report → jp_body")
        print("  J列: en_report → en_body")
        print("\nメールマージで使用する際の変数名:")
        print("  件名: {{jp_subject}} または {{en_subject}}")
        print("  本文: {{jp_body}} または {{en_body}}")
        print("  送信先: {{to_email}}")

        return True

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_column_names()
    exit(0 if success else 1)
