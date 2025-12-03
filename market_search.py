#!/usr/bin/env python3
"""
市場調査用ウェブ検索モジュール
Makuake/CAMPFIREで類似製品を検索し、実在するデータを取得
Seleniumによるブラウザ自動化でJavaScriptレンダリングに対応
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# Selenium関連
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
    print("  ✓ Seleniumモジュールを読み込みました")
except ImportError as e:
    SELENIUM_AVAILABLE = False
    print(f"  ⚠️ Seleniumモジュールが利用できません: {e}")


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

        # HTTPセッション設定（日本からのアクセスとして認識させる）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })

        # Seleniumドライバー（遅延初期化）
        self._driver = None

    def _get_driver(self, force_new=False):
        """Seleniumドライバーを取得（遅延初期化）"""
        if not SELENIUM_AVAILABLE:
            print("     ⚠️ Seleniumが利用できないためスキップ")
            return None

        # 既存のドライバーがある場合は閉じる（force_new時）
        if force_new and self._driver:
            self._close_driver()

        if self._driver is None:
            try:
                print("     Seleniumブラウザを初期化中...")
                options = Options()
                options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1280,720')
                options.add_argument('--lang=ja-JP')
                options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                # GitHub Actions用のメモリ節約・安定性オプション
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-software-rasterizer')
                options.add_argument('--disable-background-networking')
                options.add_argument('--disable-default-apps')
                options.add_argument('--disable-sync')
                options.add_argument('--disable-translate')
                options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
                options.add_argument('--force-color-profile=srgb')
                options.add_argument('--metrics-recording-only')
                options.add_argument('--mute-audio')
                options.add_argument('--no-first-run')
                options.add_argument('--safebrowsing-disable-auto-update')
                # 追加の安定性オプション（クラッシュ防止）
                options.add_argument('--disable-browser-side-navigation')
                options.add_argument('--disable-infobars')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--disable-notifications')
                options.add_argument('--disable-hang-monitor')
                options.add_argument('--disable-prompt-on-repost')
                options.add_argument('--disable-client-side-phishing-detection')
                options.add_argument('--disable-component-update')
                options.add_argument('--disable-ipc-flooding-protection')
                options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
                options.add_argument('--remote-debugging-port=0')
                # メモリ制限
                options.add_argument('--js-flags=--max-old-space-size=256')
                options.add_argument('--renderer-process-limit=1')
                options.add_argument('--memory-pressure-off')
                # 画像無効化でメモリ削減
                options.add_argument('--blink-settings=imagesEnabled=false')
                # ページロードタイムアウト設定
                options.page_load_strategy = 'eager'

                print("     ChromeDriverをセットアップ中...")
                try:
                    service = Service(ChromeDriverManager().install())
                    self._driver = webdriver.Chrome(service=service, options=options)
                    self._driver.set_page_load_timeout(30)
                    self._driver.implicitly_wait(5)
                    print("     ✓ Seleniumブラウザを初期化しました")
                except Exception as e1:
                    print(f"     webdriver-manager失敗: {e1}")
                    try:
                        self._driver = webdriver.Chrome(options=options)
                        self._driver.set_page_load_timeout(30)
                        self._driver.implicitly_wait(5)
                        print("     ✓ Seleniumブラウザを初期化しました（システム）")
                    except Exception as e2:
                        print(f"     システムchrome失敗: {e2}")
                        raise e2

            except Exception as e:
                print(f"     ⚠️ Selenium初期化エラー: {type(e).__name__}: {e}")
                self._driver = None

        return self._driver

    def _close_driver(self):
        """Seleniumドライバーを終了"""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def __del__(self):
        """デストラクタ"""
        self._close_driver()

    def _fetch_kickstarter_info(self, kickstarter_url):
        """
        Kickstarterページから製品情報を取得（Selenium使用で詳細情報も取得）

        Args:
            kickstarter_url (str): Kickstarter URL

        Returns:
            dict: 製品情報（title, description, category, funding, goal, percent, backers, rewards）
        """
        # ベースのプロジェクトURLを取得（/creator, /description, /comments 等を除去）
        base_url = kickstarter_url.split('?')[0]  # クエリパラメータを除去
        # 末尾のパスを除去してベースURLを取得
        for suffix in ['/creator', '/description', '/comments', '/updates', '/community', '/faqs']:
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)]
                break
        # /description ページにアクセス（より詳細な情報が取得できる）
        project_url = base_url + '/description'
        print(f"     Kickstarter製品情報を取得中...")
        print(f"       URL: {project_url}")

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
            "creator_name": ""
        }

        # まずSeleniumで詳細情報を取得
        driver = self._get_driver()
        if driver:
            try:
                print(f"       Seleniumで詳細情報を取得中...")
                driver.get(project_url)
                time.sleep(3)  # ページ読み込み待機

                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # JSON-LDデータを探す（構造化データ）
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            if data.get('@type') == 'Product' or data.get('@type') == 'CreativeWork':
                                result['title'] = data.get('name', result['title'])
                                result['description'] = data.get('description', result['description'])[:500]
                    except:
                        pass

                # メタタグからデータ取得
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    result['title'] = og_title.get('content', '').replace(' — Kickstarter', '').strip()

                og_desc = soup.find('meta', property='og:description')
                if og_desc:
                    result['description'] = og_desc.get('content', '')[:500]

                # 資金調達額（様々なセレクタを試す）
                # アクティブ: span.ksr-green-500, 終了: span.soft-black
                funding_selectors = [
                    'span.ksr-green-500',
                    'span.soft-black',
                    'span.ksr-green-700 span',
                ]
                for selector in funding_selectors:
                    funding_elem = soup.select_one(selector)
                    if funding_elem:
                        funding_text = funding_elem.get_text(strip=True)
                        # US$ 252,364 または $1,234,567 の形式を抽出
                        amount_match = re.search(r'(?:US\$|\$|€|£|¥)\s*([\d,]+)', funding_text)
                        if amount_match:
                            result['funding_amount'] = funding_text.strip()
                            print(f"       調達額: {result['funding_amount']}")
                            break

                # 目標金額 - 「の総プレッジ額 (US$ 5,000 中)」から抽出
                goal_elem = soup.select_one('span.money')
                if goal_elem:
                    goal_text = goal_elem.get_text(strip=True)
                    amount_match = re.search(r'(?:US\$|\$|€|£|¥)\s*([\d,]+)', goal_text)
                    if amount_match:
                        result['goal_amount'] = goal_text.strip()
                        print(f"       目標額: {result['goal_amount']}")

                # 達成率を計算（調達額 / 目標額）
                if result['funding_amount'] and result['goal_amount']:
                    try:
                        funding_num = int(re.search(r'([\d,]+)', result['funding_amount']).group(1).replace(',', ''))
                        goal_num = int(re.search(r'([\d,]+)', result['goal_amount']).group(1).replace(',', ''))
                        if goal_num > 0:
                            result['percent_funded'] = int((funding_num / goal_num) * 100)
                            print(f"       達成率: {result['percent_funded']}%")
                    except:
                        pass

                # バッカー数 - 「人のバッカー」の前にある数字を探す
                page_text = soup.get_text()
                backers_match = re.search(r'([\d,]+)\s*(?:人のバッカー|backers?)', page_text, re.I)
                if backers_match:
                    result['backers_count'] = int(backers_match.group(1).replace(',', ''))
                    print(f"       バッカー数: {result['backers_count']}人")

                # カテゴリ
                category_selectors = [
                    'a[href*="/discover/categories/"]',
                    'span.category-name',
                    'a.category-name'
                ]
                for selector in category_selectors:
                    category_elem = soup.select_one(selector)
                    if category_elem:
                        result['category'] = category_elem.get_text(strip=True)
                        print(f"       カテゴリ: {result['category']}")
                        break

                # リワード価格帯を取得
                reward_selectors = [
                    'span.pledge__amount',
                    'div[class*="reward"] span.money',
                    'h3.pledge__amount'
                ]
                rewards = []
                for selector in reward_selectors:
                    reward_elems = soup.select(selector)
                    for elem in reward_elems[:5]:  # 最大5つ
                        reward_text = elem.get_text(strip=True)
                        if reward_text and '$' in reward_text or '¥' in reward_text:
                            rewards.append(reward_text)
                    if rewards:
                        break
                result['rewards'] = rewards
                if rewards:
                    print(f"       リワード価格帯: {', '.join(rewards[:3])}")

                # 残り日数 - 「日 で締切」の前にある数字を探す
                days_match = re.search(r'(\d+)\s*(?:日\s*で締切|days?\s*(?:to go|left))', page_text, re.I)
                if days_match:
                    result['days_left'] = f"{days_match.group(1)}日"
                    print(f"       残り: {result['days_left']}")

                # クリエイター名
                creator_selectors = [
                    'a[data-test-id="creator-name"]',
                    'span[class*="creator"]',
                    'a[href*="/profile/"]'
                ]
                for selector in creator_selectors:
                    creator_elem = soup.select_one(selector)
                    if creator_elem:
                        result['creator_name'] = creator_elem.get_text(strip=True)
                        break

                print(f"       タイトル: {result['title'][:50]}..." if result['title'] else "       タイトル: 取得中...")

            except Exception as e:
                print(f"       Selenium取得エラー: {e}")

        # Seleniumで取得できなかった場合、requestsでフォールバック
        if not result['title']:
            try:
                response = self.session.get(project_url, timeout=15)
                response.raise_for_status()
                response.encoding = 'utf-8'

                soup = BeautifulSoup(response.text, 'html.parser')

                # タイトル取得
                title_elem = soup.select_one('meta[property="og:title"]')
                if title_elem:
                    result['title'] = title_elem.get('content', '').replace(' — Kickstarter', '').strip()

                # 説明取得
                desc_elem = soup.select_one('meta[property="og:description"], meta[name="description"]')
                if desc_elem:
                    result['description'] = desc_elem.get('content', '')[:500]

                print(f"       タイトル（フォールバック）: {result['title'][:50]}..." if result['title'] else "       タイトル: 取得失敗")

            except Exception as e:
                print(f"     ⚠️ Kickstarter情報取得エラー: {e}")

        return result

    def extract_product_keywords(self, kickstarter_url, product_name=''):
        """
        Kickstarter URLから製品カテゴリとキーワードを抽出

        Args:
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            dict: キーワード情報（keywords, category, filter_keywords, ks_info）
        """
        # Kickstarterから製品情報を取得（常に実行）
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
                if ks_info.get('percent_funded'):
                    funding_info += f" ({ks_info['percent_funded']}%達成)"
            if ks_info.get('backers_count'):
                funding_info += f"\nバッカー数: {ks_info['backers_count']}人"
            if ks_info.get('rewards'):
                funding_info += f"\nリワード価格帯: {', '.join(ks_info['rewards'][:3])}"

            prompt = f"""以下のKickstarter製品について、日本のクラウドファンディング（MakuakeやCAMPFIRE）で
類似製品を検索するための情報を提供してください。

【Kickstarter製品情報】
URL: {kickstarter_url}
製品名/メーカー: {product_name}
タイトル: {ks_info.get('title', '不明')}
カテゴリ: {ks_info.get('category', '不明')}
{funding_info}
説明: {ks_info.get('description', '不明')[:300]}

【回答形式（JSON）】:
{{
    "keywords": ["検索キーワード1", "検索キーワード2"],
    "category": "製品カテゴリ（日本語）",
    "filter_keywords": ["フィルタ用キーワード1", "フィルタ用キーワード2", "フィルタ用キーワード3"]
}}

【重要】回答ルール:
1. keywords: 検索用キーワード（2つまで）
   - 日本のクラウドファンディングで使われる一般的な日本語名称
   - 具体的な製品カテゴリ（例: 「キーボード」「ブロック玩具」「焚き火台」）
   - 広すぎる語は避ける（✗「ガジェット」「電子機器」）

2. category: この製品の日本語カテゴリ名

3. filter_keywords: 検索結果から類似製品を判別するためのキーワード（3つまで）
   - この製品と同じカテゴリの製品に含まれる可能性が高い単語
   - 例: ブロック玩具なら ["ブロック", "積み木", "知育", "玩具", "おもちゃ"]
   - 例: キーボードなら ["キーボード", "タイピング", "入力デバイス"]
   - 例: 財布なら ["財布", "ウォレット", "革", "カード"]
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "JSON形式で回答してください。製品の特徴を正確に分析してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result['ks_info'] = ks_info  # Kickstarter情報を追加
                print(f"     フィルタキーワード: {result.get('filter_keywords', [])}")
                return result
            return {"keywords": [product_name], "category": "製品", "filter_keywords": [], "ks_info": ks_info}

        except Exception as e:
            print(f"  ⚠️ キーワード抽出エラー: {e}")
            return {"keywords": [product_name], "category": "製品", "filter_keywords": [], "ks_info": ks_info}

    def search_makuake(self, keyword):
        """
        Makuakeで類似製品を検索
        Seleniumを使用してJavaScriptレンダリング後のページから検索

        Args:
            keyword (str): 検索キーワード

        Returns:
            dict: 検索結果
        """
        # まずSeleniumで検索を試みる
        driver = self._get_driver()

        if driver:
            result = self._search_makuake_selenium(keyword, driver)
            if result.get('found') or result.get('search_attempted'):
                return result

        # Seleniumが使えない場合はRSSフォールバック
        return self._search_makuake_rss(keyword)

    def _search_makuake_selenium(self, keyword, driver, retry_count=0):
        """Seleniumを使ったMakuake検索"""
        try:
            import urllib.parse
            # 正しい検索URL: /discover/projects/?keyword=XXX
            search_url = f"https://www.makuake.com/discover/projects/?keyword={urllib.parse.quote(keyword)}"
            print(f"     Makuake検索（Selenium）: {keyword}")
            print(f"       URL: {search_url}")

            driver.get(search_url)
            time.sleep(3)  # ページ読み込み待機

            # プロジェクトカードを待機
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/project/"]'))
                )
            except Exception:
                print(f"       → プロジェクトが見つかりませんでした")
                return {"found": False, "projects": [], "search_note": "該当する製品が見つかりませんでした", "search_attempted": True}

            # ページソースを取得してBeautifulSoupで解析
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            projects = []

            # プロジェクトリンクを検索（liタグ内のaタグを対象）
            project_links = soup.select('ul li a[href*="/project/"]')
            if not project_links:
                # フォールバック: 通常のaタグ
                project_links = soup.select('a[href*="/project/"]')

            seen_urls = set()
            print(f"       → {len(project_links)}件のリンクを発見")

            for link in project_links[:20]:
                try:
                    href = link.get('href', '')
                    if not href or '/project/' not in href:
                        continue

                    # 完全なURLを構築
                    if href.startswith('/'):
                        project_url = f"https://www.makuake.com{href}"
                    elif not href.startswith('http'):
                        continue
                    else:
                        project_url = href

                    # 重複を除外
                    base_url = project_url.split('?')[0].rstrip('/')
                    if base_url in seen_urls:
                        continue
                    seen_urls.add(base_url)

                    # リンク内のテキスト全体を取得（タイトル+金額+達成率が含まれる）
                    full_text = link.get_text(strip=True)
                    if not full_text or len(full_text) < 10:
                        continue

                    # 金額を抽出（￥の後の数字、カンマ区切りで最大3桁ずつ）
                    funding = ""
                    # パターン: ￥1,234,567 のような形式を抽出
                    amount_match = re.search(r'[￥¥]([0-9]{1,3}(?:,[0-9]{3})*)', full_text)
                    if amount_match:
                        funding = amount_match.group(1) + "円"

                    # 達成率を抽出
                    percent = 0
                    percent_match = re.search(r'(\d+)%', full_text)
                    if percent_match:
                        percent = int(percent_match.group(1))

                    # タイトルを抽出（金額の前までのテキスト）
                    if amount_match:
                        title = full_text[:amount_match.start()].strip()
                    else:
                        # 金額がない場合は最初の80文字
                        title = full_text[:80]

                    if not title or len(title) < 5:
                        continue

                    print(f"         ✓ 発見: {title[:40]}...")
                    projects.append({
                        "name": title[:100],
                        "url": base_url,
                        "funding_amount": funding if funding else "募集中",
                        "backers": 0,  # 支援者数は詳細ページから取得が必要
                        "percent": percent,
                        "platform": "Makuake"
                    })

                    if len(projects) >= 5:
                        break

                except Exception as e:
                    continue

            return {
                "found": len(projects) > 0,
                "projects": projects,
                "search_note": f"Makuakeで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした",
                "search_attempted": True
            }

        except Exception as e:
            error_name = type(e).__name__
            print(f"     ⚠️ Makuake Selenium検索エラー: {error_name}: {e}")

            # セッション切れの場合はドライバーをリセットしてリトライ
            if 'InvalidSessionId' in error_name or 'session' in str(e).lower():
                if retry_count < 1:
                    print(f"     → ドライバーをリセットしてリトライ...")
                    self._close_driver()
                    new_driver = self._get_driver(force_new=True)
                    if new_driver:
                        return self._search_makuake_selenium(keyword, new_driver, retry_count + 1)

            return {"found": False, "projects": [], "search_note": str(e), "search_attempted": False}

    def _search_makuake_rss(self, keyword):
        """RSSフィードを使ったMakuake検索（フォールバック）"""
        try:
            rss_url = "https://www.makuake.com/rss/"
            print(f"     Makuake検索（RSS フォールバック）: {keyword}")

            response = self.session.get(rss_url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'xml')
            projects = []

            items = soup.find_all('item')
            print(f"       → RSSから{len(items)}件のアイテムを取得")
            for item in items:
                try:
                    title = item.find('title').get_text(strip=True) if item.find('title') else ""
                    link = item.find('link').get_text(strip=True) if item.find('link') else ""

                    if keyword.lower() in title.lower():
                        if link and '/project/' in link:
                            project_info = self._get_makuake_project_details(link)
                            if project_info:
                                projects.append(project_info)

                            if len(projects) >= 3:
                                break

                except Exception:
                    continue

            return {
                "found": len(projects) > 0,
                "projects": projects,
                "search_note": f"Makuakeで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした"
            }

        except Exception as e:
            print(f"     ⚠️ Makuake RSS検索エラー: {type(e).__name__}: {e}")
            return {"found": False, "projects": [], "search_note": str(e)}

    def _get_makuake_project_details(self, project_url):
        """
        Makuakeプロジェクトの詳細を取得（メタタグから）

        Args:
            project_url (str): プロジェクトURL

        Returns:
            dict: プロジェクト情報
        """
        try:
            response = self.session.get(project_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # メタタグからデータを取得（Makuakeは note: プロパティを使用）
            title = ""
            funding = ""
            backers = 0
            category = ""

            # note:title
            title_meta = soup.find('meta', property='note:title')
            if title_meta:
                title = title_meta.get('content', '')

            # note:current_amount
            amount_meta = soup.find('meta', property='note:current_amount')
            if amount_meta:
                amount = amount_meta.get('content', '0')
                if amount and amount != '0':
                    # 金額をフォーマット
                    try:
                        amount_int = int(amount)
                        funding = f"{amount_int:,}円"
                    except ValueError:
                        funding = f"{amount}円"

            # note:supporters
            supporters_meta = soup.find('meta', property='note:supporters')
            if supporters_meta:
                try:
                    backers = int(supporters_meta.get('content', '0'))
                except ValueError:
                    backers = 0

            # note:category
            category_meta = soup.find('meta', property='note:category')
            if category_meta:
                category = category_meta.get('content', '')

            # タイトルが取得できなかった場合はog:titleを試す
            if not title:
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    title = og_title.get('content', '').replace('Makuake｜', '').replace('｜Makuake（マクアケ）', '')

            if title:
                return {
                    "name": title[:100],  # 長すぎる場合は切り詰め
                    "url": project_url.split('?')[0].rstrip('/'),  # クエリパラメータを除去
                    "funding_amount": funding if funding else "募集中",
                    "backers": backers,
                    "category": category,
                    "platform": "Makuake"
                }

        except Exception as e:
            pass

        return None

    def search_campfire(self, keyword, filter_keywords=None):
        """
        CAMPFIREで類似製品を検索
        Seleniumを使用してJavaScriptレンダリング後のページから検索

        Args:
            keyword (str): 検索キーワード
            filter_keywords (list): 結果フィルタリング用キーワード（動的に生成）

        Returns:
            dict: 検索結果
        """
        if filter_keywords is None:
            filter_keywords = []

        # まずSeleniumで検索を試みる
        driver = self._get_driver()
        if driver:
            result = self._search_campfire_selenium(keyword, filter_keywords, driver)
            if result.get('found') or result.get('search_attempted') or result.get('geo_restricted'):
                return result

        # Seleniumが使えない場合は従来の方法でフォールバック
        return self._search_campfire_requests(keyword, filter_keywords)

    def _search_campfire_selenium(self, keyword, filter_keywords, driver):
        """Seleniumを使ったCAMPFIRE検索"""
        try:
            import urllib.parse
            search_url = f"https://camp-fire.jp/projects/search?word={urllib.parse.quote(keyword)}"
            print(f"     CAMPFIRE検索（Selenium）: {keyword}")
            print(f"       URL: {search_url}")

            driver.get(search_url)
            time.sleep(3)  # ページ読み込み待機

            # 海外IPリダイレクトを検知
            if 'Welcome' in driver.page_source and 'International' in driver.page_source:
                print(f"     ⚠️ CAMPFIRE: 海外IPからのアクセス制限が検知されました")
                return {
                    "found": False,
                    "projects": [],
                    "search_note": "海外からのアクセス制限のため取得できませんでした",
                    "geo_restricted": True,
                    "search_attempted": True
                }

            # プロジェクトカードを待機
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/projects/"]'))
                )
            except Exception:
                print(f"       → プロジェクトが見つかりませんでした")
                return {"found": False, "projects": [], "search_note": "該当する製品が見つかりませんでした", "search_attempted": True}

            # ページソースを取得してBeautifulSoupで解析
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            projects = []

            # プロジェクトリンクを検索
            project_links = soup.select('a[href*="/projects/"][href*="/view"]')
            seen_urls = set()
            print(f"       → {len(project_links)}件のリンクを発見")

            for link in project_links[:15]:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue

                    # 完全なURLを構築
                    if href.startswith('/'):
                        project_url = f"https://camp-fire.jp{href}"
                    elif not href.startswith('http'):
                        continue
                    else:
                        project_url = href

                    # 重複を除外
                    base_url = project_url.split('?')[0].rstrip('/')
                    if base_url in seen_urls:
                        continue
                    seen_urls.add(base_url)

                    # プロジェクト詳細を取得
                    project_info = self._get_campfire_project_details(project_url, keyword, filter_keywords)
                    if project_info:
                        projects.append(project_info)

                    if len(projects) >= 5:
                        break

                except Exception:
                    continue

            return {
                "found": len(projects) > 0,
                "projects": projects,
                "search_note": f"CAMPFIREで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした",
                "search_attempted": True
            }

        except Exception as e:
            print(f"     ⚠️ CAMPFIRE Selenium検索エラー: {type(e).__name__}: {e}")
            return {"found": False, "projects": [], "search_note": str(e), "search_attempted": False}

    def _search_campfire_requests(self, keyword, filter_keywords):
        """requestsを使ったCAMPFIRE検索（フォールバック）"""
        try:
            search_url = f"https://camp-fire.jp/projects/search?word={requests.utils.quote(keyword)}"
            print(f"     CAMPFIRE検索（requests フォールバック）: {keyword}")

            headers = {
                'Referer': 'https://camp-fire.jp/',
                'Cookie': 'locale=ja',
            }
            response = self.session.get(search_url, timeout=15, headers=headers)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # 海外IPからのアクセス制限を検知
            if 'Welcome' in response.text and 'International' in response.text:
                print(f"     ⚠️ CAMPFIRE: 海外IPからのアクセス制限が検知されました")
                return {
                    "found": False,
                    "projects": [],
                    "search_note": "海外からのアクセス制限のため取得できませんでした（GitHub Actions環境）",
                    "geo_restricted": True
                }

            soup = BeautifulSoup(response.text, 'html.parser')
            projects = []

            # プロジェクトリンクを検索（パターン: /projects/ID/view）
            project_links = soup.select('a[href*="/projects/"][href*="/view"]')
            print(f"       → {len(project_links)}件のリンクを発見")

            seen_urls = set()
            for link in project_links[:10]:
                try:
                    href = link.get('href', '')
                    if not href or href in seen_urls:
                        continue

                    seen_urls.add(href)

                    # 完全なURLを構築
                    if href.startswith('/'):
                        project_url = f"https://camp-fire.jp{href}"
                    elif not href.startswith('http'):
                        project_url = f"https://camp-fire.jp/{href}"
                    else:
                        project_url = href

                    # プロジェクト詳細を取得（フィルタキーワードを渡す）
                    project_info = self._get_campfire_project_details(project_url, keyword, filter_keywords)
                    if project_info:
                        projects.append(project_info)

                    if len(projects) >= 3:
                        break

                except Exception as e:
                    continue

            return {
                "found": len(projects) > 0,
                "projects": projects,
                "search_note": f"CAMPFIREで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした"
            }

        except Exception as e:
            print(f"     ⚠️ CAMPFIRE検索エラー: {type(e).__name__}: {e}")
            return {"found": False, "projects": [], "search_note": str(e)}

    def _get_campfire_project_details(self, project_url, keyword='', filter_keywords=None):
        """
        CAMPFIREプロジェクトの詳細を取得

        Args:
            project_url (str): プロジェクトURL
            keyword (str): 検索キーワード（タイトルに含まれるかチェック用）
            filter_keywords (list): 動的フィルタキーワード（製品特徴から生成）

        Returns:
            dict: プロジェクト情報（キーワードがタイトルに含まれない場合はNone）
        """
        if filter_keywords is None:
            filter_keywords = []
        try:
            response = self.session.get(project_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # プロジェクト名
            title_elem = soup.select_one('h1, .project-title, [class*="title"]')
            title = title_elem.get_text(strip=True) if title_elem else "不明"

            # 資金調達額
            funding = ""
            funding_elem = soup.select_one('[class*="amount"], [class*="collected"]')
            if funding_elem:
                funding_text = funding_elem.get_text(strip=True)
                amount_match = re.search(r'[\d,]+', funding_text)
                if amount_match:
                    funding = amount_match.group() + "円"

            # 支援者数
            backers = 0
            backers_elem = soup.select_one('[class*="backer"], [class*="supporter"], [class*="patron"]')
            if backers_elem:
                backers_text = backers_elem.get_text(strip=True)
                backers_match = re.search(r'[\d,]+', backers_text)
                if backers_match:
                    backers = int(backers_match.group().replace(',', ''))

            # 無効なタイトルを除外（通知ページなど非プロジェクト、海外リダイレクト）
            invalid_titles = [
                "プロジェクト公開の通知を受け取ろう",
                "通知を受け取る",
                "お気に入り",
                "ログイン",
                "Welcome",  # 海外IPからのアクセス時のリダイレクトページ
                "International",
            ]

            if title and title != "不明":
                # 無効なタイトルかチェック
                if any(invalid in title for invalid in invalid_titles):
                    print(f"         ✗ 除外（無効タイトル）: {title[:40]}...")
                    return None

                # キーワードがタイトルに含まれるかチェック
                if keyword or filter_keywords:
                    keyword_matched = False

                    # 検索キーワード完全マッチ
                    if keyword and keyword in title:
                        keyword_matched = True
                        print(f"         ✓ 完全マッチ（{keyword}）: {title[:40]}...")

                    # フィルタキーワードでの部分マッチ（動的に生成されたキーワード）
                    if not keyword_matched and filter_keywords:
                        for fk in filter_keywords:
                            if fk in title:
                                keyword_matched = True
                                print(f"         ✓ フィルタマッチ（{fk}）: {title[:40]}...")
                                break

                    # 検索キーワードの部分一致も試す（キーワードが複合語の場合）
                    if not keyword_matched and keyword and len(keyword) >= 4:
                        # 前半・後半に分割してマッチを試す
                        for i in range(2, len(keyword) - 1):
                            part1 = keyword[:i]
                            part2 = keyword[i:]
                            if len(part1) >= 2 and part1 in title:
                                keyword_matched = True
                                print(f"         ✓ 部分マッチ（{part1}）: {title[:40]}...")
                                break
                            if len(part2) >= 2 and part2 in title:
                                keyword_matched = True
                                print(f"         ✓ 部分マッチ（{part2}）: {title[:40]}...")
                                break

                    if not keyword_matched:
                        print(f"         ✗ 除外（キーワード不一致）: {title[:40]}...")
                        return None

                print(f"         ✓ 採用: {title[:40]}...")
                return {
                    "name": title[:100],
                    "url": project_url.split('?')[0],
                    "funding_amount": funding if funding else "非公開",
                    "backers": backers,
                    "platform": "CAMPFIRE"
                }

        except Exception as e:
            pass

        return None

    def search_similar_products(self, kickstarter_url, product_name=''):
        """
        類似製品を総合検索

        Args:
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            dict: 検索結果（Kickstarter製品情報含む）
        """
        print(f"  🔍 類似製品を検索中...")

        # 1. 製品カテゴリとキーワードを抽出（Kickstarter情報も取得）
        keyword_info = self.extract_product_keywords(kickstarter_url, product_name)
        keywords = keyword_info.get('keywords', [product_name])
        category = keyword_info.get('category', '製品')
        filter_keywords = keyword_info.get('filter_keywords', [])
        ks_info = keyword_info.get('ks_info', {})  # Kickstarter製品情報

        print(f"     カテゴリ: {category}")
        print(f"     キーワード: {', '.join(keywords)}")

        all_makuake_projects = []

        # 2. 各キーワードでMakuakeを検索（CAMPFIREは一時的に無効化）
        for keyword in keywords[:2]:  # 最大2キーワード
            # Makuakeで検索
            makuake_results = self.search_makuake(keyword)
            if makuake_results.get('found'):
                for p in makuake_results['projects']:
                    if not any(existing['url'] == p['url'] for existing in all_makuake_projects):
                        all_makuake_projects.append(p)

        # 3. 結果を制限（最大5件に増加）
        all_makuake_projects = all_makuake_projects[:5]

        has_results = len(all_makuake_projects) > 0

        if has_results:
            summary = f"Makuakeで{len(all_makuake_projects)}件の類似製品を発見"
        else:
            summary = "日本のクラウドファンディングで類似製品は見つかりませんでした。これは市場における先行者利益の可能性を示しています。"

        print(f"  ✓ 検索完了: {summary}")

        return {
            "category": category,
            "keywords": keywords,
            "kickstarter_info": ks_info,  # Kickstarter製品の詳細情報
            "makuake": {
                "found": len(all_makuake_projects) > 0,
                "projects": all_makuake_projects
            },
            "campfire": {
                "found": False,
                "projects": [],
                "disabled": True  # 一時的に無効化
            },
            "has_results": has_results,
            "summary": summary
        }

    def format_for_prompt(self, search_results):
        """
        検索結果をプロンプト用にフォーマット

        Args:
            search_results (dict): search_similar_products()の戻り値

        Returns:
            str: プロンプトに挿入する形式のテキスト
        """
        lines = []

        # === Kickstarter製品の詳細情報 ===
        ks_info = search_results.get('kickstarter_info', {})
        if ks_info:
            lines.append("=" * 50)
            lines.append("【分析対象のKickstarter製品 - 実データ】")
            lines.append("=" * 50)

            if ks_info.get('title'):
                lines.append(f"製品名: {ks_info['title']}")

            if ks_info.get('category'):
                lines.append(f"カテゴリ: {ks_info['category']}")

            # 資金調達情報
            if ks_info.get('funding_amount'):
                funding_line = f"調達額: {ks_info['funding_amount']}"
                if ks_info.get('goal_amount'):
                    funding_line += f" / 目標: {ks_info['goal_amount']}"
                if ks_info.get('percent_funded'):
                    funding_line += f" ({ks_info['percent_funded']}%達成)"
                lines.append(funding_line)

            if ks_info.get('backers_count'):
                lines.append(f"バッカー数: {ks_info['backers_count']:,}人")

            if ks_info.get('rewards'):
                lines.append(f"リワード価格帯: {', '.join(ks_info['rewards'][:5])}")

            if ks_info.get('days_left'):
                lines.append(f"キャンペーン状況: {ks_info['days_left']}")

            if ks_info.get('description'):
                lines.append(f"\n製品説明:\n{ks_info['description'][:400]}")

            lines.append("")

        # === 日本市場の類似製品情報 ===
        if not search_results.get('has_results', False):
            lines.append("=" * 50)
            lines.append("【日本クラウドファンディング市場調査結果】")
            lines.append("=" * 50)
            lines.append("")
            lines.append("調査の結果、日本のクラウドファンディングプラットフォーム（Makuake、CAMPFIRE）において、")
            lines.append("この製品に直接類似したキャンペーンは見つかりませんでした。")
            lines.append("")
            lines.append("これは以下のポジティブな意味を持ちます：")
            lines.append("・日本市場において、この製品カテゴリは未開拓である可能性が高い")
            lines.append("・先行者利益（First Mover Advantage）を得られる大きなチャンス")
            lines.append("・競合が少ないため、適切なマーケティングで市場リーダーになれる可能性")
            lines.append("・新規性が高く、メディアや消費者の注目を集めやすい")
            lines.append("")
            lines.append("レポートでは、類似製品が見つからなかったことを「未開拓市場への参入チャンス」として")
            lines.append("前向きに伝えてください。架空の製品名やURLは絶対に記載しないでください。")
        else:
            lines.append("=" * 50)
            lines.append("【日本クラウドファンディング市場調査結果 - 検証済み実データ】")
            lines.append("=" * 50)
            lines.append(f"製品カテゴリ: {search_results.get('category', '製品')}")
            lines.append("※以下のデータはMakuakeウェブサイトから自動取得した実在する情報です。")
            lines.append("")

            # Makuake結果
            makuake = search_results.get('makuake', {})
            if makuake.get('found', False) and makuake.get('projects'):
                lines.append(f"■ Makuakeの類似製品（{len(makuake['projects'])}件発見）:")
                for i, p in enumerate(makuake['projects'], 1):
                    lines.append(f"  【製品{i}】")
                    lines.append(f"    製品名: {p.get('name', '不明')}")
                    lines.append(f"    URL: {p.get('url', '')}")
                    lines.append(f"    資金調達額: {p.get('funding_amount', '非公開')}")
                    if p.get('backers'):
                        lines.append(f"    支援者数: {p.get('backers')}人")
                    lines.append("")
            else:
                lines.append("■ Makuake: 類似製品は見つかりませんでした")
                lines.append("  → これは市場が未開拓である可能性を示しています")
                lines.append("")

        # === 分析指示 ===
        lines.append("")
        lines.append("=" * 50)
        lines.append("【レポート作成ルール - 必ず守ること】")
        lines.append("=" * 50)
        lines.append("")
        lines.append("■ Kickstarter製品の分析（必須）:")
        lines.append("1. 上記のKickstarter製品データ（調達額、バッカー数、価格帯）を必ず引用すること")
        lines.append("2. この製品の具体的な特徴・強みを分析すること")
        lines.append("3. 日本市場での具体的な価格設定を提案すること（為替レート考慮）")
        lines.append("4. バッカー数から想定される日本での支援者数を予測すること")
        lines.append("")
        lines.append("■ 日本市場データの使用:")
        lines.append("1. 上記のMakuake製品情報のみをレポートに使用すること")
        lines.append("2. 製品名・URL・金額・支援者数は上記データをそのまま引用")
        lines.append("3. 上記に記載のないデータは絶対に追加しない（架空データ禁止）")
        lines.append("4. 市場予測は上記データを根拠として計算すること")
        lines.append("")
        lines.append("■ 出力形式:")
        lines.append("1. URLは文中に自然に埋め込む（「URL：」プレフィックス不要）")
        lines.append("2. 末尾に「情報源」「Sources」セクションを作らない")
        lines.append("3. 架空のURL（www.example.com等）は絶対に記載しない")
        lines.append("=" * 50)

        return "\n".join(lines)


def test_search():
    """テスト用関数"""
    from dotenv import load_dotenv
    load_dotenv()

    searcher = MarketSearcher()

    # テスト検索
    print("=" * 60)
    print("類似製品検索テスト")
    print("=" * 60)

    results = searcher.search_similar_products(
        "https://www.kickstarter.com/projects/fearlesstoys/spinbrick/creator",
        "SpinBrick - 知育玩具"
    )

    print("\n" + "=" * 60)
    print("検索結果サマリー")
    print("=" * 60)
    print(f"カテゴリ: {results.get('category')}")
    print(f"キーワード: {results.get('keywords')}")
    print(f"結果あり: {results.get('has_results')}")

    print("\n" + "=" * 60)
    print("Makuake結果")
    print("=" * 60)
    for p in results.get('makuake', {}).get('projects', []):
        print(f"  - {p.get('name')}")
        print(f"    URL: {p.get('url')}")
        print(f"    資金: {p.get('funding_amount')}")

    print("\n" + "=" * 60)
    print("CAMPFIRE結果")
    print("=" * 60)
    for p in results.get('campfire', {}).get('projects', []):
        print(f"  - {p.get('name')}")
        print(f"    URL: {p.get('url')}")
        print(f"    資金: {p.get('funding_amount')}")

    print("\n" + "=" * 60)
    print("プロンプト用フォーマット")
    print("=" * 60)
    print(searcher.format_for_prompt(results))


if __name__ == '__main__':
    test_search()
