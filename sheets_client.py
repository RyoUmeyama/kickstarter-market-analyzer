#!/usr/bin/env python3
"""
Google Sheets連携モジュール
スプレッドシートからデータを読み取り、レポートを書き込む
"""

import os
import json
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# スコープ：Sheets APIの読み書き
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsClient:
    """Google Sheetsクライアント"""

    def __init__(self, spreadsheet_id, sheet_name='kickstarter'):
        """
        Args:
            spreadsheet_id (str): スプレッドシートID
            sheet_name (str): シート名
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.service = self._authenticate()

    def _authenticate(self):
        """Google Sheets APIの認証（OAuth or サービスアカウント）"""

        # GitHub Actions等の環境変数からサービスアカウント認証
        if os.getenv('GOOGLE_CREDENTIALS_JSON'):
            print("Using service account authentication (from environment variable)")
            credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            credentials_dict = json.loads(credentials_json)
            creds = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=SCOPES
            )
            return build('sheets', 'v4', credentials=creds)

        # credentials.jsonがある場合はサービスアカウント認証を試みる
        if os.path.exists('credentials.json'):
            try:
                with open('credentials.json', 'r') as f:
                    credentials_dict = json.load(f)

                # サービスアカウントかどうか判定
                if credentials_dict.get('type') == 'service_account':
                    print("Using service account authentication (from credentials.json)")
                    creds = service_account.Credentials.from_service_account_file(
                        'credentials.json',
                        scopes=SCOPES
                    )
                    return build('sheets', 'v4', credentials=creds)
            except (json.JSONDecodeError, KeyError):
                pass

        # OAuth 2.0認証（ローカル実行用）
        print("Using OAuth 2.0 authentication (interactive)")
        creds = None

        # token.jsonに保存された認証情報を読み込み
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        # 有効な認証情報がない場合
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # 期限切れの場合はリフレッシュ
                creds.refresh(Request())
            else:
                # 新規認証
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError(
                        'credentials.json が見つかりません。\n'
                        'Google Cloud Consoleから OAuth 2.0クライアントIDまたは\n'
                        'サービスアカウントを作成し、credentials.jsonとして\n'
                        'ダウンロードしてください。\n'
                        'またはGOOGLE_CREDENTIALS_JSON環境変数を設定してください。'
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            # 認証情報を保存
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return build('sheets', 'v4', credentials=creds)

    def read_rows(self):
        """
        スプレッドシートから全行を読み取り

        Returns:
            list: 行データのリスト
        """
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:J'
            ).execute()

            values = result.get('values', [])
            return values

        except HttpError as err:
            print(f'Error reading spreadsheet: {err}')
            return []

    def write_report(self, row_number, japanese_report, english_report=None):
        """
        レポートをスプレッドシートに書き込み

        Args:
            row_number (int): 行番号（1始まり）
            japanese_report (str): 日本語レポート
            english_report (str, optional): 英語レポート
        """
        try:
            # I列に日本語レポート
            self._update_cell(row_number, 9, japanese_report)
            print(f'✓ Japanese report written to I{row_number}')

            # J列に英語レポート（オプション）
            if english_report:
                self._update_cell(row_number, 10, english_report)
                print(f'✓ English report written to J{row_number}')

            print(f'✓ Report written to row {row_number}')

        except HttpError as err:
            print(f'Error writing to spreadsheet: {err}')

    def _update_cell(self, row, col, value):
        """
        特定のセルを更新

        Args:
            row (int): 行番号（1始まり）
            col (int): 列番号（1始まり、A=1, B=2, ...）
            value (str): 値
        """
        # 列番号を列名に変換（A, B, C, ...）
        col_letter = chr(64 + col)  # A=65
        range_name = f'{self.sheet_name}!{col_letter}{row}'

        body = {
            'values': [[value]]
        }

        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

    def get_unprocessed_rows(self):
        """
        未処理の行を取得（I列が空、または短い文字列のみの行）

        Returns:
            list: (row_number, url, product_name, maker_name, creator_name) のリスト
        """
        rows = self.read_rows()
        unprocessed = []

        for i, row in enumerate(rows):
            # ヘッダー行をスキップ
            if i == 0:
                continue

            row_number = i + 1

            # 最低限の列数チェック
            if len(row) < 2:
                continue

            url = row[1] if len(row) > 1 else ''
            product_name = row[2] if len(row) > 2 else ''
            maker_name = row[3] if len(row) > 3 else ''
            creator_name = row[4] if len(row) > 4 else ''
            japanese_report = row[8] if len(row) > 8 else ''

            # URLがあり、I列（日本語レポート）が空、または100文字未満の場合
            # 既存データ（"done"など）を上書きして処理する
            if url and (not japanese_report or len(japanese_report.strip()) < 100):
                print(f"  Found unprocessed row {row_number}: {url[:50]}... (I-col: '{japanese_report[:20] if japanese_report else 'empty'}')")
                unprocessed.append({
                    'row_number': row_number,
                    'url': url,
                    'product_name': product_name,
                    'maker_name': maker_name,
                    'creator_name': creator_name
                })

        return unprocessed


def test_sheets():
    """Google Sheets APIのテスト"""
    from dotenv import load_dotenv
    load_dotenv()

    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')

    if not spreadsheet_id:
        print('エラー: SPREADSHEET_IDが設定されていません')
        return

    print("=" * 60)
    print("Google Sheets API Test")
    print("=" * 60)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Sheet Name: {sheet_name}\n")

    client = GoogleSheetsClient(spreadsheet_id, sheet_name)

    # 全行を読み取り
    print("Reading all rows...")
    rows = client.read_rows()
    print(f"✓ Found {len(rows)} rows\n")

    # 未処理行を取得
    print("Finding unprocessed rows...")
    unprocessed = client.get_unprocessed_rows()
    print(f"✓ Found {len(unprocessed)} unprocessed rows\n")

    for item in unprocessed:
        print(f"Row {item['row_number']}: {item['url']}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    test_sheets()
