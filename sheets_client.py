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

    def read_rows(self, sheet_name=None, column_range='A:L'):
        """
        スプレッドシートから全行を読み取り

        Args:
            sheet_name (str, optional): シート名（指定しない場合はself.sheet_nameを使用）
            column_range (str, optional): 列範囲（デフォルト: A:L）

        Returns:
            list: 行データのリスト
        """
        if sheet_name is None:
            sheet_name = self.sheet_name

        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!{column_range}'
            ).execute()

            values = result.get('values', [])
            return values

        except HttpError as err:
            print(f'Error reading spreadsheet: {err}')
            return []

    def write_report(self, row_number, jp_subject, en_subject, japanese_body, english_body, status='完了'):
        """
        レポート（件名+本文）をスプレッドシートに書き込み

        新列構成: A=NO, B=product_url, C=template, D=name, E=to_email,
                 F=jp_subject, G=en_subject, H=status, I=jp_body, J=en_body

        仕様:
        - japanese_bodyが空文字列の場合、I列にGOOGLETRANSLATE関数を設定
        - japanese_bodyに値がある場合、I列にそのまま値を書き込み

        Args:
            row_number (int): 行番号（1始まり）
            jp_subject (str): 日本語件名
            en_subject (str): 英語件名
            japanese_body (str): 日本語本文（空文字列の場合は関数を設定）
            english_body (str): 英語本文
            status (str, optional): ステータス（デフォルト: '完了'）
        """
        try:
            # F列に日本語件名
            self._update_cell(row_number, 6, jp_subject)
            print(f'✓ Japanese subject written to F{row_number}')

            # G列に英語件名
            self._update_cell(row_number, 7, en_subject)
            print(f'✓ English subject written to G{row_number}')

            # H列にステータス
            self._update_cell(row_number, 8, status)
            print(f'✓ Status written to H{row_number}: {status}')

            # J列に英語本文（先に書き込む）
            self._update_cell(row_number, 10, english_body)
            print(f'✓ English body written to J{row_number}')

            # I列に日本語本文（値 or GOOGLETRANSLATE関数）
            if japanese_body and japanese_body.strip():
                # 値がある場合はそのまま書き込み
                self._update_cell(row_number, 9, japanese_body)
                print(f'✓ Japanese body written to I{row_number}')
            else:
                # 空の場合はGOOGLETRANSLATE関数を設定
                formula = f'=IF(J{row_number}="", "", GOOGLETRANSLATE(J{row_number}, "en", "ja"))'
                self._update_cell_formula(row_number, 9, formula)
                print(f'✓ GOOGLETRANSLATE formula written to I{row_number}')

            print(f'✓ Report written to row {row_number}')

        except HttpError as err:
            print(f'Error writing to spreadsheet: {err}')

    def _update_cell(self, row, col, value):
        """
        特定のセルに値を更新

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

    def _update_cell_formula(self, row, col, formula):
        """
        特定のセルに数式を設定

        Args:
            row (int): 行番号（1始まり）
            col (int): 列番号（1始まり、A=1, B=2, ...）
            formula (str): 数式（例: "=SUM(A1:A10)"）
        """
        # 列番号を列名に変換（A, B, C, ...）
        col_letter = chr(64 + col)  # A=65
        range_name = f'{self.sheet_name}!{col_letter}{row}'

        body = {
            'values': [[formula]]
        }

        # USER_ENTEREDを使用すると数式として解釈される
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

    def get_all_sheet_names(self):
        """
        スプレッドシート内の全シート名を取得

        Returns:
            list: シート名のリスト
        """
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            sheets = spreadsheet.get('sheets', [])
            sheet_names = []

            for sheet in sheets:
                properties = sheet.get('properties', {})
                sheet_name = properties.get('title', '')
                sheet_names.append(sheet_name)

            return sheet_names

        except HttpError as err:
            print(f'Error getting sheet names: {err}')
            return []

    def read_template(self, template_name):
        """
        テンプレートシートから設定を読み取る

        Args:
            template_name (str): テンプレート名（シート名）

        Returns:
            dict: テンプレート設定
                {
                    'name': テンプレート名,
                    'en_subject': 英語メール件名（A1セル）,
                    'jp_subject': 日本語メール件名（B1セル）,
                    'en_body': 英語メール本文（A2セル）,
                    'jp_body': 日本語メール本文（B2セル）,
                    'en_prompt': 英語用OpenAIプロンプト（A3セル、任意）,
                    'jp_prompt': 日本語用OpenAIプロンプト（B3セル、任意）
                }
        """
        try:
            # テンプレートシートから最初の3行を読み取り
            # A:B列を取得
            rows = self.read_rows(sheet_name=template_name, column_range='A:B')

            if len(rows) < 2:
                print(f'Warning: Template sheet "{template_name}" has insufficient rows')
                return None

            # 1行目: 件名
            row1 = rows[0]
            en_subject = row1[0] if len(row1) > 0 else ''
            jp_subject = row1[1] if len(row1) > 1 else ''

            # 2行目: 本文
            row2 = rows[1]
            en_body = row2[0] if len(row2) > 0 else ''
            jp_body = row2[1] if len(row2) > 1 else ''

            # 3行目: OpenAIプロンプト（任意）
            en_prompt = ''
            jp_prompt = ''
            if len(rows) > 2:
                row3 = rows[2]
                en_prompt = row3[0] if len(row3) > 0 else ''
                jp_prompt = row3[1] if len(row3) > 1 else ''

            template = {
                'name': template_name,
                'en_subject': en_subject,
                'jp_subject': jp_subject,
                'en_body': en_body,
                'jp_body': jp_body,
                'en_prompt': en_prompt,
                'jp_prompt': jp_prompt
            }

            return template

        except HttpError as err:
            print(f'Error reading template "{template_name}": {err}')
            return None

    def get_unprocessed_rows(self):
        """
        未処理の行を取得（I列（jp_body）が空、または短い文字列のみの行）

        新列構成: A=NO, B=product_url, C=template, D=name, E=to_email,
                 F=jp_subject, G=en_subject, H=status, I=jp_body, J=en_body

        Returns:
            list: 未処理行の情報リスト
                [
                    {
                        'row_number': 行番号,
                        'url': Kickstarter URL,
                        'template': テンプレート名,
                        'name': 担当者名,
                        'to_email': 送信先メールアドレス
                    },
                    ...
                ]
        """
        rows = self.read_rows(sheet_name=self.sheet_name, column_range='A:J')
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
            template = row[2] if len(row) > 2 else ''
            name = row[3] if len(row) > 3 else ''
            to_email = row[4] if len(row) > 4 else ''
            jp_body = row[8] if len(row) > 8 else ''  # I列

            # URLがあり、I列（日本語本文）が空、または100文字未満の場合
            # 既存データ（"done"など）を上書きして処理する
            if url and (not jp_body or len(jp_body.strip()) < 100):
                print(f"  Found unprocessed row {row_number}: {url[:50]}... (I-col: '{jp_body[:20] if jp_body else 'empty'}')")
                unprocessed.append({
                    'row_number': row_number,
                    'url': url,
                    'template': template,
                    'name': name,
                    'to_email': to_email
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
