#!/usr/bin/env python3
"""
改行文字をHTML<br>タグに変換するユーティリティ

Thunderbirdのメールマージで使用するために、
テキストの改行をHTMLの<br>タグに変換します。
"""

def convert_text_to_html(text):
    """
    プレーンテキストの改行をHTML<br>タグに変換

    Args:
        text (str): プレーンテキスト

    Returns:
        str: HTMLタグに変換されたテキスト
    """
    if not text:
        return text

    # 改行をHTMLの<br>タグに変換
    html_text = text.replace('\n', '<br>\n')

    return html_text


def convert_csv_for_html_mail(input_csv, output_csv):
    """
    CSVファイルの jp_body と en_body 列を HTML形式に変換

    Args:
        input_csv (str): 入力CSVファイルパス
        output_csv (str): 出力CSVファイルパス
    """
    import csv

    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        rows = []
        for row in reader:
            # jp_body と en_body の改行を<br>タグに変換
            if 'jp_body' in row and row['jp_body']:
                row['jp_body'] = convert_text_to_html(row['jp_body'])

            if 'en_body' in row and row['en_body']:
                row['en_body'] = convert_text_to_html(row['en_body'])

            rows.append(row)

    with open(output_csv, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ HTML形式に変換完了: {output_csv}")
    print(f"  変換行数: {len(rows)}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("使用方法: python convert_newlines_to_html.py <入力CSV> [出力CSV]")
        print("例: python convert_newlines_to_html.py kickstarter.csv kickstarter_html.csv")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else input_csv.replace('.csv', '_html.csv')

    convert_csv_for_html_mail(input_csv, output_csv)
