#!/usr/bin/env python3
"""
更新後のテンプレート読み込みテスト
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

def test_updated_template():
    """
    更新後のテンプレート読み込みをテスト
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("更新後のテンプレート読み込みテスト")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}\n")

    try:
        # Google Sheetsクライアントを初期化
        print("認証中...")
        client = GoogleSheetsClient(spreadsheet_id, 'kickstarter')
        print("✓ 認証成功！\n")

        # テンプレート名（1つ目のみテスト）
        template_name = "①1回目送信文"

        print(f"📋 テンプレート: {template_name}")
        print("-" * 80)

        template = client.read_template(template_name)

        if template:
            print(f"✓ 読み込み成功\n")

            print(f"【件名】")
            print(f"  A1（英語件名）: {template['en_subject']}")
            print(f"  B1（日本語件名）: {template['jp_subject']}")

            print(f"\n【本文】")
            print(f"  A2（英語本文、最初の200文字）:")
            print(f"    {template['en_body'][:200]}...")
            print(f"  B2（日本語本文、最初の200文字）:")
            print(f"    {template['jp_body'][:200]}...")

            print(f"\n【プロンプト】")
            if template.get('en_prompt'):
                print(f"  A3（プロンプト、最初の200文字）:")
                print(f"    {template['en_prompt'][:200]}...")
                print(f"\n  → OpenAI APIを使用します")
            else:
                print(f"  A3（プロンプト）: (空)")
                print(f"  → テンプレート本文をそのまま使用します")

            if template.get('jp_prompt'):
                print(f"  B3: {template['jp_prompt'][:100]}...")
            else:
                print(f"  B3: (空)")
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
    success = test_updated_template()
    exit(0 if success else 1)
