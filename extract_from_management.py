#!/usr/bin/env python3
"""
管理表からkickstarterシートへのデータ抽出スクリプト

使い方:
    # ステータス一覧を表示
    python extract_from_management.py --list

    # 特定ステータスの行を抽出してkickstarterシートにコピー
    python extract_from_management.py --status "②無返信2回目　要送信"

    # 複数ステータスを抽出
    python extract_from_management.py --status "②無返信2回目　要送信" --status "➂無返信3回目　要送信"

    # 抽出後にメール生成も実行
    python extract_from_management.py --status "②無返信2回目　要送信" --generate
"""

import os
import argparse
from dotenv import load_dotenv
from sheets_client import ManagementSheetClient

# .envファイルを読み込み
load_dotenv()


def list_statuses(client):
    """利用可能なステータスと件数を表示"""
    print("\n" + "=" * 60)
    print("管理表のステータス一覧")
    print("=" * 60)

    statuses = client.get_available_statuses()
    status_template_map = client.get_status_template_mapping()

    # テンプレート対応があるステータスを先に表示
    print("\n【送信対象ステータス（テンプレート対応あり）】")
    for status, template in status_template_map.items():
        if status in statuses or status == '':
            display_status = status if status else '(空白)'
            count = statuses.get(status, statuses.get('(空白)', 0))
            if count > 0:
                print(f"  {display_status}: {count}件 → {template}")

    # その他のステータス
    print("\n【その他のステータス】")
    for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
        if status not in status_template_map and status != '(空白)':
            print(f"  {status}: {count}件")

    print()


def extract_rows(client, target_statuses, generate_emails=False):
    """指定ステータスの行を抽出"""
    all_rows = []

    for status in target_statuses:
        # 「（空白＝新規）」は空文字列として扱う
        if status == '（空白＝新規）':
            status = ''
        print(f"\n処理中: ステータス「{status if status else '(空白)'}」")
        rows = client.get_rows_by_status(status)
        print(f"  → {len(rows)}件のKickstarter URLを発見")
        all_rows.extend(rows)

    if not all_rows:
        print("\n抽出対象の行がありません。")
        return

    # kickstarterシートにコピー
    print(f"\n合計 {len(all_rows)}件をkickstarterシートにコピーします...")
    copied = client.copy_to_kickstarter_sheet(all_rows)

    if copied > 0:
        print(f"\n✅ {copied}件の抽出が完了しました！")
        print("\n次のステップ:")
        print("  1. GitHub Actionsで「Run workflow」を実行してメール生成")
        print("  2. スプレッドシートをCSVでダウンロード")
        print("  3. Thunderbirdのメールマージで送信")

        if generate_emails:
            print("\n--generate オプションが指定されたため、メール生成を実行します...")
            from main import main as generate_main
            generate_main()


def main():
    parser = argparse.ArgumentParser(
        description='管理表からkickstarterシートへデータを抽出',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ステータス一覧を表示
  python extract_from_management.py --list

  # ②無返信2回目の行を抽出
  python extract_from_management.py --status "②無返信2回目　要送信"

  # 複数ステータスを抽出
  python extract_from_management.py --status "②無返信2回目　要送信" --status "➂無返信3回目　要送信"

  # 抽出後にメール生成も実行
  python extract_from_management.py --status "②無返信2回目　要送信" --generate
        """
    )
    parser.add_argument('--list', action='store_true', help='利用可能なステータス一覧を表示')
    parser.add_argument('--status', action='append', help='抽出対象のステータス（複数指定可）')
    parser.add_argument('--generate', action='store_true', help='抽出後にメール生成も実行')

    args = parser.parse_args()

    # 環境変数を取得
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return

    # クライアント初期化
    print("Google Sheets認証中...")
    client = ManagementSheetClient(spreadsheet_id)
    print("✓ 認証成功！")

    if args.list:
        list_statuses(client)
    elif args.status:
        extract_rows(client, args.status, args.generate)
    else:
        # 引数なしの場合はステータス一覧を表示
        list_statuses(client)
        print("使い方: python extract_from_management.py --status \"ステータス名\"")
        print("詳細は: python extract_from_management.py --help")


if __name__ == '__main__':
    main()
