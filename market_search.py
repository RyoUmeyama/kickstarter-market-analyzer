#!/usr/bin/env python3
"""
市場調査用ウェブ検索モジュール
Makuakeで類似製品を検索し、実在するデータを取得
Playwrightによるブラウザ自動化でJavaScriptレンダリングに対応

重要：架空のデータは絶対に生成しない。取得できない場合は正直に報告する。
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# Playwright関連
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
    print("  ✓ Playwrightモジュールを読み込みました")
except ImportError as e:
    PLAYWRIGHT_AVAILABLE = False
    print(f"  ⚠️ Playwrightモジュールが利用できません: {e}")


class MarketSearcher:
    """クラウドファンディング市場の類似製品検索クラス"""

    def __init__(self, api_key=None, model='gpt-4o-mini'):
        """
        Args:
            api_key (str, optional): OpenAI API key
            model (str, optional): モデル名
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        if self.api_key and self.api_key != 'your-openai-api-key-here':
            self.client = OpenAI(api_key=self.api_key)
            self.api_available = True
        else:
            self.client = None
            self.api_available = False

        # HTTPセッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
        })

        # Playwright（遅延初期化）
        self._playwright = None
        self._browser = None
        self._context = None

    def _get_browser(self, use_proxy=False):
        """
        Playwrightブラウザを取得（遅延初期化）

        Args:
            use_proxy: Trueの場合、Bright Dataプロキシを使用
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("     ⚠️ Playwrightが利用できないためスキップ")
            return None

        # プロキシ使用時は別のブラウザインスタンスを使用
        if use_proxy:
            return self._get_proxy_browser()

        if self._browser is None:
            try:
                print("     Playwrightブラウザを初期化中（直接接続）...")
                self._playwright = sync_playwright().start()

                # Chromiumを使用（より自然なフィンガープリント）
                self._browser = self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                # コンテキスト作成（より自然なブラウザ設定）
                self._context = self._browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='ja-JP',
                    timezone_id='Asia/Tokyo',
                )

                print("     ✓ Playwrightブラウザを初期化しました（直接接続）")

            except Exception as e:
                print(f"     ⚠️ Playwright初期化エラー: {type(e).__name__}: {e}")
                self._browser = None

        return self._browser

    def _get_proxy_browser(self):
        """Bright Dataプロキシ付きブラウザを取得"""
        if not hasattr(self, '_proxy_browser') or self._proxy_browser is None:
            bright_data_username = os.getenv('BRIGHT_DATA_USERNAME')
            bright_data_password = os.getenv('BRIGHT_DATA_PASSWORD')

            if not bright_data_username or not bright_data_password:
                print("     ⚠️ Bright Data未設定 - プロキシを使用できません")
                return None

            try:
                print("     Playwrightブラウザを初期化中（Bright Dataプロキシ）...")

                if self._playwright is None:
                    self._playwright = sync_playwright().start()

                proxy_config = {
                    "server": "brd.superproxy.io:22225",
                    "username": bright_data_username,
                    "password": bright_data_password
                }

                self._proxy_browser = self._playwright.chromium.launch(
                    headless=True,
                    proxy=proxy_config,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                self._proxy_context = self._proxy_browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='ja-JP',
                    timezone_id='Asia/Tokyo',
                    ignore_https_errors=True,  # プロキシ使用時はSSL検証をスキップ
                )

                print("     ✓ Bright Dataプロキシブラウザを初期化しました（日本IP）")

            except Exception as e:
                print(f"     ⚠️ プロキシブラウザ初期化エラー: {type(e).__name__}: {e}")
                self._proxy_browser = None

        return self._proxy_browser

    def _get_context(self, use_proxy=False):
        """適切なブラウザコンテキストを取得"""
        if use_proxy:
            ctx = getattr(self, '_proxy_context', None)
            if ctx:
                return ctx
            print(f"     ⚠️ プロキシコンテキストがありません")
            return None
        return self._context

    def _close_browser(self):
        """Playwrightブラウザを終了"""
        # 直接接続ブラウザを終了
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        # プロキシブラウザを終了
        if hasattr(self, '_proxy_context') and self._proxy_context:
            try:
                self._proxy_context.close()
            except Exception:
                pass
            self._proxy_context = None
        if hasattr(self, '_proxy_browser') and self._proxy_browser:
            try:
                self._proxy_browser.close()
            except Exception:
                pass
            self._proxy_browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def __del__(self):
        """デストラクタ"""
        self._close_browser()

    def _normalize_kickstarter_url(self, kickstarter_url):
        """KickstarterのURLを正規化してベースURLを取得"""
        base_url = kickstarter_url.split('?')[0]
        for suffix in ['/creator', '/description', '/comments', '/updates', '/community', '/faqs', '/rewards']:
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)]
                break
        return base_url

    def _fetch_kickstarter_info_playwright(self, kickstarter_url, use_proxy=False):
        """
        PlaywrightでKickstarterページから製品情報を取得

        Args:
            kickstarter_url: KickstarterのURL
            use_proxy: Trueの場合、Bright Dataプロキシを使用
        """
        base_url = self._normalize_kickstarter_url(kickstarter_url)
        proxy_label = "Bright Dataプロキシ" if use_proxy else "直接接続"
        print(f"     Kickstarter製品情報を取得中（{proxy_label}）...")
        print(f"       URL: {base_url}")

        result = {
            "title": "",
            "description": "",
            "category": "",
            "funding_amount": "",
            "goal_amount": "",
            "percent_funded": 0,
            "backers_count": 0,
            "rewards": [],
            "days_left": "",
            "creator_name": "",
            "data_source": "",
            "source_url": ""
        }

        browser = self._get_browser(use_proxy=use_proxy)
        if not browser:
            print(f"       ⚠️ ブラウザの取得に失敗しました")
            return result

        context = self._get_context(use_proxy=use_proxy)
        if not context:
            print(f"       ⚠️ コンテキストの取得に失敗しました")
            return result

        page = None
        try:
            page = context.new_page()
            print(f"       ページを作成しました")

            # ページにアクセス（loadでページ読み込みを待つ）
            page.goto(base_url, wait_until='load', timeout=60000)
            page.wait_for_timeout(5000)  # JavaScriptのレンダリングを待機

            # ページ内容を取得
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()

            # ブロックされているかチェック
            if 'しばらくお待ちください' in page_text or 'please wait' in page_text.lower():
                print(f"       ⚠️ Kickstarterにブロックされました")
                return result

            # メタタグからタイトル取得
            og_title = soup.find('meta', property='og:title')
            if og_title:
                result['title'] = og_title.get('content', '').replace(' — Kickstarter', '').strip()
                print(f"       タイトル: {result['title'][:50]}...")

            # メタタグから説明取得
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                result['description'] = og_desc.get('content', '')[:500]

            # 資金調達額を複数のパターンで検索
            # パターン1: span.ksr-green-500 (アクティブ), span.soft-black (終了)
            for selector in ['span.ksr-green-500', 'span.soft-black', 'span.money']:
                funding_elem = soup.select_one(selector)
                if funding_elem:
                    funding_text = funding_elem.get_text(strip=True)
                    if re.search(r'[\$€£¥]', funding_text):
                        result['funding_amount'] = funding_text.strip()
                        print(f"       調達額: {result['funding_amount']}")
                        break

            # 目標金額
            goal_match = re.search(r'pledged of\s*([\$€£¥][\d,]+)', page_text)
            if goal_match:
                result['goal_amount'] = goal_match.group(1)
                print(f"       目標額: {result['goal_amount']}")

            # バッカー数
            backers_match = re.search(r'([\d,]+)\s*(?:backers?|人のバッカー)', page_text, re.I)
            if backers_match:
                result['backers_count'] = int(backers_match.group(1).replace(',', ''))
                print(f"       バッカー数: {result['backers_count']}人")

            # 達成率を計算
            if result['funding_amount'] and result['goal_amount']:
                try:
                    funding_num = int(re.search(r'([\d,]+)', result['funding_amount']).group(1).replace(',', ''))
                    goal_num = int(re.search(r'([\d,]+)', result['goal_amount']).group(1).replace(',', ''))
                    if goal_num > 0:
                        result['percent_funded'] = int((funding_num / goal_num) * 100)
                        print(f"       達成率: {result['percent_funded']}%")
                except:
                    pass

            # 残り日数
            days_match = re.search(r'(\d+)\s*(?:days?\s*(?:to go|left)|日\s*で締切)', page_text, re.I)
            if days_match:
                result['days_left'] = f"{days_match.group(1)}日"
                print(f"       残り: {result['days_left']}")

            # リワード/価格情報を取得
            rewards = self._extract_rewards_from_page(soup, page_text)
            if rewards:
                result['rewards'] = rewards
                print(f"       リワード: {len(rewards)}件取得")

            # データソースを記録
            if result['funding_amount'] or result['backers_count']:
                result['data_source'] = f'Kickstarter ({proxy_label})'
                result['source_url'] = base_url

        except PlaywrightTimeout:
            print(f"       ⚠️ タイムアウト")
        except Exception as e:
            print(f"       ⚠️ Playwright取得エラー: {type(e).__name__}: {e}")
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass

        return result

    def _extract_rewards_from_page(self, soup, page_text):
        """
        Kickstarterページからリワード/価格情報を抽出（ベストエフォート方式）

        Kickstarterのページ構造は頻繁に変更されるため、
        取得できない場合は空リストを返し、レポートではKickstarterページへの
        参照を促すようにする。

        Args:
            soup: BeautifulSoupオブジェクト
            page_text: ページのテキスト

        Returns:
            list: リワード情報のリスト（取得できない場合は空リスト）
        """
        # 注意: Kickstarterのリワード構造は複雑で頻繁に変更されるため、
        # 価格情報の自動抽出は信頼性が低い。
        # 将来的にKickstarter APIが利用可能になった場合はそちらを使用すべき。
        #
        # 現時点では価格情報の抽出を行わず、レポート生成時に
        # 「価格詳細はKickstarterページでご確認ください」と記載する方針とする。

        return []  # 価格抽出は行わない（汎用性を優先）

    def _fetch_kickstarter_info_kicktraq(self, kickstarter_url):
        """
        Kicktraqから製品情報を取得（フォールバック）
        Kicktraqはサードパーティのトラッキングサイトで、Kickstarterよりアクセスしやすい
        """
        base_url = self._normalize_kickstarter_url(kickstarter_url)

        # KickstarterのURLからKicktraqのURLを生成
        # https://www.kickstarter.com/projects/xxx/yyy -> https://www.kicktraq.com/projects/xxx/yyy/
        kicktraq_url = base_url.replace('www.kickstarter.com', 'www.kicktraq.com')
        if not kicktraq_url.endswith('/'):
            kicktraq_url += '/'

        print(f"     Kicktraqからデータ取得中...")
        print(f"       URL: {kicktraq_url}")

        result = {
            "title": "",
            "description": "",
            "category": "",
            "funding_amount": "",
            "goal_amount": "",
            "percent_funded": 0,
            "backers_count": 0,
            "rewards": [],
            "days_left": "",
            "creator_name": "",
            "data_source": "",
            "source_url": ""
        }

        try:
            response = self.session.get(kicktraq_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # Kicktraqでまだインデックスされていない場合をチェック
            if 'We should have something for you soon' in page_text or 'magical ninja-gnomes' in page_text:
                print(f"       ⚠️ Kicktraq: この製品はまだインデックスされていません")
                return result

            # タイトル（Kicktraqのページ構造に合わせて取得）
            # 重要: "KickTraq"というサイト名ではなく、製品タイトルを取得する
            title_elem = soup.select_one('h1.project-title')
            if title_elem:
                title = title_elem.get_text(strip=True)
                # "KickTraq"を含む場合は無効
                if 'kicktraq' not in title.lower():
                    result['title'] = title
                    print(f"       タイトル: {result['title'][:50]}...")

            # タイトルが取得できなかった場合、metaタグから取得を試みる
            if not result['title']:
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    title = og_title.get('content', '')
                    # "KickTraq"や"Kicktraq"を含まない場合のみ使用
                    if title and 'kicktraq' not in title.lower():
                        result['title'] = title
                        print(f"       タイトル(meta): {result['title'][:50]}...")

            # 調達額を探す（Kicktraqのフォーマット）
            # "pledged of $X goal" パターン
            pledged_match = re.search(r'\$([\d,]+)\s*pledged', page_text, re.I)
            if pledged_match:
                amount = pledged_match.group(1)
                result['funding_amount'] = f"${amount}"
                print(f"       調達額: {result['funding_amount']}")

            # 目標額
            goal_match = re.search(r'of\s*\$([\d,]+)\s*goal', page_text, re.I)
            if goal_match:
                result['goal_amount'] = f"${goal_match.group(1)}"
                print(f"       目標額: {result['goal_amount']}")

            # バッカー数
            backers_match = re.search(r'([\d,]+)\s*backers?', page_text, re.I)
            if backers_match:
                result['backers_count'] = int(backers_match.group(1).replace(',', ''))
                print(f"       バッカー数: {result['backers_count']}人")

            # 達成率
            if result['funding_amount'] and result['goal_amount']:
                try:
                    funding_num = int(re.search(r'([\d,]+)', result['funding_amount']).group(1).replace(',', ''))
                    goal_num = int(re.search(r'([\d,]+)', result['goal_amount']).group(1).replace(',', ''))
                    if goal_num > 0:
                        result['percent_funded'] = int((funding_num / goal_num) * 100)
                        print(f"       達成率: {result['percent_funded']}%")
                except:
                    pass

            # データソースを記録
            if result['funding_amount'] or result['backers_count']:
                result['data_source'] = 'Kicktraq'
                result['source_url'] = kicktraq_url

        except Exception as e:
            print(f"       ⚠️ Kicktraq取得エラー: {type(e).__name__}: {e}")

        return result

    def reset_browser(self):
        """
        ブラウザセッションをリセット（Kickstarterのボット検出回避用）
        各商品処理後に呼び出すことで、新しいセッションで次の商品を取得できる
        """
        print("     🔄 ブラウザセッションをリセット中...")
        self._close_browser()
        print("     ✓ ブラウザセッションをリセットしました")

    def _fetch_kickstarter_info(self, kickstarter_url):
        """
        Kickstarterページから製品情報を取得

        優先順位：
        1. 直接接続（Playwright）- 無料
        2. Bright Dataプロキシ - 有料
        3. 取得失敗を正直に報告
        """
        # 1. まず直接接続で試す（無料）
        result = self._fetch_kickstarter_info_playwright(kickstarter_url, use_proxy=False)

        # データが取得できたかチェック
        if result.get('funding_amount') or result.get('backers_count'):
            return result

        # 2. Bright Dataプロキシは一時的に無効化（API制限のため）
        # bright_data_username = os.getenv('BRIGHT_DATA_USERNAME')
        # bright_data_password = os.getenv('BRIGHT_DATA_PASSWORD')
        #
        # if bright_data_username and bright_data_password:
        #     print("     → Bright Dataプロキシで再試行...")
        #     result = self._fetch_kickstarter_info_playwright(kickstarter_url, use_proxy=True)
        #
        #     if result.get('funding_amount') or result.get('backers_count'):
        #         return result

        # 3. 全て失敗した場合は正直に報告
        print("     ⚠️ Kickstarterデータの取得に失敗しました")
        result['data_source'] = 'データ取得失敗'
        result['source_url'] = self._normalize_kickstarter_url(kickstarter_url)

        return result

    def extract_product_keywords(self, kickstarter_url, product_name=''):
        """
        Kickstarter URLから製品カテゴリとキーワードを抽出
        """
        # Kickstarterから製品情報を取得
        ks_info = self._fetch_kickstarter_info(kickstarter_url)

        if not self.api_available:
            return {"keywords": [product_name], "category": "製品", "filter_keywords": [], "ks_info": ks_info}

        try:
            # 取得した情報をサマリーにする
            funding_info = ""
            if ks_info.get('funding_amount'):
                funding_info = f"調達額: {ks_info['funding_amount']}"
                if ks_info.get('goal_amount'):
                    funding_info += f" / 目標: {ks_info['goal_amount']}"
            if ks_info.get('backers_count'):
                funding_info += f"\nバッカー数: {ks_info['backers_count']}人"

            prompt = f"""以下のKickstarter製品について、日本のクラウドファンディング（Makuake、CAMPFIRE）で
類似製品を検索するための情報を提供してください。

【Kickstarter製品情報】
URL: {kickstarter_url}
製品名/メーカー: {product_name}
タイトル: {ks_info.get('title', '不明')}
{funding_info}
説明: {ks_info.get('description', '不明')[:300]}

【回答形式（JSON）】:
{{
    "keywords": ["検索キーワード1", "検索キーワード2"],
    "category": "製品カテゴリ（日本語）",
    "filter_keywords": ["フィルタ用キーワード1", "フィルタ用キーワード2"]
}}

【重要なルール】:
1. keywords: 日本語の検索キーワード（2つ）
   - 一般的で汎用的なキーワードを使用すること
   - 例: 「テンカラ竿」より「テンカラ」「フライロッド」のような一般的な単語
   - 例: 「AI夜間カメラ」より「ナイトビジョン」「暗視カメラ」のような検索されやすい単語
2. category: 製品の一般的なカテゴリ名（日本語、1-3単語）
   - 例: 「釣り具」「カメラ」「アウトドア用品」「ガジェット」など
3. filter_keywords: 類似製品を判別するためのキーワード（2つまで）
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "JSON形式で回答してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result['ks_info'] = ks_info
                return result
            return {"keywords": [product_name], "category": "製品", "filter_keywords": [], "ks_info": ks_info}

        except Exception as e:
            print(f"  ⚠️ キーワード抽出エラー: {e}")
            return {"keywords": [product_name], "category": "製品", "filter_keywords": [], "ks_info": ks_info}

    def _search_makuake_playwright(self, keyword):
        """PlaywrightでMakuake検索"""
        import urllib.parse
        search_url = f"https://www.makuake.com/discover/projects/?keyword={urllib.parse.quote(keyword)}"
        print(f"     Makuake検索（Playwright）: {keyword}")
        print(f"       URL: {search_url}")

        projects = []
        browser = self._get_browser()
        if not browser:
            return {"found": False, "projects": [], "search_note": "ブラウザ初期化失敗"}

        page = None
        try:
            page = self._context.new_page()
            # 最適化: タイムアウトと待機時間を短縮
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # プロジェクトリンクを検索
            project_links = soup.select('ul li a[href*="/project/"]')
            if not project_links:
                project_links = soup.select('a[href*="/project/"]')

            seen_urls = set()
            print(f"       → {len(project_links)}件のリンクを発見")

            for link in project_links[:20]:
                try:
                    href = link.get('href', '')
                    if not href or '/project/' not in href:
                        continue

                    if href.startswith('/'):
                        project_url = f"https://www.makuake.com{href}"
                    elif not href.startswith('http'):
                        continue
                    else:
                        project_url = href

                    base_url = project_url.split('?')[0].rstrip('/')
                    if base_url in seen_urls:
                        continue
                    seen_urls.add(base_url)

                    full_text = link.get_text(strip=True)
                    if not full_text or len(full_text) < 10:
                        continue

                    # 金額を抽出
                    funding = ""
                    amount_match = re.search(r'[￥¥]([0-9]{1,3}(?:,[0-9]{3})*)', full_text)
                    if amount_match:
                        funding = amount_match.group(1) + "円"

                    # 達成率を抽出
                    percent = 0
                    percent_match = re.search(r'(\d+)%', full_text)
                    if percent_match:
                        percent = int(percent_match.group(1))

                    # タイトルを抽出
                    if amount_match:
                        title = full_text[:amount_match.start()].strip()
                    else:
                        title = full_text[:80]

                    if not title or len(title) < 5:
                        continue

                    print(f"         ✓ 発見: {title[:40]}...")
                    projects.append({
                        "name": title[:100],
                        "url": base_url,
                        "funding_amount": funding if funding else "募集中",
                        "backers": 0,
                        "percent": percent,
                        "platform": "Makuake",
                        "data_verified": True  # 実際に取得したデータ
                    })

                    if len(projects) >= 5:
                        break

                except Exception:
                    continue

        except PlaywrightTimeout:
            print(f"       ⚠️ タイムアウト")
        except Exception as e:
            print(f"     ⚠️ Makuake検索エラー: {type(e).__name__}: {e}")
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass

        return {
            "found": len(projects) > 0,
            "projects": projects,
            "search_note": f"Makuakeで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした",
            "search_attempted": True
        }

    def search_makuake(self, keyword):
        """Makuakeで類似製品を検索"""
        return self._search_makuake_playwright(keyword)

    def _search_campfire_playwright(self, keyword, use_proxy=False):
        """PlaywrightでCAMPFIRE検索"""
        import urllib.parse
        search_url = f"https://camp-fire.jp/projects/search?word={urllib.parse.quote(keyword)}"
        proxy_label = "Bright Dataプロキシ" if use_proxy else "直接接続"
        print(f"     CAMPFIRE検索（Playwright - {proxy_label}）: {keyword}")
        print(f"       URL: {search_url}")

        projects = []
        browser = self._get_browser(use_proxy=use_proxy)
        if not browser:
            return {"found": False, "projects": [], "search_note": "ブラウザ初期化失敗"}

        context = self._get_context(use_proxy=use_proxy)
        if not context:
            return {"found": False, "projects": [], "search_note": "コンテキスト初期化失敗"}

        page = None
        try:
            page = context.new_page()
            # 最適化: タイムアウトと待機時間を短縮
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # 海外IPブロックのチェック
            if 'Welcome' in html and 'International' in html:
                print(f"       ⚠️ CAMPFIRE: 海外IPからのアクセス制限")
                if page:
                    try:
                        page.close()
                    except:
                        pass
                # プロキシ未使用時はプロキシで再試行
                if not use_proxy:
                    bright_data_username = os.getenv('BRIGHT_DATA_USERNAME')
                    bright_data_password = os.getenv('BRIGHT_DATA_PASSWORD')
                    if bright_data_username and bright_data_password:
                        print(f"       → Bright Dataプロキシで再試行...")
                        return self._search_campfire_playwright(keyword, use_proxy=True)
                return {
                    "found": False,
                    "projects": [],
                    "search_note": "海外IPからのアクセス制限",
                    "geo_restricted": True
                }

            # プロジェクトリンクを検索
            project_links = soup.select('a[href*="/projects/"][href*="/view"]')
            seen_urls = set()
            print(f"       → {len(project_links)}件のリンクを発見")

            for link in project_links[:15]:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue

                    if href.startswith('/'):
                        project_url = f"https://camp-fire.jp{href}"
                    elif not href.startswith('http'):
                        continue
                    else:
                        project_url = href

                    base_url = project_url.split('?')[0].rstrip('/')
                    if base_url in seen_urls:
                        continue
                    seen_urls.add(base_url)

                    full_text = link.get_text(strip=True)
                    if not full_text or len(full_text) < 10:
                        continue

                    # 無効なタイトルを除外
                    invalid_titles = ["プロジェクト公開の通知", "通知を受け取る", "お気に入り", "ログイン", "Welcome"]
                    if any(invalid in full_text for invalid in invalid_titles):
                        continue

                    # 金額を抽出
                    funding = ""
                    amount_match = re.search(r'([\d,]+)円', full_text)
                    if amount_match:
                        funding = amount_match.group(1) + "円"

                    # 達成率を抽出
                    percent = 0
                    percent_match = re.search(r'(\d+)%', full_text)
                    if percent_match:
                        percent = int(percent_match.group(1))

                    # タイトルを抽出（不要なテキストを除去）
                    title = full_text

                    # 先頭の募集終了/FINISH/SUCCESS等を除去
                    prefixes_to_remove = ['募集終了FINISH募集終了', '募集終了SUCCESS募集終了',
                                         '募集終了FINISH', '募集終了SUCCESS', '募集終了',
                                         'FINISH', 'SUCCESS']
                    for prefix in prefixes_to_remove:
                        if title.startswith(prefix):
                            title = title[len(prefix):].strip()

                    # 末尾のステータス/金額情報を除去（正規表現で）
                    # パターン: FINISH現在, SUCCESS現在, FUNDED現在, 数字円, 数字人
                    title = re.sub(r'(FINISH|SUCCESS|FUNDED|募集終了)現在[\d,]*.*$', '', title).strip()
                    title = re.sub(r'\d{1,3}(,\d{3})*円.*$', '', title).strip()
                    title = re.sub(r'\d+人.*$', '', title).strip()
                    title = re.sub(r'達成率\d+%.*$', '', title).strip()

                    # それでもタイトルが長すぎる場合
                    if len(title) > 80:
                        title = title[:80]

                    if not title or len(title) < 5:
                        continue

                    print(f"         ✓ 発見: {title[:40]}...")
                    projects.append({
                        "name": title[:100],
                        "url": base_url,
                        "funding_amount": funding if funding else "非公開",
                        "backers": 0,
                        "percent": percent,
                        "platform": "CAMPFIRE",
                        "data_verified": True
                    })

                    if len(projects) >= 5:
                        break

                except Exception:
                    continue

        except PlaywrightTimeout:
            print(f"       ⚠️ タイムアウト")
        except Exception as e:
            print(f"     ⚠️ CAMPFIRE検索エラー: {type(e).__name__}: {e}")
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass

        return {
            "found": len(projects) > 0,
            "projects": projects,
            "search_note": f"CAMPFIREで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした",
            "search_attempted": True
        }

    def search_campfire(self, keyword):
        """CAMPFIREで類似製品を検索"""
        return self._search_campfire_playwright(keyword)

    def search_similar_products(self, kickstarter_url, product_name=''):
        """
        類似製品を総合検索

        検索戦略：
        - GPT生成キーワード（日本語）で検索
        - 具体的なキーワードのみ使用（汎用的なカテゴリ名は使用しない）

        重要：架空のデータは絶対に生成しない
        """
        print(f"  🔍 類似製品を検索中...")

        # 1. 製品カテゴリとキーワードを抽出（Kickstarter情報も取得）
        keyword_info = self.extract_product_keywords(kickstarter_url, product_name)
        keywords = keyword_info.get('keywords', [product_name])
        category = keyword_info.get('category', '製品')
        ks_info = keyword_info.get('ks_info', {})

        print(f"     カテゴリ: {category}")
        print(f"     キーワード: {', '.join(keywords)}")

        all_makuake_projects = []
        all_campfire_projects = []

        # 検索キーワードリストを構築（重複排除、GPT生成キーワードのみ使用）
        search_keywords = []
        for kw in keywords[:2]:
            if kw and kw not in search_keywords:
                search_keywords.append(kw)

        # 2. 各キーワードでMakuakeとCAMPFIREを検索
        for keyword in search_keywords[:2]:  # 最大2キーワード
            # Makuake検索
            makuake_results = self.search_makuake(keyword)
            if makuake_results.get('found'):
                for p in makuake_results['projects']:
                    if not any(existing['url'] == p['url'] for existing in all_makuake_projects):
                        all_makuake_projects.append(p)

            # CAMPFIRE検索
            campfire_results = self.search_campfire(keyword)
            if campfire_results.get('found'):
                for p in campfire_results['projects']:
                    if not any(existing['url'] == p['url'] for existing in all_campfire_projects):
                        all_campfire_projects.append(p)

        all_makuake_projects = all_makuake_projects[:5]
        all_campfire_projects = all_campfire_projects[:5]
        has_results = len(all_makuake_projects) > 0 or len(all_campfire_projects) > 0

        summary_parts = []
        if all_makuake_projects:
            summary_parts.append(f"Makuake {len(all_makuake_projects)}件")
        if all_campfire_projects:
            summary_parts.append(f"CAMPFIRE {len(all_campfire_projects)}件")

        if summary_parts:
            summary = f"類似製品を発見: {', '.join(summary_parts)}"
        else:
            summary = "日本のクラウドファンディングで類似製品は見つかりませんでした"

        print(f"  ✓ 検索完了: {summary}")

        return {
            "category": category,
            "keywords": keywords,
            "kickstarter_info": ks_info,
            "makuake": {
                "found": len(all_makuake_projects) > 0,
                "projects": all_makuake_projects
            },
            "campfire": {
                "found": len(all_campfire_projects) > 0,
                "projects": all_campfire_projects
            },
            "has_results": has_results,
            "summary": summary
        }

    def format_for_prompt(self, search_results):
        """
        検索結果をプロンプト用にフォーマット

        重要：取得できたデータのみを記載。架空のデータは絶対に含めない。
        """
        lines = []

        # === Kickstarter製品の詳細情報 ===
        ks_info = search_results.get('kickstarter_info', {})
        lines.append("=" * 50)
        lines.append("【分析対象のKickstarter製品】")
        lines.append("=" * 50)

        if ks_info.get('data_source') == 'データ取得失敗':
            lines.append("")
            lines.append("⚠️ Kickstarterからのデータ取得に失敗しました。")
            lines.append("以下の情報は利用できません：")
            lines.append("- 資金調達額")
            lines.append("- バッカー数")
            lines.append("- 目標金額")
            lines.append("- リワード/価格情報")
            lines.append("")
            lines.append("レポートではこれらのデータに言及しないでください。")
            lines.append("価格については「Kickstarterページでご確認ください」と記載してください。")
            lines.append(f"製品URL: {ks_info.get('source_url', 'N/A')}")
        else:
            if ks_info.get('title'):
                lines.append(f"製品名: {ks_info['title']}")

            if ks_info.get('funding_amount'):
                funding_line = f"調達額: {ks_info['funding_amount']}"
                if ks_info.get('goal_amount'):
                    funding_line += f" / 目標: {ks_info['goal_amount']}"
                if ks_info.get('percent_funded'):
                    funding_line += f" ({ks_info['percent_funded']}%達成)"
                lines.append(funding_line)

            if ks_info.get('backers_count'):
                lines.append(f"バッカー数: {ks_info['backers_count']:,}人")

            if ks_info.get('days_left'):
                lines.append(f"キャンペーン状況: {ks_info['days_left']}")

            if ks_info.get('data_source'):
                lines.append(f"データソース: {ks_info['data_source']}")

            # リワード/価格情報を追加
            rewards = ks_info.get('rewards', [])
            if rewards:
                lines.append("")
                lines.append("■ 利用可能なリワード/価格:")
                for i, reward in enumerate(rewards, 1):
                    price = reward.get('price', '')
                    title = reward.get('title', '')
                    is_early = reward.get('is_early_bird', False)
                    is_limited = reward.get('is_limited', False)
                    backers = reward.get('backers', 0)
                    available = reward.get('available', '')

                    reward_line = f"  {i}. {price}"
                    if is_early:
                        reward_line += " [Early Bird]"
                    if is_limited:
                        reward_line += " [限定]"
                    if title:
                        reward_line += f" - {title}"
                    if backers:
                        reward_line += f" ({backers}人が支援)"
                    if available:
                        reward_line += f" {available}"
                    lines.append(reward_line)
            else:
                lines.append("")
                lines.append("■ リワード/価格情報: 取得できませんでした")
                lines.append("  → 価格については「詳細はKickstarterページでご確認ください」と記載してください")

            if ks_info.get('description'):
                lines.append(f"\n製品説明:\n{ks_info['description'][:400]}")

        lines.append("")

        # === 日本市場の類似製品情報 ===
        lines.append("=" * 50)
        lines.append("【日本クラウドファンディング市場調査結果】")
        lines.append("=" * 50)

        if not search_results.get('has_results', False):
            lines.append("")
            lines.append("調査の結果、MakuakeおよびCAMPFIREで類似製品は見つかりませんでした。")
            lines.append("")
            lines.append("これは以下の可能性を示唆します：")
            lines.append("・日本市場において未開拓のカテゴリである可能性")
            lines.append("・先行者利益を得られるチャンス")
            lines.append("")
            lines.append("【重要】架空の製品名やURLを記載しないでください。")
            lines.append("「類似製品が見つからなかった」という事実をそのまま伝えてください。")
        else:
            lines.append(f"製品カテゴリ: {search_results.get('category', '製品')}")
            lines.append("※以下は実際にMakuake/CAMPFIREから取得したデータです。")
            lines.append("")

            # Makuake結果
            makuake = search_results.get('makuake', {})
            if makuake.get('found', False) and makuake.get('projects'):
                lines.append(f"■ Makuakeの類似製品（{len(makuake['projects'])}件）:")
                for i, p in enumerate(makuake['projects'], 1):
                    lines.append(f"  【製品{i}】")
                    lines.append(f"    製品名: {p.get('name', '不明')}")
                    lines.append(f"    URL: {p.get('url', '')}")
                    lines.append(f"    資金調達額: {p.get('funding_amount', '非公開')}")
                    if p.get('percent'):
                        lines.append(f"    達成率: {p.get('percent')}%")
                    lines.append("")

            # CAMPFIRE結果
            campfire = search_results.get('campfire', {})
            if campfire.get('found', False) and campfire.get('projects'):
                lines.append(f"■ CAMPFIREの類似製品（{len(campfire['projects'])}件）:")
                for i, p in enumerate(campfire['projects'], 1):
                    lines.append(f"  【製品{i}】")
                    lines.append(f"    製品名: {p.get('name', '不明')}")
                    lines.append(f"    URL: {p.get('url', '')}")
                    lines.append(f"    資金調達額: {p.get('funding_amount', '非公開')}")
                    if p.get('percent'):
                        lines.append(f"    達成率: {p.get('percent')}%")
                    lines.append("")

        # === 厳格なルール ===
        lines.append("")
        lines.append("=" * 50)
        lines.append("【レポート作成の絶対ルール】")
        lines.append("=" * 50)
        lines.append("")
        lines.append("■ 絶対に守ること：")
        lines.append("1. 上記に記載されたデータのみを使用すること")
        lines.append("2. 架空の製品名、URL、金額を絶対に記載しない")
        lines.append("3. データが取得できなかった項目には言及しない")
        lines.append("4. 「Kickstarterページをご覧ください」のような曖昧な表現は禁止")
        lines.append("5. 上記のMakuake/CAMPFIRE製品のURLは必ずそのまま引用すること")
        lines.append("")
        lines.append("■ データがない場合：")
        lines.append("- その項目についてはレポートで触れない")
        lines.append("- 「情報が取得できませんでした」とは書かない")
        lines.append("- 代わりに、取得できた情報だけで分析を行う")
        lines.append("=" * 50)

        return "\n".join(lines)


def test_search():
    """テスト用関数"""
    from dotenv import load_dotenv
    load_dotenv()

    searcher = MarketSearcher()

    print("=" * 60)
    print("Kickstarter情報取得テスト")
    print("=" * 60)

    # テスト: Tenkara Rod Co.
    test_url = "https://www.kickstarter.com/projects/tenkara/the-kita-made-in-japan-tenkara-fly-fishing-rod"
    results = searcher.search_similar_products(test_url, "Tenkara Rod Co.")

    print("\n" + "=" * 60)
    print("検索結果サマリー")
    print("=" * 60)

    ks_info = results.get('kickstarter_info', {})
    print(f"データソース: {ks_info.get('data_source', 'N/A')}")
    print(f"調達額: {ks_info.get('funding_amount', 'N/A')}")
    print(f"バッカー数: {ks_info.get('backers_count', 'N/A')}")
    print(f"目標額: {ks_info.get('goal_amount', 'N/A')}")

    print("\n" + "=" * 60)
    print("Makuake結果")
    print("=" * 60)
    for p in results.get('makuake', {}).get('projects', []):
        print(f"  - {p.get('name')}")
        print(f"    URL: {p.get('url')}")
        print(f"    資金: {p.get('funding_amount')}")

    print("\n" + "=" * 60)
    print("プロンプト用フォーマット")
    print("=" * 60)
    print(searcher.format_for_prompt(results))

    # クリーンアップ
    searcher._close_browser()


if __name__ == '__main__':
    test_search()
