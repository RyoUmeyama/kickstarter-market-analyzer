#!/usr/bin/env python3
"""
Kickstarterスクレイピングモジュール
プロジェクトURLから製品情報を取得
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from datetime import datetime


class KickstarterScraper:
    """Kickstarterプロジェクト情報を取得するクラス"""

    # User-Agentのリスト（ランダム化）
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]

    def __init__(self, max_retries=3, retry_delay=5, debug=False):
        """
        Args:
            max_retries (int): 最大リトライ回数
            retry_delay (int): リトライ間隔の初期値（秒）
            debug (bool): デバッグモード
        """
        self.session = requests.Session()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.debug = debug
        self._update_headers()

    def _update_headers(self, referer=None):
        """ヘッダーを更新（ランダムUser-Agent含む）"""
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin' if referer else 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }

        if referer:
            headers['Referer'] = referer

        self.session.headers.update(headers)

    def fetch_project_data(self, url):
        """
        Kickstarterプロジェクトのデータを取得（リトライ付き）

        Args:
            url (str): KickstarterプロジェクトURL

        Returns:
            dict: プロジェクト情報
        """
        for attempt in range(self.max_retries):
            try:
                print(f"Fetching: {url} (attempt {attempt + 1}/{self.max_retries})")

                # ヘッダーを更新（User-Agentランダム化）
                self._update_headers()

                # 待機時間を追加（2回目以降）
                if attempt > 0:
                    wait_time = self.retry_delay * (2 ** attempt) + random.uniform(1, 3)
                    print(f"  Waiting {wait_time:.1f} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    # 初回も軽く待機（人間らしい動作）
                    time.sleep(random.uniform(1, 3))

                # 2ステップアプローチ：まずホームページを訪問
                if attempt == 0:
                    try:
                        print(f"  Step 1: Visiting Kickstarter homepage...")
                        home_response = self.session.get('https://www.kickstarter.com/', timeout=10)
                        time.sleep(random.uniform(1, 2))
                    except:
                        pass  # ホームページ訪問は失敗してもOK

                # Refererを設定してリクエスト送信
                self._update_headers(referer='https://www.kickstarter.com/')
                print(f"  Step 2: Fetching project page...")
                response = self.session.get(url, timeout=30, allow_redirects=True)

                # ステータスコード確認
                if response.status_code == 403:
                    print(f"  ✗ Access forbidden (403). Retrying with different User-Agent...")
                    continue
                elif response.status_code == 429:
                    print(f"  ✗ Rate limited (429). Waiting longer...")
                    time.sleep(30)
                    continue
                elif response.status_code != 200:
                    print(f"  ✗ HTTP {response.status_code}")
                    continue

                html = response.text

                # デバッグモード：HTMLサンプルを出力
                if self.debug:
                    print(f"\n  === HTML Sample (first 1000 chars) ===")
                    print(html[:1000])
                    print(f"  === End Sample ===\n")
                    print(f"  Response headers: {dict(response.headers)}\n")

                # HTMLの長さチェック（空のレスポンスやエラーページの検出）
                if len(html) < 1000:
                    print(f"  ⚠️  Response too short ({len(html)} bytes). Might be blocked.")
                    if self.debug:
                        print(f"  Full response:\n{html}")
                    continue

                # データ抽出
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

                # データ取得成功の確認（製品名が取れているか）
                if data['product_name'] != '不明':
                    print(f"✓ Data extracted: {data['product_name']}")
                    return data
                else:
                    print(f"  ⚠️  Product name not found. Retrying...")
                    continue

            except requests.RequestException as e:
                print(f"  ✗ Request error: {e}")
                if attempt < self.max_retries - 1:
                    continue
                else:
                    return self._error_response(url, str(e))

        # 全てのリトライが失敗
        print(f"✗ Failed to fetch data after {self.max_retries} attempts")
        return self._error_response(url, f"Failed after {self.max_retries} attempts")

    def _extract_product_name(self, html):
        """製品名を抽出"""
        # og:titleから取得
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1).replace(' — Kickstarter', '').strip()

        # titleタグから取得
        match = re.search(r'<title>([^<]+)</title>', html, re.I)
        if match:
            return match.group(1).replace(' — Kickstarter', '').strip()

        return '不明'

    def _extract_pledge_amounts(self, html):
        """プレッジ金額を抽出（複数）"""
        amounts = set()

        # パターン1: data-reward属性
        pattern = re.compile(r'data-reward[^>]*minimum[^>]*=["\'](\d+)["\']', re.I)
        for match in pattern.finditer(html):
            amounts.add(int(match.group(1)))

        # パターン2: JSON内のminimum
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
        """総支援額を抽出（USD）"""
        # パターン1: data-pledged属性
        match = re.search(r'data-pledged=["\']([^"\']+)["\']', html, re.I)
        if match:
            amount_str = re.sub(r'[^0-9.]', '', match.group(1))
            try:
                return float(amount_str)
            except ValueError:
                pass

        # パターン2: JSON内のpledged
        match = re.search(r'"pledged"[^}]*"amount"[^}]*:\s*"?(\d+(?:\.\d+)?)"?', html, re.I)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # パターン3: テキストパターン
        match = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:USD\s*)?pledged', html, re.I)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                pass

        return 0

    def _extract_backers(self, html):
        """支援者数を抽出"""
        # パターン1: data-backers-count
        match = re.search(r'data-backers-count=["\']([^"\']+)["\']', html, re.I)
        if match:
            return int(match.group(1))

        # パターン2: JSON内のbackers_count
        match = re.search(r'"backers_count"[^}]*:\s*(\d+)', html, re.I)
        if match:
            return int(match.group(1))

        # パターン3: テキストパターン
        match = re.search(r'([\d,]+)\s+backers?', html, re.I)
        if match:
            return int(match.group(1).replace(',', ''))

        return 0

    def _extract_category(self, html):
        """カテゴリを抽出"""
        # data-category属性
        match = re.search(r'data-category=["\']([^"\']+)["\']', html, re.I)
        if match:
            return match.group(1)

        # JSON内のcategory
        match = re.search(r'"category"[^}]*"name"[^}]*:\s*"([^"]+)"', html, re.I)
        if match:
            return match.group(1)

        return '不明'

    def _extract_end_date(self, html):
        """終了日を抽出"""
        # data-end_time属性
        match = re.search(r'data-end[_-]time=["\']([^"\']+)["\']', html, re.I)
        if match:
            try:
                timestamp = int(match.group(1))
                from datetime import datetime
                date = datetime.fromtimestamp(timestamp)
                return date.strftime('%Y年%m月%d日')
            except (ValueError, OSError):
                pass

        # ISO日付形式
        match = re.search(r'"deadline"[^}]*:\s*"([^"]+)"', html, re.I)
        if match:
            try:
                from datetime import datetime
                date = datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
                return date.strftime('%Y年%m月%d日')
            except ValueError:
                pass

        return '不明'

    def _extract_description(self, html):
        """製品説明を抽出"""
        # og:description
        match = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1)[:500]

        # meta description
        match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.I)
        if match:
            return match.group(1)[:500]

        return '説明なし'

    def _extract_goal_amount(self, html):
        """ゴール金額を抽出"""
        # data-goal属性
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


def test_scraper():
    """スクレイパーのテスト"""
    import sys

    # デバッグモードの判定
    debug = '--debug' in sys.argv or '-d' in sys.argv

    scraper = KickstarterScraper(max_retries=3, retry_delay=5, debug=debug)

    test_url = 'https://www.kickstarter.com/projects/beehivebooks/gulliver'

    print("=" * 60)
    print("Kickstarter Scraper Test (Enhanced)")
    print("=" * 60)
    print(f"URL: {test_url}")
    print(f"Debug Mode: {debug}")
    print(f"Max Retries: 3\n")

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
    test_scraper()
