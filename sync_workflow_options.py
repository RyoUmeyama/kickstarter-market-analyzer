#!/usr/bin/env python3
"""
設定シートからワークフローの選択肢を同期するスクリプト

使い方:
    python sync_workflow_options.py

機能:
    1. 設定シートのC列（ステータス）を読み取り
    2. .github/workflows/extract_and_generate.yml の options を更新
"""

import os
import re
from dotenv import load_dotenv
from sheets_client import ManagementSheetClient

# .envファイルを読み込み
load_dotenv()

WORKFLOW_FILE = '.github/workflows/extract_and_generate.yml'


def get_statuses_from_sheet():
    """設定シートからステータス一覧を取得"""
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_IDが設定されていません")

    print("Google Sheets認証中...")
    client = ManagementSheetClient(spreadsheet_id)
    print("✓ 認証成功！")

    # ステータス→テンプレート対応表を取得
    status_template_map = client.get_status_template_mapping()

    # ステータス一覧を取得（空白は「（空白＝新規）」として表示）
    statuses = []
    for status in status_template_map.keys():
        if status == '':
            statuses.append('（空白＝新規）')
        else:
            statuses.append(status)

    return statuses


def update_workflow_file(statuses):
    """ワークフローファイルの選択肢を更新"""
    if not os.path.exists(WORKFLOW_FILE):
        raise FileNotFoundError(f"{WORKFLOW_FILE} が見つかりません")

    with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # options: セクションを見つけて置換
    # パターン: options: の後に続くインデント付きの - で始まる行群
    pattern = r"(options:\n)((?:\s+- '[^']*'\n)+)"

    # 新しいoptionsを構築
    new_options = "options:\n"
    for status in statuses:
        new_options += f"          - '{status}'\n"

    # 置換
    new_content = re.sub(pattern, new_options, content)

    if new_content == content:
        print("⚠️  変更なし（パターンが見つからないか、既に同じ内容です）")
        return False

    with open(WORKFLOW_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    print("=" * 60)
    print("ワークフロー選択肢の同期")
    print("=" * 60)

    try:
        # 設定シートからステータスを取得
        print("\n設定シートからステータスを取得中...")
        statuses = get_statuses_from_sheet()

        print(f"\n取得したステータス ({len(statuses)}件):")
        for s in statuses:
            print(f"  - {s}")

        # ワークフローファイルを更新
        print(f"\n{WORKFLOW_FILE} を更新中...")
        updated = update_workflow_file(statuses)

        if updated:
            print("✅ ワークフローファイルを更新しました！")
            print("\n次のステップ:")
            print("  このスクリプトがGitHub Actionsで実行された場合、")
            print("  変更は自動的にコミット・プッシュされます。")
        else:
            print("ℹ️  更新は不要でした。")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
