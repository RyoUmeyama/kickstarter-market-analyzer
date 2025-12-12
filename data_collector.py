#!/usr/bin/env python3
"""
データ収集モジュール（Phase 1）
複数ソースから製品データを収集し、構造化JSONを生成

データソース:
1. Kickstarter - 製品詳細、資金調達情報
2. Kicktraq - 統計データ
3. BackerKit - 平均Pledge等
4. Amazon.co.jp - 日本EC流通確認
5. Makuake/CAMPFIRE - 日本CF実績
6. 為替API - USD/JPYレート
7. 公式サイト - MSRP（定価）
"""

import os
import re
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse

# Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwrightが利用できません")

# OpenAI（公式サイト価格取得用）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class DataCollector:
    """
    複数ソースからデータを収集するクラス

    収集データは全て出典URLと取得日時を含む
    """

    def __init__(self, openai_api_key=None):
        """
        Args:
            openai_api_key: OpenAI APIキー（公式サイト検索用）
        """
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if self.openai_api_key and OPENAI_AVAILABLE:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None

        # HTTPセッション
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        })

        # Playwright（遅延初期化）
        self._playwright = None
        self._browser = None
        self._context = None

        # 収集データの格納
        self.collected_data = {
            "meta": {
                "collected_at": datetime.now().isoformat(),
                "kickstarter_url": "",
            },
            "kickstarter": {},
            "kicktraq": {},
            "backerkit": {},
            "amazon_jp": {},
            "makuake": {},
            "campfire": {},
            "exchange_rate": {},
            "official_site": {},
            "errors": []
        }

    def _get_browser(self):
        """Playwrightブラウザを取得"""
        if not PLAYWRIGHT_AVAILABLE:
            return None

        if self._browser is None:
            try:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                self._context = self._browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    locale='ja-JP',
                    timezone_id='Asia/Tokyo',
                )
            except Exception as e:
                print(f"⚠️ Playwright初期化エラー: {e}")
                return None

        return self._browser

    def _close_browser(self):
        """ブラウザを閉じる"""
        if self._context:
            try:
                self._context.close()
            except:
                pass
        if self._browser:
            try:
                self._browser.close()
            except:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except:
                pass
        self._context = None
        self._browser = None
        self._playwright = None

    def collect_all(self, kickstarter_url, product_keywords=None):
        """
        全データソースからデータを収集

        Args:
            kickstarter_url: KickstarterのURL
            product_keywords: 検索用キーワード（Noneの場合はKickstarterから抽出）

        Returns:
            dict: 収集した全データ（構造化JSON）

        Note:
            Kickstarterからのデータ取得は必須。
            タイトル・調達額・バッカー数が取得できない場合はエラーを記録。
        """
        print("=" * 60)
        print("📊 データ収集開始")
        print("=" * 60)

        self.collected_data["meta"]["kickstarter_url"] = kickstarter_url

        # ========================================
        # Phase 1: Kickstarterデータ取得（必須）
        # ========================================
        print("\n[1/7] Kickstarter データ取得中...")
        self._collect_kickstarter(kickstarter_url)

        # Kickstarterデータの検証
        ks_data = self.collected_data.get("kickstarter", {})
        ks_title = ks_data.get("title", "")
        ks_funding = ks_data.get("funding_amount_usd", 0)
        ks_backers = ks_data.get("backers_count", 0)

        if not ks_title:
            print("  ❌ Kickstarter: タイトル取得失敗")
            self.collected_data["errors"].append("Kickstarter: タイトル取得失敗 - 製品情報が不明")

        if not ks_funding:
            print("  ⚠️ Kickstarter: 調達額取得失敗")
            self.collected_data["errors"].append("Kickstarter: 調達額取得失敗")

        if not ks_backers:
            print("  ⚠️ Kickstarter: バッカー数取得失敗")
            self.collected_data["errors"].append("Kickstarter: バッカー数取得失敗")

        # 最低限の情報（タイトル）がない場合は警告
        if not ks_title:
            print("\n  ⚠️ 警告: Kickstarter製品情報が取得できませんでした")
            print("       続行しますが、レポート品質に影響があります")

        # ========================================
        # Phase 2: 補助データ取得
        # ========================================
        # 2. Kicktraqデータ取得
        print("\n[2/7] Kicktraq データ取得中...")
        self._collect_kicktraq(kickstarter_url)

        # 3. BackerKitデータ取得
        print("\n[3/7] BackerKit データ取得中...")
        self._collect_backerkit(kickstarter_url)

        # 4. 為替レート取得
        print("\n[4/7] 為替レート取得中...")
        self._collect_exchange_rate()

        # ========================================
        # Phase 3: 日本市場調査（製品名で検索）
        # ========================================
        # キーワードが指定されていない場合、Kickstarterの製品名から生成
        if not product_keywords:
            product_keywords = self._extract_keywords()

        if not product_keywords:
            print("  ⚠️ 検索キーワードが抽出できませんでした")
            self.collected_data["errors"].append("キーワード抽出失敗: Kickstarterタイトルが不明")
        else:
            print(f"  検索キーワード: {product_keywords}")

        # 5. Amazon.co.jp検索
        print("\n[5/7] Amazon.co.jp 検索中...")
        self._collect_amazon_jp(product_keywords)

        # 6. Makuake検索
        print("\n[6/7] Makuake 検索中...")
        self._collect_makuake(product_keywords)

        # 7. CAMPFIRE検索
        print("\n[7/7] CAMPFIRE 検索中...")
        self._collect_campfire(product_keywords)

        # ブラウザを閉じる
        self._close_browser()

        print("\n" + "=" * 60)
        print("✅ データ収集完了")
        print("=" * 60)

        # 収集結果のサマリー
        error_count = len(self.collected_data.get("errors", []))
        if error_count > 0:
            print(f"  ⚠️ {error_count}件のエラーが発生しました")

        return self.collected_data

    def _normalize_kickstarter_url(self, url):
        """KickstarterのURLを正規化"""
        base_url = url.split('?')[0]
        for suffix in ['/creator', '/description', '/comments', '/updates', '/community', '/faqs', '/rewards']:
            if base_url.endswith(suffix):
                base_url = base_url[:-len(suffix)]
        return base_url

    def _collect_kickstarter(self, kickstarter_url):
        """Kickstarterからデータを収集"""
        base_url = self._normalize_kickstarter_url(kickstarter_url)

        data = {
            "source_url": base_url,
            "collected_at": datetime.now().isoformat(),
            "title": "",
            "description": "",
            "category": "",
            "creator_name": "",
            "funding_amount": "",
            "funding_amount_usd": 0,
            "goal_amount": "",
            "goal_amount_usd": 0,
            "percent_funded": 0,
            "backers_count": 0,
            "days_left": "",
            "campaign_status": "",  # active, successful, failed
            "campaign_end_date": "",
            "rewards": [],
            "data_quality": "none"  # none, partial, full
        }

        browser = self._get_browser()
        if not browser:
            self.collected_data["errors"].append("Kickstarter: ブラウザ初期化失敗")
            self.collected_data["kickstarter"] = data
            return

        page = None
        try:
            page = self._context.new_page()
            page.goto(base_url, wait_until='load', timeout=60000)
            page.wait_for_timeout(5000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()

            # ブロックチェック
            if 'しばらくお待ちください' in page_text or 'please wait' in page_text.lower():
                self.collected_data["errors"].append("Kickstarter: アクセスブロック")
                data["data_quality"] = "blocked"
                self.collected_data["kickstarter"] = data
                return

            # タイトル
            og_title = soup.find('meta', property='og:title')
            if og_title:
                data["title"] = og_title.get('content', '').replace(' — Kickstarter', '').strip()
                print(f"  ✓ タイトル: {data['title'][:50]}...")

            # 説明
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                data["description"] = og_desc.get('content', '')[:500]

            # 資金調達額
            for selector in ['span.ksr-green-500', 'span.soft-black', 'span.money']:
                funding_elem = soup.select_one(selector)
                if funding_elem:
                    funding_text = funding_elem.get_text(strip=True)
                    if re.search(r'[\$€£¥]', funding_text):
                        data["funding_amount"] = funding_text.strip()
                        # USD金額を抽出
                        usd_match = re.search(r'\$([\d,]+)', funding_text)
                        if usd_match:
                            data["funding_amount_usd"] = int(usd_match.group(1).replace(',', ''))
                        print(f"  ✓ 調達額: {data['funding_amount']}")
                        break

            # 目標金額 - 複数のパターンで抽出を試みる
            goal_patterns = [
                # "pledged of $15,000 goal" パターン
                r'pledged\s+of\s+\$([\d,]+)\s*goal',
                # "$143,110 pledged of $15,000 goal" パターン
                r'\$[\d,]+\s+pledged\s+of\s+\$([\d,]+)',
                # "of $15,000 goal" パターン
                r'of\s+\$([\d,]+)\s*goal',
                # "$15,000 goal" パターン
                r'\$([\d,]+)\s*goal',
                # "goal $15,000" パターン
                r'goal\s*[:\s]*\$([\d,]+)',
            ]
            for pattern in goal_patterns:
                goal_match = re.search(pattern, page_text, re.I)
                if goal_match:
                    goal_amount = goal_match.group(1).replace(',', '')
                    data["goal_amount"] = f"${goal_match.group(1)}"
                    data["goal_amount_usd"] = int(goal_amount)
                    print(f"  ✓ 目標額: {data['goal_amount']}")
                    break

            # HTMLから直接取得を試みる（メタデータやJSON-LD）
            if not data["goal_amount_usd"]:
                # JSON-LDからの抽出を試みる
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        ld_data = json.loads(script.string)
                        if isinstance(ld_data, dict):
                            # fundingGoalなどのフィールドを探す
                            goal = ld_data.get('fundingGoal', {})
                            if isinstance(goal, dict) and 'value' in goal:
                                data["goal_amount_usd"] = int(float(goal['value']))
                                data["goal_amount"] = f"${data['goal_amount_usd']:,}"
                                print(f"  ✓ 目標額（JSON-LD）: {data['goal_amount']}")
                    except:
                        continue

            # バッカー数
            backers_match = re.search(r'([\d,]+)\s*(?:backers?|人のバッカー)', page_text, re.I)
            if backers_match:
                data["backers_count"] = int(backers_match.group(1).replace(',', ''))
                print(f"  ✓ バッカー数: {data['backers_count']}人")

            # 達成率計算
            if data["funding_amount_usd"] and data["goal_amount_usd"]:
                data["percent_funded"] = int((data["funding_amount_usd"] / data["goal_amount_usd"]) * 100)
                print(f"  ✓ 達成率: {data['percent_funded']}%")

            # 残り日数
            days_match = re.search(r'(\d+)\s*(?:days?\s*(?:to go|left)|日)', page_text, re.I)
            if days_match:
                data["days_left"] = days_match.group(1)

            # キャンペーンステータス判定
            if 'successfully funded' in page_text.lower() or 'funded!' in page_text.lower():
                data["campaign_status"] = "successful"
            elif data.get("days_left"):
                data["campaign_status"] = "active"
            else:
                data["campaign_status"] = "ended"

            # データ品質評価
            if data["funding_amount"] and data["backers_count"]:
                data["data_quality"] = "full"
            elif data["title"]:
                data["data_quality"] = "partial"

        except Exception as e:
            self.collected_data["errors"].append(f"Kickstarter: {str(e)}")
            print(f"  ⚠️ エラー: {e}")
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass

        self.collected_data["kickstarter"] = data

    def _collect_kicktraq(self, kickstarter_url):
        """Kicktraqから統計データを収集"""
        base_url = self._normalize_kickstarter_url(kickstarter_url)
        kicktraq_url = base_url.replace('www.kickstarter.com', 'www.kicktraq.com')
        if not kicktraq_url.endswith('/'):
            kicktraq_url += '/'

        data = {
            "source_url": kicktraq_url,
            "collected_at": datetime.now().isoformat(),
            "funding_amount": "",
            "funding_amount_usd": 0,
            "backers_count": 0,
            "average_pledge": "",
            "average_pledge_usd": 0,
            "campaign_duration": "",
            "campaign_dates": "",
            "data_quality": "none"
        }

        try:
            response = self.session.get(kicktraq_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # 未インデックスチェック
            if 'magical ninja-gnomes' in page_text or 'We should have something' in page_text:
                print("  ⚠️ Kicktraq: まだインデックスされていません")
                data["data_quality"] = "not_indexed"
                self.collected_data["kicktraq"] = data
                return

            # 調達額
            pledged_match = re.search(r'\$([\d,]+)\s*pledged', page_text, re.I)
            if pledged_match:
                data["funding_amount"] = f"${pledged_match.group(1)}"
                data["funding_amount_usd"] = int(pledged_match.group(1).replace(',', ''))
                print(f"  ✓ 調達額: {data['funding_amount']}")

            # バッカー数
            backers_match = re.search(r'([\d,]+)\s*backers?', page_text, re.I)
            if backers_match:
                data["backers_count"] = int(backers_match.group(1).replace(',', ''))
                print(f"  ✓ バッカー数: {data['backers_count']}人")

            # 平均Pledge計算
            if data["funding_amount_usd"] and data["backers_count"]:
                avg = data["funding_amount_usd"] / data["backers_count"]
                data["average_pledge_usd"] = round(avg, 2)
                data["average_pledge"] = f"${data['average_pledge_usd']:.2f}"
                print(f"  ✓ 平均Pledge: {data['average_pledge']}")

            # キャンペーン期間
            duration_match = re.search(r'(\d+)\s*days?(?:\s*campaign)?', page_text, re.I)
            if duration_match:
                data["campaign_duration"] = f"{duration_match.group(1)}日間"

            # データ品質評価
            if data["funding_amount_usd"] and data["backers_count"]:
                data["data_quality"] = "full"
            elif data["funding_amount_usd"]:
                data["data_quality"] = "partial"

        except Exception as e:
            self.collected_data["errors"].append(f"Kicktraq: {str(e)}")
            print(f"  ⚠️ エラー: {e}")

        self.collected_data["kicktraq"] = data

    def _collect_backerkit(self, kickstarter_url):
        """BackerKitから統計データを収集"""
        base_url = self._normalize_kickstarter_url(kickstarter_url)

        # KickstarterのURLからプロジェクトIDを抽出
        # 例: /projects/726629114/maxpro-air-... → 726629114/maxpro-air-...
        match = re.search(r'/projects/([^/]+/[^/?]+)', base_url)
        if not match:
            print("  ⚠️ BackerKit: プロジェクトID抽出失敗")
            self.collected_data["backerkit"] = {"data_quality": "none"}
            return

        project_path = match.group(1)
        backerkit_url = f"https://www.backerkit.com/projects/{project_path}"

        data = {
            "source_url": backerkit_url,
            "collected_at": datetime.now().isoformat(),
            "funding_amount": "",
            "funding_amount_usd": 0,
            "backers_count": 0,
            "average_pledge": "",
            "average_pledge_usd": 0,
            "data_quality": "none"
        }

        try:
            response = self.session.get(backerkit_url, timeout=15)

            if response.status_code == 404:
                print("  ⚠️ BackerKit: プロジェクトが見つかりません")
                data["data_quality"] = "not_found"
                self.collected_data["backerkit"] = data
                return

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # 調達額
            pledged_match = re.search(r'\$([\d,]+)\s*(?:pledged|raised)', page_text, re.I)
            if pledged_match:
                data["funding_amount"] = f"${pledged_match.group(1)}"
                data["funding_amount_usd"] = int(pledged_match.group(1).replace(',', ''))
                print(f"  ✓ 調達額: {data['funding_amount']}")

            # バッカー数
            backers_match = re.search(r'([\d,]+)\s*backers?', page_text, re.I)
            if backers_match:
                data["backers_count"] = int(backers_match.group(1).replace(',', ''))
                print(f"  ✓ バッカー数: {data['backers_count']}人")

            # 平均Pledge
            avg_match = re.search(r'(?:average|avg)[:\s]*\$([\d,.]+)', page_text, re.I)
            if avg_match:
                data["average_pledge"] = f"${avg_match.group(1)}"
                data["average_pledge_usd"] = float(avg_match.group(1).replace(',', ''))
                print(f"  ✓ 平均Pledge: {data['average_pledge']}")
            elif data["funding_amount_usd"] and data["backers_count"]:
                # 計算で求める
                avg = data["funding_amount_usd"] / data["backers_count"]
                data["average_pledge_usd"] = round(avg, 2)
                data["average_pledge"] = f"${data['average_pledge_usd']:.2f}"
                print(f"  ✓ 平均Pledge（計算）: {data['average_pledge']}")

            # データ品質評価
            if data["funding_amount_usd"] and data["backers_count"]:
                data["data_quality"] = "full"
            elif data["funding_amount_usd"]:
                data["data_quality"] = "partial"

        except Exception as e:
            self.collected_data["errors"].append(f"BackerKit: {str(e)}")
            print(f"  ⚠️ エラー: {e}")

        self.collected_data["backerkit"] = data

    def _collect_exchange_rate(self):
        """為替レート（USD/JPY）を取得"""
        data = {
            "source_url": "",
            "collected_at": datetime.now().isoformat(),
            "usd_jpy": 0,
            "source_name": "",
            "data_quality": "none"
        }

        # 複数のAPIを試行
        apis = [
            {
                "name": "ExchangeRate-API",
                "url": "https://api.exchangerate-api.com/v4/latest/USD",
                "extract": lambda r: r.json().get("rates", {}).get("JPY")
            },
            {
                "name": "Open Exchange Rates (free)",
                "url": "https://open.er-api.com/v6/latest/USD",
                "extract": lambda r: r.json().get("rates", {}).get("JPY")
            },
        ]

        for api in apis:
            try:
                response = self.session.get(api["url"], timeout=10)
                response.raise_for_status()
                rate = api["extract"](response)
                if rate:
                    data["usd_jpy"] = round(float(rate), 2)
                    data["source_url"] = api["url"]
                    data["source_name"] = api["name"]
                    data["data_quality"] = "full"
                    print(f"  ✓ USD/JPY: {data['usd_jpy']} ({api['name']})")
                    break
            except Exception as e:
                continue

        # フォールバック（固定値）
        if not data["usd_jpy"]:
            data["usd_jpy"] = 150.0  # フォールバック値
            data["source_name"] = "フォールバック（固定値）"
            data["data_quality"] = "fallback"
            print(f"  ⚠️ 為替API失敗、フォールバック値使用: {data['usd_jpy']}")

        self.collected_data["exchange_rate"] = data

    def _extract_keywords(self):
        """収集済みデータからキーワードを抽出

        シンプルな戦略:
        - Kickstarterの製品名（ブランド名）をそのまま検索キーワードとして使用
        - マッピングは使わない（数百の製品URLがあり、カテゴリは予測不可能）

        例: "MAXPRO Air: 100+lbs of Resistance. Just 2.5lbs of Gear."
        → ["MAXPRO", "MAXPRO Air"]
        """
        # 除外する一般的な単語（冠詞、前置詞など）
        STOP_WORDS = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'dare', 'ought', 'used', 'your', 'my', 'our', 'their', 'its', 'his',
            'her', 'this', 'that', 'these', 'those', 'new', 'all', 'just', 'only',
            'now', 'world', 'first', 'best', 'most', 'ultimate', 'perfect',
        }

        keywords = []

        ks_data = self.collected_data.get("kickstarter", {})
        title = ks_data.get("title", "")

        if not title:
            return []

        # タイトルからブランド名/製品名を抽出
        # コロン、ハイフン、パイプなどで分割して最初の部分を取得
        # 例: "MAXPRO Air: 100+lbs of Resistance..." → "MAXPRO Air"
        parts = re.split(r'[:\-–|]', title)
        if parts:
            brand_part = parts[0].strip()
            # 英数字を含む有効なブランド名のみ
            if re.search(r'[A-Za-z0-9]', brand_part) and len(brand_part) >= 2:
                words = brand_part.split()
                if words:
                    # 最初の単語（ブランド名）を追加（ストップワードでない場合）
                    first_word = words[0]
                    if len(first_word) >= 2 and first_word.lower() not in STOP_WORDS:
                        keywords.append(first_word)

                    # ストップワードで始まる場合、2番目以降の単語を試す
                    if not keywords and len(words) > 1:
                        for word in words[1:]:
                            if len(word) >= 2 and word.lower() not in STOP_WORDS:
                                keywords.append(word)
                                break

                    # フルネーム（製品名）も追加（異なる場合）
                    # ストップワードで始まる場合は除去して追加
                    if len(brand_part) <= 50:
                        clean_brand = brand_part
                        if words[0].lower() in STOP_WORDS:
                            clean_brand = ' '.join(words[1:]).strip()
                        if clean_brand and clean_brand not in keywords:
                            keywords.append(clean_brand)

        # 重複を除去
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and kw_lower not in STOP_WORDS:
                seen.add(kw_lower)
                unique_keywords.append(kw)

        print(f"  抽出キーワード: {unique_keywords}")
        return unique_keywords

    def _collect_amazon_jp(self, keywords):
        """Amazon.co.jpで製品を検索"""
        data = {
            "source_url": "",
            "collected_at": datetime.now().isoformat(),
            "search_keywords": keywords,
            "same_brand_found": False,
            "same_product_found": False,
            "products": [],
            "data_quality": "none"
        }

        if not keywords:
            self.collected_data["amazon_jp"] = data
            return

        browser = self._get_browser()
        if not browser:
            self.collected_data["errors"].append("Amazon.co.jp: ブラウザ初期化失敗")
            self.collected_data["amazon_jp"] = data
            return

        # ブランド名で検索（最初のキーワード）
        search_keyword = keywords[0]
        search_url = f"https://www.amazon.co.jp/s?k={quote(search_keyword)}"
        data["source_url"] = search_url

        page = None
        try:
            page = self._context.new_page()
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)

            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # 検索結果を解析
            items = soup.select('div[data-component-type="s-search-result"]')
            print(f"  検索結果: {len(items)}件")

            for item in items[:10]:
                try:
                    # 製品タイトル
                    title_elem = item.select_one('h2 a span')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)

                    # URL
                    link_elem = item.select_one('h2 a')
                    url = ""
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href.startswith('/'):
                            url = f"https://www.amazon.co.jp{href}"
                        else:
                            url = href

                    # 価格
                    price = ""
                    price_elem = item.select_one('span.a-price-whole')
                    if price_elem:
                        price = price_elem.get_text(strip=True)
                        price = f"¥{price}"

                    # レビュー数
                    reviews = 0
                    review_elem = item.select_one('span.a-size-base.s-underline-text')
                    if review_elem:
                        review_text = review_elem.get_text(strip=True)
                        review_match = re.search(r'([\d,]+)', review_text)
                        if review_match:
                            reviews = int(review_match.group(1).replace(',', ''))

                    product_data = {
                        "title": title[:100],
                        "url": url.split('?')[0] if url else "",
                        "price": price,
                        "reviews": reviews
                    }
                    data["products"].append(product_data)

                    # 同一ブランドチェック
                    if search_keyword.lower() in title.lower():
                        data["same_brand_found"] = True
                        print(f"  ✓ 同一ブランド発見: {title[:40]}...")

                except Exception:
                    continue

            if data["products"]:
                data["data_quality"] = "full"
            else:
                data["data_quality"] = "no_results"
                print("  検索結果なし")

        except Exception as e:
            self.collected_data["errors"].append(f"Amazon.co.jp: {str(e)}")
            print(f"  ⚠️ エラー: {e}")
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass

        self.collected_data["amazon_jp"] = data

    def _collect_makuake(self, keywords):
        """Makuakeで類似製品を検索"""
        data = {
            "source_url": "",
            "collected_at": datetime.now().isoformat(),
            "search_keywords": keywords,
            "same_product_found": False,
            "similar_products": [],
            "data_quality": "none"
        }

        if not keywords:
            self.collected_data["makuake"] = data
            return

        browser = self._get_browser()
        if not browser:
            self.collected_data["errors"].append("Makuake: ブラウザ初期化失敗")
            self.collected_data["makuake"] = data
            return

        all_products = []

        for keyword in keywords[:2]:
            search_url = f"https://www.makuake.com/discover/projects/?keyword={quote(keyword)}"

            if not data["source_url"]:
                data["source_url"] = search_url

            page = None
            try:
                page = self._context.new_page()
                page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                project_links = soup.select('a[href*="/project/"]')
                print(f"  「{keyword}」: {len(project_links)}件のリンク")

                seen_urls = set()
                for link in project_links[:15]:
                    try:
                        href = link.get('href', '')
                        if not href or '/project/' not in href:
                            continue

                        if href.startswith('/'):
                            project_url = f"https://www.makuake.com{href}"
                        else:
                            project_url = href

                        base_url = project_url.split('?')[0].rstrip('/')
                        if base_url in seen_urls:
                            continue
                        seen_urls.add(base_url)

                        full_text = link.get_text(strip=True)
                        if not full_text or len(full_text) < 10:
                            continue

                        # 金額抽出
                        funding = ""
                        funding_jpy = 0
                        amount_match = re.search(r'[￥¥]([0-9]{1,3}(?:,[0-9]{3})*)', full_text)
                        if amount_match:
                            funding = amount_match.group(1) + "円"
                            funding_jpy = int(amount_match.group(1).replace(',', ''))

                        # 達成率
                        percent = 0
                        percent_match = re.search(r'(\d+)%', full_text)
                        if percent_match:
                            percent = int(percent_match.group(1))

                        # タイトル
                        if amount_match:
                            title = full_text[:amount_match.start()].strip()
                        else:
                            title = full_text[:80]

                        if not title or len(title) < 5:
                            continue

                        product_data = {
                            "title": title[:100],
                            "url": base_url,
                            "funding_amount": funding,
                            "funding_amount_jpy": funding_jpy,
                            "percent_funded": percent,
                            "platform": "Makuake"
                        }

                        if not any(p["url"] == base_url for p in all_products):
                            all_products.append(product_data)
                            print(f"    ✓ {title[:30]}... ({funding})")

                    except Exception:
                        continue

            except Exception as e:
                self.collected_data["errors"].append(f"Makuake({keyword}): {str(e)}")
                print(f"  ⚠️ エラー: {e}")
            finally:
                if page:
                    try:
                        page.close()
                    except:
                        pass

        data["similar_products"] = all_products[:10]

        if all_products:
            data["data_quality"] = "full"
            print(f"  合計: {len(data['similar_products'])}件の類似製品")
        else:
            data["data_quality"] = "no_results"
            print("  類似製品なし")

        self.collected_data["makuake"] = data

    def _collect_campfire(self, keywords):
        """CAMPFIREで類似製品を検索"""
        data = {
            "source_url": "",
            "collected_at": datetime.now().isoformat(),
            "search_keywords": keywords,
            "same_product_found": False,
            "similar_products": [],
            "geo_restricted": False,
            "data_quality": "none"
        }

        if not keywords:
            self.collected_data["campfire"] = data
            return

        browser = self._get_browser()
        if not browser:
            self.collected_data["errors"].append("CAMPFIRE: ブラウザ初期化失敗")
            self.collected_data["campfire"] = data
            return

        all_products = []

        for keyword in keywords[:2]:
            search_url = f"https://camp-fire.jp/projects/search?word={quote(keyword)}"

            if not data["source_url"]:
                data["source_url"] = search_url

            page = None
            try:
                page = self._context.new_page()
                page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # 海外IP制限チェック
                if 'Welcome' in html and 'International' in html:
                    print(f"  ⚠️ CAMPFIRE: 海外IPからのアクセス制限")
                    data["geo_restricted"] = True
                    data["data_quality"] = "geo_restricted"
                    break

                project_links = soup.select('a[href*="/projects/"][href*="/view"]')
                print(f"  「{keyword}」: {len(project_links)}件のリンク")

                seen_urls = set()
                for link in project_links[:15]:
                    try:
                        href = link.get('href', '')
                        if not href:
                            continue

                        if href.startswith('/'):
                            project_url = f"https://camp-fire.jp{href}"
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
                        invalid = ["プロジェクト公開の通知", "通知を受け取る", "お気に入り", "ログイン"]
                        if any(inv in full_text for inv in invalid):
                            continue

                        # 金額
                        funding = ""
                        funding_jpy = 0
                        amount_match = re.search(r'([\d,]+)円', full_text)
                        if amount_match:
                            funding = amount_match.group(1) + "円"
                            funding_jpy = int(amount_match.group(1).replace(',', ''))

                        # 達成率
                        percent = 0
                        percent_match = re.search(r'(\d+)%', full_text)
                        if percent_match:
                            percent = int(percent_match.group(1))

                        # タイトル整形
                        title = full_text
                        prefixes = ['募集終了FINISH', '募集終了SUCCESS', '募集終了', 'FINISH', 'SUCCESS']
                        for prefix in prefixes:
                            if title.startswith(prefix):
                                title = title[len(prefix):].strip()
                        title = re.sub(r'(FINISH|SUCCESS|FUNDED)現在.*$', '', title).strip()
                        title = re.sub(r'\d{1,3}(,\d{3})*円.*$', '', title).strip()

                        if not title or len(title) < 5:
                            continue

                        product_data = {
                            "title": title[:100],
                            "url": base_url,
                            "funding_amount": funding,
                            "funding_amount_jpy": funding_jpy,
                            "percent_funded": percent,
                            "platform": "CAMPFIRE"
                        }

                        if not any(p["url"] == base_url for p in all_products):
                            all_products.append(product_data)
                            print(f"    ✓ {title[:30]}... ({funding})")

                    except Exception:
                        continue

            except Exception as e:
                self.collected_data["errors"].append(f"CAMPFIRE({keyword}): {str(e)}")
                print(f"  ⚠️ エラー: {e}")
            finally:
                if page:
                    try:
                        page.close()
                    except:
                        pass

        data["similar_products"] = all_products[:10]

        if all_products:
            data["data_quality"] = "full"
            print(f"  合計: {len(data['similar_products'])}件の類似製品")
        elif not data["geo_restricted"]:
            data["data_quality"] = "no_results"
            print("  類似製品なし")

        self.collected_data["campfire"] = data

    def get_summary(self):
        """収集データのサマリーを取得"""
        ks = self.collected_data.get("kickstarter", {})
        kt = self.collected_data.get("kicktraq", {})
        bk = self.collected_data.get("backerkit", {})
        fx = self.collected_data.get("exchange_rate", {})
        az = self.collected_data.get("amazon_jp", {})
        mk = self.collected_data.get("makuake", {})
        cf = self.collected_data.get("campfire", {})

        summary = {
            "製品名": ks.get("title", "不明"),
            "Kickstarter調達額": ks.get("funding_amount", "未取得"),
            "バッカー数": ks.get("backers_count", 0),
            "平均Pledge": bk.get("average_pledge") or kt.get("average_pledge") or "未取得",
            "為替レート": f"$1 = ¥{fx.get('usd_jpy', 0)}",
            "Amazon.co.jp": "ブランド発見" if az.get("same_brand_found") else "未発見",
            "Makuake類似製品": len(mk.get("similar_products", [])),
            "CAMPFIRE類似製品": len(cf.get("similar_products", [])),
            "エラー": len(self.collected_data.get("errors", [])),
        }

        return summary

    def to_json(self, filepath=None):
        """収集データをJSONとして出力"""
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.collected_data, f, ensure_ascii=False, indent=2)
            print(f"✓ データを {filepath} に保存しました")

        return json.dumps(self.collected_data, ensure_ascii=False, indent=2)


def test_collector():
    """テスト用関数"""
    from dotenv import load_dotenv
    load_dotenv()

    collector = DataCollector()

    # テスト用URL
    test_url = "https://www.kickstarter.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear"

    data = collector.collect_all(test_url, product_keywords=["MAXPRO", "fitness"])

    print("\n" + "=" * 60)
    print("📋 収集サマリー")
    print("=" * 60)
    for key, value in collector.get_summary().items():
        print(f"  {key}: {value}")

    # JSON出力
    collector.to_json("collected_data.json")


if __name__ == '__main__':
    test_collector()
