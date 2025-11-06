#!/usr/bin/env python3
"""
Kickstarterスクレイピングモジュール
プロジェクトURLから製品情報を取得
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime


class KickstarterScraper:
    """Kickstarterプロジェクト情報を取得するクラス"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.kickstarter.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })

    def fetch_project_data(self, url):
        """
        Kickstarterプロジェクトのデータを取得

        Args:
            url (str): KickstarterプロジェクトURL

        Returns:
            dict: プロジェクト情報
        """
        try:
            print(f"Fetching: {url}")

            # リクエスト送信
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            html = response.text

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

            print(f"✓ Data extracted: {data['product_name']}")
            return data

        except requests.RequestException as e:
            print(f"✗ Error fetching {url}: {e}")
            return self._error_response(url, str(e))

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
    scraper = KickstarterScraper()

    test_url = 'https://www.kickstarter.com/projects/beehivebooks/gulliver'

    print("=" * 60)
    print("Kickstarter Scraper Test")
    print("=" * 60)
    print(f"URL: {test_url}\n")

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


if __name__ == '__main__':
    test_scraper()
