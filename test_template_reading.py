#!/usr/bin/env python3
"""
テンプレート読み込み機能のテスト
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

def test_template_reading():
    """
    テンプレート読み込み機能をテスト
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("テンプレート読み込み機能のテスト")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}\n")

    try:
        # Google Sheetsクライアントを初期化
        print("認証中...")
        client = GoogleSheetsClient(spreadsheet_id, 'kickstarter')
        print("✓ 認証成功！\n")

        # テンプレート名のリスト
        template_names = [
            "①1回目送信文",
            "②無返信用2回目送信",
            "➂無返信3回目",
            "④自動返信用　2回目送信",
            "⑤好返信用　詳細レポート送信"
        ]

        # 各テンプレートを読み込んでテスト
        for template_name in template_names:
            print(f"\n📋 テンプレート: {template_name}")
            print("-" * 80)

            template = client.read_template(template_name)

            if template:
                print(f"✓ 読み込み成功")
                print(f"\n英語件名:")
                print(f"  {template['en_subject']}")
                print(f"\n英語本文（最初の200文字）:")
                en_body_preview = template['en_body'][:200].replace('\n', '\\n')
                print(f"  {en_body_preview}...")
                print(f"\n日本語本文（最初の200文字）:")
                jp_body_preview = template['jp_body'][:200].replace('\n', '\\n')
                print(f"  {jp_body_preview}...")
            else:
                print(f"❌ 読み込み失敗")

        print("\n" + "=" * 80)
        print("✅ テスト完了")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_template_reading()
    exit(0 if success else 1)
