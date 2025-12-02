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

    def write_report(self, row_number, jp_subject, en_subject, japanese_body, english_body):
        """
        レポート（件名+本文）をスプレッドシートに書き込み

        新列構成: A=NO, B=product_url, C=template, D=name, E=to_email,
                 F=jp_subject, G=en_subject, H=jp_body, I=en_body,
                 J=jp_body_html, K=en_body_html

        仕様:
        - japanese_bodyが空文字列の場合、H列にGOOGLETRANSLATE関数を設定
        - japanese_bodyに値がある場合、H列にそのまま値を書き込み
        - J列とK列にはHTML形式（改行を<br>に変換）を書き込み

        Args:
            row_number (int): 行番号（1始まり）
            jp_subject (str): 日本語件名
            en_subject (str): 英語件名
            japanese_body (str): 日本語本文（空文字列の場合は関数を設定）
            english_body (str): 英語本文
        """
        try:
            # F列に日本語件名
            self._update_cell(row_number, 6, jp_subject)
            print(f'✓ Japanese subject written to F{row_number}')

            # G列に英語件名
            self._update_cell(row_number, 7, en_subject)
            print(f'✓ English subject written to G{row_number}')

            # I列に英語本文（先に書き込む）
            self._update_cell(row_number, 9, english_body)
            print(f'✓ English body written to I{row_number}')

            # H列に日本語本文（値 or GOOGLETRANSLATE関数）
            if japanese_body and japanese_body.strip():
                # 値がある場合はそのまま書き込み
                self._update_cell(row_number, 8, japanese_body)
                print(f'✓ Japanese body written to H{row_number}')
            else:
                # 空の場合はGOOGLETRANSLATE関数を設定（名前は英語のまま保持）
                # SUBSTITUTE で翻訳された名前を英語の名前に置き換え（様は追加しない - 翻訳時に付与済み）
                formula = f'=IF(I{row_number}="", "", SUBSTITUTE(GOOGLETRANSLATE(I{row_number}, "en", "ja"), GOOGLETRANSLATE(D{row_number}, "en", "ja"), D{row_number}))'
                self._update_cell_formula(row_number, 8, formula)
                print(f'✓ GOOGLETRANSLATE + SUBSTITUTE formula written to H{row_number}')

            # K列に英語本文HTML版（改行を<br>に変換）
            en_body_html = self._convert_to_html(english_body)
            self._update_cell(row_number, 11, en_body_html)
            print(f'✓ English body (HTML) written to K{row_number}')

            # J列に日本語本文HTML版（値 or GOOGLETRANSLATE関数）
            if japanese_body and japanese_body.strip():
                jp_body_html = self._convert_to_html(japanese_body)
                self._update_cell(row_number, 10, jp_body_html)
                print(f'✓ Japanese body (HTML) written to J{row_number}')
            else:
                # 空の場合はGOOGLETRANSLATE関数を設定（名前は英語のまま保持、改行を<br>に変換）
                formula = f'=IF(I{row_number}="", "", SUBSTITUTE(SUBSTITUTE(GOOGLETRANSLATE(I{row_number}, "en", "ja"), GOOGLETRANSLATE(D{row_number}, "en", "ja"), D{row_number}), CHAR(10), "<br>"))'
                self._update_cell_formula(row_number, 10, formula)
                print(f'✓ GOOGLETRANSLATE + SUBSTITUTE + HTML formula written to J{row_number}')

            print(f'✓ Report written to row {row_number}')

        except HttpError as err:
            print(f'Error writing to spreadsheet: {err}')

    def _convert_to_html(self, text):
        """
        プレーンテキストをHTML形式に変換
        - 改行を<br>に変換
        - 特殊文字をエスケープ（&, <, >）

        Args:
            text (str): プレーンテキスト

        Returns:
            str: HTML形式のテキスト
        """
        if not text:
            return ''

        # 特殊文字をエスケープ
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        # 改行を<br>に変換
        text = text.replace('\n', '<br>')

        return text

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

    def get_common_prompt(self):
        """
        設定シートから共通プロンプトを読み取る

        Returns:
            str: 共通プロンプト（A2セルの内容）
                 設定シートが存在しない場合やエラー時は空文字列を返す
        """
        try:
            rows = self.read_rows(sheet_name='設定', column_range='A2:A2')

            if rows and len(rows) > 0 and len(rows[0]) > 0:
                common_prompt = rows[0][0]
                print(f'✓ 共通プロンプトを読み込みました（{len(common_prompt)}文字）')
                return common_prompt
            else:
                print('⚠️  設定シートに共通プロンプトが設定されていません')
                return ''

        except HttpError as err:
            print(f'⚠️  設定シートの読み込みエラー: {err}')
            print('   共通プロンプトなしで処理を続行します')
            return ''

    def get_system_settings(self):
        """
        設定シートからシステム設定を読み取る（変更不可の技術的ルール）

        Returns:
            str: システム設定（G2セルの内容）
                 設定シートが存在しない場合やエラー時は空文字列を返す
        """
        try:
            rows = self.read_rows(sheet_name='設定', column_range='G2:G2')

            if rows and len(rows) > 0 and len(rows[0]) > 0:
                system_settings = rows[0][0]
                print(f'✓ システム設定を読み込みました（{len(system_settings)}文字）')
                return system_settings
            else:
                print('⚠️  設定シートにシステム設定が設定されていません')
                return ''

        except HttpError as err:
            print(f'⚠️  システム設定の読み込みエラー: {err}')
            return ''

    def get_translation_rules(self):
        """
        設定シートから翻訳ルールを読み取る

        Returns:
            str: 翻訳ルール（H2セルの内容）
                 設定シートが存在しない場合やエラー時は空文字列を返す
        """
        try:
            rows = self.read_rows(sheet_name='設定', column_range='H2:H2')

            if rows and len(rows) > 0 and len(rows[0]) > 0:
                translation_rules = rows[0][0]
                print(f'✓ 翻訳ルールを読み込みました（{len(translation_rules)}文字）')
                return translation_rules
            else:
                print('⚠️  設定シートに翻訳ルールが設定されていません')
                return ''

        except HttpError as err:
            print(f'⚠️  翻訳ルールの読み込みエラー: {err}')
            return ''

    def get_output_format_rules(self):
        """
        設定シートから出力形式ルールを読み取る

        Returns:
            str: 出力形式ルール（I2セルの内容）
                 設定シートが存在しない場合やエラー時は空文字列を返す
        """
        try:
            rows = self.read_rows(sheet_name='設定', column_range='I2:I2')

            if rows and len(rows) > 0 and len(rows[0]) > 0:
                output_format_rules = rows[0][0]
                print(f'✓ 出力形式ルールを読み込みました（{len(output_format_rules)}文字）')
                return output_format_rules
            else:
                print('⚠️  設定シートに出力形式ルールが設定されていません')
                return ''

        except HttpError as err:
            print(f'⚠️  出力形式ルールの読み込みエラー: {err}')
            return ''

    def get_unprocessed_rows(self):
        """
        未処理の行を取得（H列（jp_body）が空、または短い文字列のみの行）

        新列構成: A=NO, B=product_url, C=template, D=name, E=to_email,
                 F=jp_subject, G=en_subject, H=jp_body, I=en_body

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
        rows = self.read_rows(sheet_name=self.sheet_name, column_range='A:I')
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
            jp_body = row[7] if len(row) > 7 else ''  # H列

            # URLがあり、H列（日本語本文）が空、または100文字未満の場合
            # 既存データ（"done"など）を上書きして処理する
            if url and (not jp_body or len(jp_body.strip()) < 100):
                print(f"  Found unprocessed row {row_number}: {url[:50]}... (H-col: '{jp_body[:20] if jp_body else 'empty'}')")
                unprocessed.append({
                    'row_number': row_number,
                    'url': url,
                    'template': template,
                    'name': name,
                    'to_email': to_email
                })

        return unprocessed


# デフォルトのステータス→テンプレート対応表（設定シートに定義がない場合のフォールバック）
DEFAULT_STATUS_TEMPLATE_MAP = {
    '': '①1回目送信文',
    '新規': '①1回目送信文',
    '①1回目送信文 要送信': '①1回目送信文',
    '②無返信2回目　要送信': '②無返信用2回目送信',
    '②無返信2回目 要送信': '②無返信用2回目送信',
    '➂無返信3回目　要送信': '➂無返信3回目',
    '③無返信3回目　要送信': '➂無返信3回目',
    '③無返信3回目 要送信': '➂無返信3回目',
    '④自動返信　要送信': '④自動返信用　2回目送信',
    '④自動返信 要送信': '④自動返信用　2回目送信',
    '⑤好返信　要送信': '⑤好返信用　詳細レポート送信',
    '⑤好返信 要送信': '⑤好返信用　詳細レポート送信',
}

# 後方互換性のためのエイリアス
STATUS_TEMPLATE_MAP = DEFAULT_STATUS_TEMPLATE_MAP


class ManagementSheetClient(GoogleSheetsClient):
    """管理表専用クライアント"""

    # 管理表の列定義（行11がヘッダー、行12からデータ）
    COL_NO = 0          # A列: 番号
    COL_STATUS = 5      # F列: 状況
    COL_NAME = 24       # Y列: name
    COL_EMAIL = 25      # Z列: email
    COL_URL = 26        # AA列: URL
    HEADER_ROW = 11
    DATA_START_ROW = 12

    def __init__(self, spreadsheet_id):
        super().__init__(spreadsheet_id, 'kickstarter')
        self.management_sheet = 'AMANE'
        self._status_template_map = None  # キャッシュ用

    def get_status_template_mapping(self):
        """
        設定シートからステータス→テンプレート対応表を読み込む

        設定シートの構造:
        - C1: "ステータス→テンプレート対応表"（ヘッダー）
        - C2: "ステータス", D2: "テンプレート"（列ヘッダー）
        - C3:D以降: 実際のマッピングデータ

        Returns:
            dict: ステータスをキー、テンプレート名を値とする辞書
        """
        # キャッシュがあれば返す
        if self._status_template_map is not None:
            return self._status_template_map

        try:
            # 設定シートのC3:D列を読み込み（C3から開始、最大50行）
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'設定'!C3:D50"
            ).execute()

            values = result.get('values', [])
            mapping = {}

            for row in values:
                if len(row) >= 2:
                    status = row[0].strip() if row[0] else ''
                    template = row[1].strip() if row[1] else ''
                    if template:  # テンプレートが設定されている場合のみ追加
                        mapping[status] = template

            if mapping:
                print(f"✓ 設定シートからステータス→テンプレート対応表を読み込みました（{len(mapping)}件）")
                self._status_template_map = mapping
                return mapping
            else:
                print("⚠️  設定シートに対応表がありません。デフォルト設定を使用します")
                self._status_template_map = DEFAULT_STATUS_TEMPLATE_MAP
                return DEFAULT_STATUS_TEMPLATE_MAP

        except HttpError as err:
            print(f"⚠️  設定シートの読み込みエラー: {err}")
            print("   デフォルト設定を使用します")
            self._status_template_map = DEFAULT_STATUS_TEMPLATE_MAP
            return DEFAULT_STATUS_TEMPLATE_MAP

    def get_template_for_status(self, status):
        """
        ステータスに対応するテンプレート名を取得

        Args:
            status (str): ステータス値

        Returns:
            str: テンプレート名（対応がない場合は①1回目送信文）
        """
        mapping = self.get_status_template_mapping()
        status_clean = status.strip() if status else ''
        return mapping.get(status_clean, mapping.get('', '①1回目送信文'))

    def get_rows_by_status(self, target_status):
        """
        管理表から指定ステータスの行を取得

        Args:
            target_status (str): 対象ステータス（F列の値）
                               空文字列の場合は空白の行を取得

        Returns:
            list: 該当行のデータリスト
                [
                    {
                        'row_number': 管理表での行番号,
                        'no': 番号（A列）,
                        'status': ステータス（F列）,
                        'name': メーカー名（Y列）,
                        'email': メールアドレス（Z列）,
                        'url': Kickstarter URL（AA列、ハイパーリンク対応）
                    },
                    ...
                ]
        """
        try:
            # 管理表の全データを取得（A列からAA列まで）
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.management_sheet}'!A{self.DATA_START_ROW}:AA1000"
            ).execute()

            values = result.get('values', [])

            # ハイパーリンク情報を取得（AA列）
            hyperlinks = self._get_hyperlinks_from_column(
                self.management_sheet,
                'AA',
                self.DATA_START_ROW,
                self.DATA_START_ROW + len(values) - 1
            )

            matched_rows = []

            for i, row in enumerate(values):
                row_number = self.DATA_START_ROW + i

                # 各列のデータを取得（列が存在しない場合は空文字）
                no = row[self.COL_NO] if len(row) > self.COL_NO else ''
                status = row[self.COL_STATUS] if len(row) > self.COL_STATUS else ''
                name = row[self.COL_NAME] if len(row) > self.COL_NAME else ''
                email = row[self.COL_EMAIL] if len(row) > self.COL_EMAIL else ''
                cell_value = row[self.COL_URL] if len(row) > self.COL_URL else ''

                # URLを取得：ハイパーリンクがあればそれを使用、なければセルの値を使用
                url = hyperlinks.get(row_number, '') or cell_value

                # ステータスが一致する行を抽出
                status_clean = status.strip()
                target_clean = target_status.strip()

                if status_clean == target_clean:
                    # URLがKickstarter URLかどうか確認
                    if url and 'kickstarter.com' in url.lower():
                        matched_rows.append({
                            'row_number': row_number,
                            'no': no,
                            'status': status,
                            'name': name.strip() if name else '',
                            'email': email.strip() if email else '',
                            'url': url.strip() if url else ''
                        })

            return matched_rows

        except HttpError as err:
            print(f'Error reading management sheet: {err}')
            return []

    def _get_hyperlinks_from_column(self, sheet_name, column, start_row, end_row):
        """
        指定列のハイパーリンクを取得

        Args:
            sheet_name (str): シート名
            column (str): 列名（例: 'AA'）
            start_row (int): 開始行
            end_row (int): 終了行

        Returns:
            dict: 行番号をキー、ハイパーリンクURLを値とする辞書
        """
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id,
                ranges=[f"'{sheet_name}'!{column}{start_row}:{column}{end_row}"],
                includeGridData=True
            ).execute()

            hyperlinks = {}

            for sheet in result.get('sheets', []):
                for data in sheet.get('data', []):
                    row_data = data.get('rowData', [])
                    for i, row in enumerate(row_data):
                        row_number = start_row + i
                        cells = row.get('values', [])
                        if cells:
                            cell = cells[0]
                            hyperlink = cell.get('hyperlink', '')
                            if hyperlink:
                                hyperlinks[row_number] = hyperlink

            return hyperlinks

        except HttpError as err:
            print(f'Warning: Could not get hyperlinks: {err}')
            return {}

    def copy_to_kickstarter_sheet(self, rows, clear_existing=True):
        """
        管理表から抽出した行をkickstarterシートにコピー

        Args:
            rows (list): get_rows_by_status()の戻り値
            clear_existing (bool): 既存データをクリアするか

        Returns:
            int: コピーした行数
        """
        if not rows:
            print("コピーする行がありません")
            return 0

        try:
            if clear_existing:
                # kickstarterシートの既存データをクリア（ヘッダー以外）
                self.service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{self.sheet_name}'!A2:K1000"
                ).execute()
                print(f"✓ {self.sheet_name}シートの既存データをクリアしました")

            # データを準備
            values_to_write = []
            for i, row in enumerate(rows, 1):
                # ステータスからテンプレートを自動選択（設定シートから読み込み）
                template = self.get_template_for_status(row['status'])

                values_to_write.append([
                    i,                  # A: NO
                    row['url'],         # B: product_url
                    template,           # C: template（自動選択）
                    row['name'],        # D: name
                    row['email'],       # E: to_email
                    '',                 # F: jp_subject（空）
                    '',                 # G: en_subject（空）
                    '',                 # H: jp_body（空）
                    '',                 # I: en_body（空）
                    '',                 # J: jp_body_html（空）
                    '',                 # K: en_body_html（空）
                ])

            # kickstarterシートに書き込み
            body = {'values': values_to_write}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.sheet_name}'!A2:K{len(values_to_write) + 1}",
                valueInputOption='RAW',
                body=body
            ).execute()

            print(f"✓ {len(values_to_write)}行をkickstarterシートにコピーしました")
            return len(values_to_write)

        except HttpError as err:
            print(f'Error copying to kickstarter sheet: {err}')
            return 0

    def get_available_statuses(self):
        """
        管理表で使用されている全ステータスを取得

        Returns:
            dict: ステータスと件数の辞書
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.management_sheet}'!F{self.DATA_START_ROW}:F1000"
            ).execute()

            values = result.get('values', [])
            status_count = {}

            for row in values:
                status = row[0].strip() if row and row[0] else '(空白)'
                status_count[status] = status_count.get(status, 0) + 1

            return status_count

        except HttpError as err:
            print(f'Error getting statuses: {err}')
            return {}


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
