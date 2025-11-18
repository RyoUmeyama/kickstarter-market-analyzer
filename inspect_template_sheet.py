#!/usr/bin/env python3
"""
テンプレートシートの構造を確認
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

def inspect_template():
    """
    テンプレートシート（①1回目送信文）の構造を確認
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("テンプレートシート構造確認")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}\n")

    try:
        # Google Sheetsクライアントを初期化
        print("認証中...")
        client = GoogleSheetsClient(spreadsheet_id, 'kickstarter')
        print("✓ 認証成功！\n")

        # テンプレートシート名
        template_name = "①1回目送信文"

        print(f"テンプレートシート: {template_name}")
        print("-" * 80)

        # 最初の10行を取得して構造を確認
        rows = client.read_rows(sheet_name=template_name, column_range='A:Z')

        if not rows:
            print("❌ データが見つかりません")
            return False

        # 1行目: 件名
        print("\n1行目（件名）:")
        if len(rows) > 0:
            row1 = rows[0]
            print(f"  A1（英語件名）: {row1[0] if len(row1) > 0 else '(空)'}")
            print(f"  B1（日本語件名）: {row1[1] if len(row1) > 1 else '(空)'}")

        # 2行目: 本文
        print("\n2行目（本文）:")
        if len(rows) > 1:
            row2 = rows[1]
            en_body = row2[0] if len(row2) > 0 else '(空)'
            jp_body = row2[1] if len(row2) > 1 else '(空)'
            print(f"  A2（英語本文）: {en_body[:200].replace(chr(10), '\\n')}...")
            print(f"  B2（日本語本文）: {jp_body[:200].replace(chr(10), '\\n')}...")

        # 3行目: プロンプト
        print("\n3行目（OpenAIプロンプト）:")
        if len(rows) > 2:
            row3 = rows[2]
            en_prompt = row3[0] if len(row3) > 0 else ''
            jp_prompt = row3[1] if len(row3) > 1 else ''
            if en_prompt:
                print(f"  A3（英語プロンプト）: {en_prompt[:200].replace(chr(10), '\\n')}...")
            else:
                print(f"  A3（英語プロンプト）: (空) → A2の本文をそのまま使用")
            if jp_prompt:
                print(f"  B3（日本語プロンプト）: {jp_prompt[:200].replace(chr(10), '\\n')}...")
            else:
                print(f"  B3（日本語プロンプト）: (空) → B2の本文をそのまま使用")
        else:
            print("  3行目が存在しません → 本文をそのまま使用")

        # 全列数・行数を表示
        print(f"\n総行数: {len(rows)}行")
        print(f"総列数: {len(rows[0]) if len(rows) > 0 else 0}列")

        print("\n" + "=" * 80)
        print("✅ 完了")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = inspect_template()
    exit(0 if success else 1)
