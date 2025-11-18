#!/usr/bin/env python3
"""
Google Spreadsheetsの全シートを総当たりでダウンロード
GIDを0から順番に試す
"""

import requests
import csv


def download_sheet_by_gid(spreadsheet_id, gid):
    """
    特定のGIDのシートをCSVでダウンロード

    Returns:
        tuple: (success, row_count, col_count)
    """
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # CSVとして読み込んで行数・列数を確認
        content = response.content.decode('utf-8')
        lines = content.split('\n')

        if len(lines) <= 1:
            return False, 0, 0

        # 最初の行から列数を取得
        reader = csv.reader([lines[0]])
        first_row = next(reader)
        col_count = len(first_row)

        # ファイルに保存
        output_file = f"/tmp/sheet_gid_{gid}.csv"
        with open(output_file, 'wb') as f:
            f.write(response.content)

        return True, len(lines), col_count

    except Exception as e:
        return False, 0, 0


def get_sheet_header(spreadsheet_id, gid):
    """
    シートのヘッダー行（最初の数行）を取得
    """
    try:
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        content = response.content.decode('utf-8')
        lines = content.split('\n')[:5]  # 最初の5行

        return lines

    except:
        return []


def analyze_sheet_content(file_path, gid):
    """
    シートの内容を分析
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return

        # 非空白行数
        non_empty_rows = sum(1 for row in rows if any(cell.strip() for cell in row))

        print(f"  Total rows: {len(rows)}")
        print(f"  Non-empty rows: {non_empty_rows}")

        # ヘッダー行を推測（最初の数行から）
        print(f"\n  First 3 rows:")
        for i, row in enumerate(rows[:3], 1):
            print(f"    Row {i}:")
            # 最初の15列のみ表示（空でないセル）
            displayed = 0
            for col_idx, cell in enumerate(row, 1):
                if cell.strip() and displayed < 15:
                    cell_preview = str(cell)[:60] + '...' if len(str(cell)) > 60 else str(cell)
                    col_letter = ''
                    # 列番号を列名に変換（A, B, ..., Z, AA, AB, ...）
                    num = col_idx
                    while num > 0:
                        num, remainder = divmod(num - 1, 26)
                        col_letter = chr(65 + remainder) + col_letter
                    print(f"      {col_letter}: {cell_preview}")
                    displayed += 1
            if displayed == 0:
                print(f"      (empty row)")

        # Kickstarter URLを含む列を検索
        print(f"\n  Searching for Kickstarter URLs...")
        url_columns = []
        for row_idx, row in enumerate(rows[:20], 1):  # 最初の20行を検索
            for col_idx, cell in enumerate(row, 1):
                if 'kickstarter.com' in cell.lower():
                    num = col_idx
                    col_letter = ''
                    while num > 0:
                        num, remainder = divmod(num - 1, 26)
                        col_letter = chr(65 + remainder) + col_letter
                    url_columns.append((row_idx, col_letter, cell[:80]))

        if url_columns:
            print(f"  ✓ Found Kickstarter URLs in:")
            for row, col, url in url_columns[:5]:  # 最初の5つ
                print(f"    Row {row}, Column {col}: {url}")
        else:
            print(f"  ✗ No Kickstarter URLs found in first 20 rows")

    except Exception as e:
        print(f"  Error analyzing: {e}")


def scan_all_sheets(spreadsheet_id, max_gid=100):
    """
    GID 0から順番に全シートをスキャン

    Args:
        spreadsheet_id (str): スプレッドシートID
        max_gid (int): 最大GID（この数まで試す）
    """
    print("=" * 80)
    print("Google Spreadsheet Scanner (Brute Force GID)")
    print("=" * 80)
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Scanning GIDs from 0 to {max_gid}...\n")

    found_sheets = []

    for gid in range(max_gid + 1):
        success, rows, cols = download_sheet_by_gid(spreadsheet_id, gid)

        if success:
            print(f"✓ GID {gid}: Found sheet ({rows} rows × {cols} cols)")
            found_sheets.append((gid, rows, cols))
        else:
            # 進捗を表示（見つからない場合は何も表示しない）
            pass

    print(f"\n" + "=" * 80)
    print(f"Scan complete! Found {len(found_sheets)} sheets:")
    print("=" * 80)

    for i, (gid, rows, cols) in enumerate(found_sheets, 1):
        print(f"\nSheet {i} (GID: {gid})")
        print(f"  Rows: {rows}")
        print(f"  Cols: {cols}")

    # 各シートの詳細を分析
    print(f"\n" + "=" * 80)
    print("Detailed Analysis:")
    print("=" * 80)

    for i, (gid, rows, cols) in enumerate(found_sheets, 1):
        print(f"\n{'=' * 80}")
        print(f"Sheet {i} - GID {gid}")
        print(f"{'=' * 80}")

        file_path = f"/tmp/sheet_gid_{gid}.csv"
        analyze_sheet_content(file_path, gid)

    print(f"\n" + "=" * 80)
    print("All sheets analyzed!")
    print("=" * 80)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        spreadsheet_id = sys.argv[1]
    else:
        spreadsheet_id = '1vAVnv3oYUm_J2eIvDNrJi6fUcnpLYSb8Q2Y_aq6NDqM'

    # GID 0-100までスキャン（通常は0-10で十分だが、念のため）
    scan_all_sheets(spreadsheet_id, max_gid=100)
