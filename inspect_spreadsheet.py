#!/usr/bin/env python3
"""
Google Spreadsheetsの全シートを確認するスクリプト
"""

import os
import json
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def authenticate():
    """Google Sheets APIの認証"""
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
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError('credentials.json not found')

            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # 認証情報を保存
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('sheets', 'v4', credentials=creds)


def get_all_sheet_names(service, spreadsheet_id):
    """
    スプレッドシートの全シート名を取得

    Args:
        service: Google Sheets APIサービス
        spreadsheet_id (str): スプレッドシートID

    Returns:
        list: シート名のリスト
    """
    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        sheets = spreadsheet.get('sheets', [])
        sheet_names = []

        for sheet in sheets:
            properties = sheet.get('properties', {})
            sheet_name = properties.get('title', 'Unknown')
            sheet_id = properties.get('sheetId', 'Unknown')
            row_count = properties.get('gridProperties', {}).get('rowCount', 0)
            col_count = properties.get('gridProperties', {}).get('columnCount', 0)

            sheet_names.append({
                'name': sheet_name,
                'id': sheet_id,
                'rows': row_count,
                'cols': col_count
            })

        return sheet_names

    except HttpError as err:
        print(f'Error getting sheet names: {err}')
        return []


def read_sheet_data(service, spreadsheet_id, sheet_name, max_rows=10):
    """
    特定のシートのデータを読み取る

    Args:
        service: Google Sheets APIサービス
        spreadsheet_id (str): スプレッドシートID
        sheet_name (str): シート名
        max_rows (int): 表示する最大行数

    Returns:
        list: 行データのリスト
    """
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A1:ZZ{max_rows}'
        ).execute()

        values = result.get('values', [])
        return values

    except HttpError as err:
        print(f'Error reading sheet {sheet_name}: {err}')
        return []


def inspect_spreadsheet(spreadsheet_id):
    """
    スプレッドシートの全シートを検査

    Args:
        spreadsheet_id (str): スプレッドシートID
    """
    print("=" * 80)
    print("Google Spreadsheet Inspector")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}\n")

    # 認証
    service = authenticate()

    # 全シート名を取得
    print("Fetching sheet names...")
    sheets = get_all_sheet_names(service, spreadsheet_id)

    if not sheets:
        print("No sheets found or error occurred.")
        return

    print(f"✓ Found {len(sheets)} sheet(s)\n")

    # 各シートの情報を表示
    for i, sheet_info in enumerate(sheets, 1):
        print("=" * 80)
        print(f"Sheet {i}: {sheet_info['name']}")
        print("=" * 80)
        print(f"Sheet ID: {sheet_info['id']}")
        print(f"Dimensions: {sheet_info['rows']} rows × {sheet_info['cols']} columns\n")

        # データを読み取る（最初の10行）
        print(f"Reading first 10 rows of '{sheet_info['name']}'...")
        data = read_sheet_data(service, spreadsheet_id, sheet_info['name'], max_rows=10)

        if not data:
            print("  (No data or empty sheet)\n")
            continue

        # ヘッダー行を表示
        if len(data) > 0:
            print(f"\nHeader row (Row 1):")
            headers = data[0]
            for j, header in enumerate(headers, 1):
                print(f"  Column {chr(64+j)}: {header}")

        # データ行数を表示
        print(f"\nTotal rows retrieved: {len(data)}")

        # 最初の数行のデータをサンプル表示（ヘッダー除く）
        if len(data) > 1:
            print(f"\nSample data (Rows 2-{min(len(data), 4)}):")
            for row_idx, row in enumerate(data[1:min(len(data), 4)], 2):
                print(f"\n  Row {row_idx}:")
                for col_idx, cell in enumerate(row, 1):
                    # 長すぎるセルは省略
                    cell_preview = str(cell)[:50] + '...' if len(str(cell)) > 50 else str(cell)
                    print(f"    {chr(64+col_idx)}: {cell_preview}")

        print()

    print("=" * 80)
    print("Inspection complete!")
    print("=" * 80)


if __name__ == '__main__':
    import sys

    # コマンドライン引数からスプレッドシートIDを取得
    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1]
    else:
        # デフォルトのスプレッドシートID（ユーザーが指定したもの）
        spreadsheet_id = '1vAVnv3oYUm_J2eIvDNrJi6fUcnpLYSb8Q2Y_aq6NDqM'

    inspect_spreadsheet(spreadsheet_id)
