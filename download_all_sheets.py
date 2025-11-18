#!/usr/bin/env python3
"""
公開Google Spreadsheetsの全シートをCSVでダウンロード
認証不要で公開スプレッドシートからデータを取得
"""

import requests
import csv
import re


def get_all_sheet_gids(spreadsheet_id):
    """
    公開スプレッドシートの全シートGIDを取得

    Args:
        spreadsheet_id (str): スプレッドシートID

    Returns:
        list: (sheet_name, gid) のリスト
    """
    # スプレッドシートのHTMLを取得してシート情報を抽出
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    try:
        response = requests.get(url)
        response.raise_for_status()
        html = response.text

        # シート情報を正規表現で抽出
        # パターン: "name":"シート名"..."id":"数値"
        sheet_pattern = r'"name":"([^"]+)"[^}]*"id":"(\d+)"'
        matches = re.findall(sheet_pattern, html)

        if matches:
            sheets = [(name, gid) for name, gid in matches]
            return sheets

        # 代替パターン
        sheet_pattern2 = r'\["([^"]+)".*?,"(\d+)"\]'
        matches2 = re.findall(sheet_pattern2, html)

        if matches2:
            sheets = [(name, gid) for name, gid in matches2 if gid.isdigit()]
            return sheets

        print("Warning: Could not extract sheet information from HTML")
        return []

    except Exception as e:
        print(f"Error fetching spreadsheet metadata: {e}")
        return []


def download_sheet_as_csv(spreadsheet_id, gid, output_file):
    """
    特定のシートをCSV形式でダウンロード

    Args:
        spreadsheet_id (str): スプレッドシートID
        gid (str): シートGID
        output_file (str): 出力ファイルパス

    Returns:
        bool: 成功した場合True
    """
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        with open(output_file, 'wb') as f:
            f.write(response.content)

        return True

    except Exception as e:
        print(f"Error downloading sheet {gid}: {e}")
        return False


def analyze_csv(file_path, max_rows=10):
    """
    CSVファイルを分析して構造を表示

    Args:
        file_path (str): CSVファイルパス
        max_rows (int): 表示する最大行数
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            print("  (Empty sheet)")
            return

        # ヘッダー行
        print(f"\n  Header (Row 1):")
        if len(rows) > 0:
            headers = rows[0]
            for i, header in enumerate(headers, 1):
                if header:  # 空でない列のみ表示
                    print(f"    Column {chr(64+i)}: {header}")

        # 行数
        print(f"\n  Total rows: {len(rows)}")

        # 非空白行数
        non_empty_rows = sum(1 for row in rows if any(cell.strip() for cell in row))
        print(f"  Non-empty rows: {non_empty_rows}")

        # サンプルデータ
        if len(rows) > 1:
            sample_count = min(len(rows), max_rows)
            print(f"\n  Sample data (Rows 2-{sample_count}):")
            for row_idx, row in enumerate(rows[1:sample_count], 2):
                # 空行はスキップ
                if not any(cell.strip() for cell in row):
                    continue

                print(f"\n    Row {row_idx}:")
                for col_idx, cell in enumerate(row[:10], 1):  # 最初の10列まで
                    if cell:  # 空でないセルのみ表示
                        cell_preview = str(cell)[:80] + '...' if len(str(cell)) > 80 else str(cell)
                        print(f"      {chr(64+col_idx)}: {cell_preview}")

    except Exception as e:
        print(f"  Error analyzing CSV: {e}")


def download_and_analyze_all_sheets(spreadsheet_id):
    """
    スプレッドシートの全シートをダウンロードして分析

    Args:
        spreadsheet_id (str): スプレッドシートID
    """
    print("=" * 80)
    print("Google Spreadsheet Inspector (No Auth Required)")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}\n")

    print("Fetching sheet list...")
    sheets = get_all_sheet_gids(spreadsheet_id)

    if not sheets:
        # デフォルトのシートGIDを試す
        print("Could not detect sheets automatically. Trying default GID...")
        sheets = [("Sheet1", "0"), ("Sheet2", "53120128")]

    print(f"✓ Found {len(sheets)} sheet(s)\n")

    for i, (sheet_name, gid) in enumerate(sheets, 1):
        print("=" * 80)
        print(f"Sheet {i}: {sheet_name} (GID: {gid})")
        print("=" * 80)

        output_file = f"/tmp/sheet_{gid}_{sheet_name.replace(' ', '_')}.csv"

        print(f"Downloading...")
        if download_sheet_as_csv(spreadsheet_id, gid, output_file):
            print(f"✓ Downloaded to: {output_file}")

            print(f"\nAnalyzing...")
            analyze_csv(output_file)
        else:
            print(f"✗ Failed to download")

        print()

    print("=" * 80)
    print("Inspection complete!")
    print("=" * 80)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1]
    else:
        spreadsheet_id = '1vAVnv3oYUm_J2eIvDNrJi6fUcnpLYSb8Q2Y_aq6NDqM'

    download_and_analyze_all_sheets(spreadsheet_id)
