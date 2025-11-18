#!/usr/bin/env python3
"""
kickstarterシートの列構成を更新
件名列（jp_subject, en_subject）を追加
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

def update_sheet_structure():
    """
    kickstarterシートのヘッダー行を更新

    旧構成: A=NO, B=product_url, C=template, D=name, E=to_email, F=subject, G=status, H=jp_report, I=en_report
    新構成: A=NO, B=product_url, C=template, D=name, E=to_email, F=jp_subject, G=en_subject, H=status, I=jp_report, J=en_report
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("kickstarterシート構造更新")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheet Name: {sheet_name}\n")

    try:
        # Google Sheetsクライアントを初期化
        print("認証中...")
        client = GoogleSheetsClient(spreadsheet_id, sheet_name)
        print("✓ 認証成功！\n")

        # 現在のヘッダー行を読み取り
        print("現在のヘッダー行を確認中...")
        rows = client.read_rows(sheet_name=sheet_name, column_range='A:J')

        if len(rows) > 0:
            print("現在のヘッダー行:")
            for i, header in enumerate(rows[0]):
                col_letter = chr(65 + i)
                print(f"  {col_letter}列: {header}")
            print()

        # 新しいヘッダー行
        new_headers = [
            'NO',           # A
            'product_url',  # B
            'template',     # C
            'name',         # D
            'to_email',     # E
            'jp_subject',   # F（新規）
            'en_subject',   # G（新規）
            'status',       # H
            'jp_report',    # I
            'en_report'     # J
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
        print("\n注意事項:")
        print("1. 既存データがある場合、F列（jp_subject）とG列（en_subject）は空欄です")
        print("2. main.pyを実行すると、テンプレートから件名が自動的に取得されます")
        print("3. H列以降のデータ（status, jp_report, en_report）が1列ずつ右にシフトします")
        print("4. 既存データがある場合は手動で調整が必要です")

        return True

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_sheet_structure()
    exit(0 if success else 1)
