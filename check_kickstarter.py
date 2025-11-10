#!/usr/bin/env python3
"""
Kickstarter Market Analyzer - メインスクリプト
Kickstarterから製品情報を取得し、ChatGPTで市場分析レポートを生成して
Google Sheetsに書き込む
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

from kickstarter_scraper_selenium import KickstarterScraperSelenium
from openai_client_improved import ImprovedMarketReportGenerator as MarketReportGenerator
from sheets_client import GoogleSheetsClient


def main():
    """メイン処理"""
    print("=" * 60)
    print("Kickstarter Market Analyzer")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 環境変数読み込み
    load_dotenv()

    # デバッグモード確認
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    if debug_mode:
        print("⚠️  DEBUG MODE: ON\n")

    # 設定確認
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    sheet_name = os.getenv('SHEET_NAME', 'kickstarter')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    business_context = os.getenv('BUSINESS_CONTEXT', '')

    if not spreadsheet_id:
        print("❌ Error: SPREADSHEET_ID not set in .env")
        sys.exit(1)

    if not openai_api_key:
        print("❌ Error: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    # クライアント初期化
    print("Initializing clients...")
    try:
        print("  - Initializing Kickstarter scraper (Selenium headless mode)...")
        scraper = KickstarterScraperSelenium(headless=True)
        print("  ✓ Kickstarter scraper initialized")

        print(f"  - Initializing OpenAI client (model: {openai_model})...")
        generator = MarketReportGenerator(api_key=openai_api_key, model=openai_model)
        print("  ✓ OpenAI client initialized")

        print(f"  - Initializing Google Sheets client...")
        print(f"    Spreadsheet ID: {spreadsheet_id}")
        print(f"    Sheet Name: {sheet_name}")
        sheets_client = GoogleSheetsClient(spreadsheet_id, sheet_name)
        print("  ✓ Google Sheets client initialized")

        print("✓ All clients initialized successfully\n")

        if business_context:
            print(f"📝 Business Context loaded ({len(business_context)} characters)")
            print(f"   {business_context[:100]}...\n")
    except Exception as e:
        print(f"❌ Error initializing clients: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 未処理の行を取得
    print("Fetching unprocessed rows from spreadsheet...")
    unprocessed_rows = sheets_client.get_unprocessed_rows()
    print(f"✓ Found {len(unprocessed_rows)} unprocessed rows\n")

    if not unprocessed_rows:
        print("No unprocessed rows found. Exiting.")
        return

    # 各行を処理
    success_count = 0
    error_count = 0

    try:
        for i, row_data in enumerate(unprocessed_rows, 1):
            row_number = row_data['row_number']
            url = row_data['url']
            product_name = row_data['product_name']
            maker_name = row_data['maker_name']
            creator_name = row_data['creator_name']

            print(f"[{i}/{len(unprocessed_rows)}] Processing row {row_number}")
            print(f"  URL: {url}")
            print(f"  Product: {product_name}")
            print(f"  Maker: {maker_name}\n")

            try:
                # Step 1: Kickstarterからデータ取得
                print("  [1/4] Scraping Kickstarter...")
                print(f"    URL: {url}")
                kickstarter_data = scraper.fetch_project_data(url)

                if 'error' in kickstarter_data:
                    print(f"  ⚠️  Warning: {kickstarter_data['error']}")
                    # エラーでも続行（取得できたデータで生成）
                else:
                    print(f"    ✓ Successfully scraped project data")
                    print(f"    Product: {kickstarter_data.get('product_name', 'N/A')}")
                    print(f"    Pledged: {kickstarter_data.get('pledged', 'N/A')}")
                    print(f"    Backers: {kickstarter_data.get('backers', 'N/A')}")

                # 商品名が空の場合、スクレイピング結果を使用
                if not product_name:
                    product_name = kickstarter_data.get('product_name', '不明')

                time.sleep(2)  # レート制限対策

                # Step 2: ChatGPTでレポート生成（日本語）
                print("  [2/4] Generating Japanese report with ChatGPT...")
                print(f"    Model: {openai_model}")
                print(f"    Maker: {maker_name or 'メーカー名不明'}")
                print(f"    Creator: {creator_name or 'クリエーター名不明'}")
                if business_context:
                    print(f"    Business Context: {len(business_context)} characters")
                japanese_report = generator.generate_japanese_report(
                    kickstarter_data,
                    maker_name or 'メーカー名不明',
                    creator_name or 'クリエーター名不明',
                    business_context
                )
                print(f"    ✓ Japanese report generated ({len(japanese_report)} characters)")

                time.sleep(2)  # レート制限対策

                # Step 3: ChatGPTでレポート生成（英語）- オプション
                english_report = None
                if not debug_mode:
                    print("  [3/4] Generating English report with ChatGPT...")
                    english_report = generator.generate_english_report(
                        kickstarter_data,
                        maker_name or 'Unknown Maker',
                        creator_name or 'Unknown Creator'
                    )
                    print(f"    ✓ English report generated ({len(english_report)} characters)")
                    time.sleep(2)
                else:
                    print("  [3/4] Skipping English report (DEBUG_MODE=true)")

                # Step 4: Google Sheetsに書き込み
                print("  [4/4] Writing to spreadsheet...")
                print(f"    Writing to row {row_number} (K{row_number} and L{row_number})")
                sheets_client.write_report(row_number, japanese_report, english_report)

                print(f"  ✓ Row {row_number} completed successfully\n")
                success_count += 1

            except Exception as e:
                print(f"  ❌ Error processing row {row_number}: {e}\n")
                error_count += 1

                # エラーメッセージをスプレッドシートに書き込み
                try:
                    error_message = f"エラー: {str(e)}"
                    sheets_client.write_report(row_number, error_message)
                except:
                    pass

            # 次の行の前に少し待機
            if i < len(unprocessed_rows):
                time.sleep(3)

    finally:
        # Seleniumドライバーをクリーンアップ
        print("\nCleaning up resources...")
        scraper.close()

    # サマリー
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total processed: {len(unprocessed_rows)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
