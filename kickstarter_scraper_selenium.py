#!/usr/bin/env python3
"""
Kickstarterスクレイピングモジュール（Selenium版）
実際のブラウザを使用してBot検出を回避
"""

import time
import random
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class KickstarterScraperSelenium:
    """Selenium を使用したKickstarterスクレイパー"""

    def __init__(self, headless=True):
        """
        Args:
            headless (bool): ヘッドレスモード（画面非表示）
        """
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Chromeドライバーを初期化"""
        options = Options()

        if self.headless:
            options.add_argument('--headless=new')

        # Bot検出回避のためのオプション
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # User-Agent設定
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')

        # ウィンドウサイズ
        options.add_argument('--window-size=1920,1080')

        try:
            self.driver = webdriver.Chrome(options=options)

            # WebDriver検出を回避するJavaScriptを実行
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })

            return True

        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            print("\nSeleniumとChromeDriverのインストールが必要です：")
            print("  pip install selenium")
            print("  brew install chromedriver  # Mac")
            return False

    def fetch_project_data(self, url):
        """
        Kickstarterプロジェクトのデータを取得

        Args:
            url (str): KickstarterプロジェクトURL

        Returns:
            dict: プロジェクト情報
        """
        if not self.driver:
            if not self._init_driver():
                return self._error_response(url, "Failed to initialize Chrome driver")

        try:
            print(f"Fetching: {url}")

            # ページにアクセス
            self.driver.get(url)

            # ページロード待機
            time.sleep(random.uniform(3, 5))

            # HTMLを取得
            html = self.driver.page_source

            # データ抽出（既存のメソッドを使用）
            data = {
                'url': url,
                'product_name': self._extract_product_name(html),
                'pledge_amounts': self._extract_pledge_amounts(html),
                'funding_total_usd': self._extract_funding_total(html),
                'funding_total_jpy': 0,
                'backers': self._extract_backers(html),
                'category': self._extract_category(html),
                'end_date': self._extract_end_date(html),
                'description': self._extract_description(html),
                'goal_amount_usd': self._extract_goal_amount(html),
                'fetched_at': datetime.now().isoformat()
            }

            # 円換算
            if data['funding_total_usd'] > 0:
                data['funding_total_jpy'] = int(data['funding_total_usd'] * 150)

            print(f"✓ Data extracted: {data['product_name']}")
            return data

        except Exception as e:
            print(f"✗ Error: {e}")
            return self._error_response(url, str(e))

    def close(self):
        """ドライバーを閉じる"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """コンテキストマネージャー"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー"""
        self.close()

    # データ抽出メソッド（requests版と同じ）
    def _extract_product_name(self, html):
        """製品名を抽出"""
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1).replace(' — Kickstarter', '').strip()

        match = re.search(r'<title>([^<]+)</title>', html, re.I)
        if match:
            return match.group(1).replace(' — Kickstarter', '').strip()

        return '不明'

    def _extract_pledge_amounts(self, html):
        """プレッジ金額を抽出"""
        amounts = set()

        pattern = re.compile(r'data-reward[^>]*minimum[^>]*=["\'](\d+)["\']', re.I)
        for match in pattern.finditer(html):
            amounts.add(int(match.group(1)))

        pattern = re.compile(r'"minimum"[^}]*:\s*(\d+)', re.I)
        for match in pattern.finditer(html):
            amount = int(match.group(1))
            if 0 < amount < 100000:
                amounts.add(amount)

        if not amounts:
            return '不明'

        sorted_amounts = sorted(amounts)
        return ', '.join([f'${amt} (約{int(amt * 150):,}円)' for amt in sorted_amounts])

    def _extract_funding_total(self, html):
        """総支援額を抽出"""
        match = re.search(r'data-pledged=["\']([^"\']+)["\']', html, re.I)
        if match:
            amount_str = re.sub(r'[^0-9.]', '', match.group(1))
            try:
                return float(amount_str)
            except ValueError:
                pass

        match = re.search(r'"pledged"[^}]*"amount"[^}]*:\s*"?(\d+(?:\.\d+)?)"?', html, re.I)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return 0

    def _extract_backers(self, html):
        """支援者数を抽出"""
        match = re.search(r'data-backers-count=["\']([^"\']+)["\']', html, re.I)
        if match:
            return int(match.group(1))

        match = re.search(r'"backers_count"[^}]*:\s*(\d+)', html, re.I)
        if match:
            return int(match.group(1))

        match = re.search(r'([\d,]+)\s+backers?', html, re.I)
        if match:
            return int(match.group(1).replace(',', ''))

        return 0

    def _extract_category(self, html):
        """カテゴリを抽出"""
        match = re.search(r'data-category=["\']([^"\']+)["\']', html, re.I)
        if match:
            return match.group(1)

        match = re.search(r'"category"[^}]*"name"[^}]*:\s*"([^"]+)"', html, re.I)
        if match:
            return match.group(1)

        return '不明'

    def _extract_end_date(self, html):
        """終了日を抽出"""
        match = re.search(r'data-end[_-]time=["\']([^"\']+)["\']', html, re.I)
        if match:
            try:
                timestamp = int(match.group(1))
                date = datetime.fromtimestamp(timestamp)
                return date.strftime('%Y年%m月%d日')
            except (ValueError, OSError):
                pass

        return '不明'

    def _extract_description(self, html):
        """製品説明を抽出"""
        match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1)[:500]

        match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1)[:500]

        return '説明なし'

    def _extract_goal_amount(self, html):
        """ゴール金額を抽出"""
        match = re.search(r'data-goal=["\']([^"\']+)["\']', html, re.I)
        if match:
            amount_str = re.sub(r'[^0-9.]', '', match.group(1))
            try:
                return float(amount_str)
            except ValueError:
                pass

        return 0

    def _error_response(self, url, error_message):
        """エラーレスポンス"""
        return {
            'url': url,
            'product_name': '取得失敗',
            'pledge_amounts': '不明',
            'funding_total_usd': 0,
            'funding_total_jpy': 0,
            'backers': 0,
            'category': '不明',
            'end_date': '不明',
            'description': f'エラー: {error_message}',
            'goal_amount_usd': 0,
            'fetched_at': datetime.now().isoformat(),
            'error': error_message
        }


def test_selenium_scraper():
    """Selenium版スクレイパーのテスト"""
    test_url = 'https://www.kickstarter.com/projects/beehivebooks/gulliver'

    print("=" * 60)
    print("Kickstarter Scraper Test (Selenium)")
    print("=" * 60)
    print(f"URL: {test_url}\n")

    with KickstarterScraperSelenium(headless=True) as scraper:
        data = scraper.fetch_project_data(test_url)

        print("\n" + "=" * 60)
        print("Results")
        print("=" * 60)
        print(f"Product Name: {data['product_name']}")
        print(f"Pledge Amounts: {data['pledge_amounts']}")
        print(f"Funding Total: ${data['funding_total_usd']:,.2f} (約{data['funding_total_jpy']:,}円)")
        print(f"Backers: {data['backers']:,}")
        print(f"Category: {data['category']}")
        print(f"End Date: {data['end_date']}")
        print(f"Description: {data['description'][:100]}...")

        if 'error' in data:
            print(f"\n⚠️  Error: {data['error']}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    test_selenium_scraper()
