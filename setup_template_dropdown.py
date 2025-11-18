#!/usr/bin/env python3
"""
kickstarterシートのtemplate列（C列）にドロップダウンリスト（データ検証）を設定
"""

import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# .envファイルを読み込み
load_dotenv()

# Google Sheets API のスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def authenticate():
    """Google Sheets APIの認証を行う"""
    creds = None

    # token.pickleファイルがあれば読み込む
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # 認証情報がない、または無効な場合は再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # 認証情報を保存
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds)

def setup_template_dropdown():
    """
    kickstarterシートのC列（template）にドロップダウンリストを設定
    """
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return False

    print("=" * 80)
    print("テンプレート列のドロップダウンリスト設定")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheet Name: {sheet_name}\n")

    try:
        # 認証
        print("認証中...")
        service = authenticate()
        print("✓ 認証成功！\n")

        # シートIDを取得
        print(f"シート '{sheet_name}' のIDを取得中...")
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        sheet_id = None
        for sheet in spreadsheet.get('sheets', []):
            properties = sheet.get('properties', {})
            if properties.get('title') == sheet_name:
                sheet_id = properties.get('sheetId')
                break

        if sheet_id is None:
            print(f"❌ エラー: シート '{sheet_name}' が見つかりませんでした")
            print("\n次の手順:")
            print("1. スプレッドシートに 'kickstarter' という名前のシートを作成")
            print("2. 1行目にヘッダー行を追加")
            print("3. 再度このスクリプトを実行")
            return False

        print(f"✓ シートID: {sheet_id}\n")

        # テンプレート名のリスト（既存の5つのテンプレートシート名）
        template_names = [
            "①1回目送信文",
            "②無返信用2回目送信",
            "➂無返信3回目",
            "④自動返信用　2回目送信",
            "⑤好返信用　詳細レポート送信"
        ]

        print("ドロップダウンリストの設定:")
        for i, name in enumerate(template_names, 1):
            print(f"  {i}. {name}")
        print()

        # データ検証ルールを設定
        # C列（列番号2、0始まりなので2）の2行目以降（ヘッダー除く）に適用
        print("データ検証ルールを作成中...")

        request_body = {
            'requests': [
                {
                    'setDataValidation': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 1,  # 2行目から（0始まりなので1）
                            'endRowIndex': 1000,  # 1000行目まで
                            'startColumnIndex': 2,  # C列（0始まりなので2）
                            'endColumnIndex': 3  # C列のみ（終了は+1）
                        },
                        'rule': {
                            'condition': {
                                'type': 'ONE_OF_LIST',
                                'values': [
                                    {'userEnteredValue': name}
                                    for name in template_names
                                ]
                            },
                            'showCustomUi': True,  # ドロップダウンリストを表示
                            'strict': True  # リスト外の入力を拒否
                        }
                    }
                }
            ]
        }

        # APIリクエストを実行
        print("APIリクエストを送信中...")
        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()

        print("✓ データ検証ルールの設定が完了しました！\n")

        print("=" * 80)
        print("✅ 完了！")
        print("=" * 80)
        print(f"\nkickstarterシートのC列（template）に以下のドロップダウンリストが設定されました:")
        for i, name in enumerate(template_names, 1):
            print(f"  {i}. {name}")

        print("\n次の手順:")
        print("1. スプレッドシートを開いてC列のセルをクリック")
        print("2. ドロップダウンリストが表示されることを確認")
        print("3. テンプレートを選択してデータを入力")

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
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = setup_template_dropdown()
    exit(0 if success else 1)
