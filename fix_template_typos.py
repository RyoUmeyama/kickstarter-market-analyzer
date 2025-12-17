#!/usr/bin/env python3
"""
スプレッドシートのテンプレート誤字を修正するスクリプト
"""

import os
import json
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# .envファイルを読み込み
load_dotenv()

# 修正対象の誤字リスト
TYPO_FIXES = [
    ("成功を覚悟する", "成功を目指す"),
    ("OMP]", "OMP"),
    # 他の誤字があれば追加
]

# テンプレートシート名
TEMPLATE_SHEETS = [
    "①1回目送信文",
    "②2回目送信文",
    "③3回目送信文",
    "④4回目送信文",
    "⑤5回目送信文",
]

def get_sheets_service():
    """Google Sheets APIサービスを取得"""
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON環境変数が設定されていません")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=creds)


def read_sheet(service, spreadsheet_id, sheet_name, range_str):
    """シートからデータを読み取る"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!{range_str}"
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f"  ❌ 読み取りエラー ({sheet_name}): {e}")
        return []


def update_cell(service, spreadsheet_id, sheet_name, cell, value):
    """セルを更新する"""
    try:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!{cell}",
            valueInputOption='RAW',
            body={'values': [[value]]}
        ).execute()
        return True
    except Exception as e:
        print(f"  ❌ 更新エラー ({sheet_name}!{cell}): {e}")
        return False


def fix_typos_in_text(text):
    """テキスト内の誤字を修正"""
    if not text:
        return text, []

    fixed = text
    applied_fixes = []

    for old, new in TYPO_FIXES:
        if old in fixed:
            fixed = fixed.replace(old, new)
            applied_fixes.append((old, new))

    return fixed, applied_fixes


def main():
    print("=" * 60)
    print("テンプレート誤字修正スクリプト")
    print("=" * 60)

    spreadsheet_id = os.getenv('SPREADSHEET_ID', '1Xv7YF2prMHpWDc1lTLWcp8JjkkU9u2KoyspFI-eBoQw')

    print(f"\nSpreadsheet ID: {spreadsheet_id}")
    print(f"修正対象の誤字: {len(TYPO_FIXES)}件")
    for old, new in TYPO_FIXES:
        print(f"  - 「{old}」→「{new}」")

    print("\n[1/2] Google Sheets APIに接続中...")
    try:
        service = get_sheets_service()
        print("  ✓ 接続成功")
    except Exception as e:
        print(f"  ❌ 接続エラー: {e}")
        return

    print("\n[2/2] テンプレートシートを確認・修正中...")

    total_fixes = 0

    for sheet_name in TEMPLATE_SHEETS:
        print(f"\n  📄 {sheet_name}")

        # A1:B3の範囲を読み取り（件名、本文、プロンプト）
        rows = read_sheet(service, spreadsheet_id, sheet_name, "A1:B3")

        if not rows:
            print(f"    ⚠️ データなし or 読み取りエラー")
            continue

        # セルの位置マッピング
        cell_mapping = [
            (0, 0, "A1", "en_subject"),
            (0, 1, "B1", "jp_subject"),
            (1, 0, "A2", "en_body"),
            (1, 1, "B2", "jp_body"),
            (2, 0, "A3", "en_prompt"),
            (2, 1, "B3", "jp_prompt"),
        ]

        sheet_fixes = 0

        for row_idx, col_idx, cell, label in cell_mapping:
            if row_idx >= len(rows):
                continue
            if col_idx >= len(rows[row_idx]):
                continue

            original = rows[row_idx][col_idx]
            fixed, applied = fix_typos_in_text(original)

            if applied:
                print(f"    ✏️ {cell} ({label}): ", end="")
                for old, new in applied:
                    print(f"「{old}」→「{new}」 ", end="")
                print()

                # 更新を実行
                if update_cell(service, spreadsheet_id, sheet_name, cell, fixed):
                    print(f"      ✓ 更新完了")
                    sheet_fixes += len(applied)
                else:
                    print(f"      ❌ 更新失敗")

        if sheet_fixes == 0:
            print(f"    ✓ 誤字なし")
        else:
            total_fixes += sheet_fixes

    print("\n" + "=" * 60)
    if total_fixes > 0:
        print(f"✅ 完了: {total_fixes}件の誤字を修正しました")
    else:
        print("✅ 完了: 修正対象の誤字は見つかりませんでした")
    print("=" * 60)


if __name__ == '__main__':
    main()
