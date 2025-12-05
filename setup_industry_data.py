#!/usr/bin/env python3
"""
業界データをスプレッドシートに設定するスクリプト
設定シートのL列に業界統計データを書き込む
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

# .envファイルを読み込み
load_dotenv()

# 業界データ（ソース付き）
INDUSTRY_DATA = [
    # ヘッダー行
    ["項目", "数値", "ソース"],
    # クラウドファンディング市場
    ["日本CF市場規模（購入型）", "432億円（2024年）", "PR TIMES 2024"],
    ["Makuake市場シェア", "44.4%", "クラウドファンディングチャンネル 2024"],
    ["CAMPFIRE市場シェア", "32.3%", "クラウドファンディングチャンネル 2024"],
    ["READYFOR市場シェア", "13.8%", "クラウドファンディングチャンネル 2024"],
    ["月間新規CFプロジェクト数", "約2,050件", "クラウドファンディングチャンネル 2024"],
    ["CFプロジェクト平均成功率", "約40%", "Makuake公式 2024"],
    # ガジェット・電子機器市場
    ["日本ガジェット市場規模", "約3兆円（2024年）", "矢野経済研究所"],
    ["日本EC市場規模（BtoC）", "約23兆円（2024年）", "経済産業省"],
    ["Amazon Japan年間流通総額", "約4.2兆円", "Amazon Japan 2024"],
    ["楽天市場年間流通総額", "約5.6兆円", "楽天グループ 2024"],
    # Kickstarter関連
    ["Kickstarter総プロジェクト数", "60万件以上（2024年）", "Kickstarter公式"],
    ["Kickstarter成功率", "約38%", "Kickstarter公式"],
    ["Kickstarter日本人支援者数", "増加傾向（詳細非公開）", "Kickstarter Japan"],
]


def main():
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return

    print("=" * 60)
    print("業界データ設定スクリプト")
    print("=" * 60)

    # Google Sheetsクライアントを初期化
    print("\nGoogle Sheets認証中...")
    client = GoogleSheetsClient(spreadsheet_id, 'kickstarter')
    print("✓ 認証成功！\n")

    # L1にヘッダーを書き込み
    print("設定シートに業界データを書き込み中...")

    try:
        # L1:N1にヘッダー「業界データ」を書き込み
        header_range = "'設定'!L1:N1"
        header_body = {'values': [["業界データ", "", ""]]}
        client.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=header_range,
            valueInputOption='RAW',
            body=header_body
        ).execute()
        print("✓ L1にヘッダー「業界データ」を書き込みました")

        # L2:N以降にデータを書き込み
        data_range = f"'設定'!L2:N{len(INDUSTRY_DATA) + 1}"
        data_body = {'values': INDUSTRY_DATA}
        client.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=data_range,
            valueInputOption='RAW',
            body=data_body
        ).execute()
        print(f"✓ L2:N{len(INDUSTRY_DATA) + 1}に業界データ（{len(INDUSTRY_DATA)}行）を書き込みました")

        print("\n" + "=" * 60)
        print("✅ 業界データの設定が完了しました！")
        print("=" * 60)

        # 確認のためデータを読み取り
        print("\n設定されたデータの確認:")
        industry_data = client.get_industry_data()
        if industry_data:
            print(industry_data)

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
