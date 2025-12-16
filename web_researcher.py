#!/usr/bin/env python3
"""
Web調査モジュール - 実Web検索 + Playwright + GPT-4o分析

ChatGPTのWeb検索と同等の精度を実現:
1. Kickstarterページを取得して製品情報を分析
2. 製品カテゴリ・キーワードを動的に抽出
3. 抽出したキーワードで各種検索を実行
4. GPT-4oで取得コンテンツを分析・構造化

※特定の業界・カテゴリにハードコードしない汎用設計
"""

import os
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from openai import OpenAI

# DuckDuckGo検索
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("⚠️ duckduckgo-search がインストールされていません: pip install duckduckgo-search")

# Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ playwright がインストールされていません")


class WebResearcher:
    """
    実Web検索を使用した情報収集クラス

    DuckDuckGo + Playwright + GPT-4oの組み合わせで
    ChatGPTのWeb検索と同等の精度を実現

    ※製品カテゴリは動的に判定（ハードコードしない）
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ OpenAI APIキーが設定されていません")

        self.browser = None
        self.context = None
        self.page = None

        # 製品分析結果（動的に設定）
        self.product_analysis = None

    def _init_browser(self):
        """Playwrightブラウザを初期化"""
        if not PLAYWRIGHT_AVAILABLE:
            return False

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            self.page = self.context.new_page()
            return True
        except Exception as e:
            print(f"  ⚠️ ブラウザ初期化エラー: {e}")
            return False

    def _close_browser(self):
        """ブラウザを終了"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except:
            pass

    def _search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict]:
        """DuckDuckGoで検索してURL一覧を取得"""
        if not DDGS_AVAILABLE:
            return []

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    }
                    for r in results
                ]
        except Exception as e:
            print(f"  ⚠️ DuckDuckGo検索エラー: {e}")
            return []

    def _fetch_page_content(self, url: str, timeout: int = 15000, wait_for_js: bool = False) -> Optional[str]:
        """Playwrightでページコンテンツを取得"""
        if not self.page:
            return None

        try:
            self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Makuakeなど動的コンテンツの場合は追加の待機
            if wait_for_js or "makuake.com" in url or "camp-fire.jp" in url:
                time.sleep(3)  # JavaScript読み込み待ち
                # スクロールしてコンテンツを読み込み
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
            else:
                time.sleep(1)

            # メインコンテンツを抽出（不要な要素を除外）
            content = self.page.evaluate("""
                () => {
                    // 不要な要素を削除
                    const removeSelectors = ['script', 'style', 'nav', 'header', 'footer',
                                            'aside', 'iframe', '.ad', '.advertisement',
                                            '.sidebar', '.menu', '.navigation'];
                    removeSelectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });

                    // メインコンテンツを取得
                    const main = document.querySelector('main, article, .content, #content, .main')
                                || document.body;
                    return main.innerText.substring(0, 15000);  // 15000文字制限
                }
            """)
            return content
        except PlaywrightTimeout:
            print(f"    ⚠️ タイムアウト: {url[:50]}...")
            return None
        except Exception as e:
            print(f"    ⚠️ ページ取得エラー ({url[:30]}...): {str(e)[:50]}")
            return None

    def _fetch_makuake_projects(self, search_term: str) -> List[Dict]:
        """Makuakeから実際のプロジェクトを取得"""
        if not self.page:
            return []

        projects = []
        search_url = f"https://www.makuake.com/discover/?keyword={search_term}"

        try:
            print(f"    → Makuake「{search_term}」を検索中（JS待機あり）...")
            self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3)

            # スクロールしてコンテンツを読み込み
            for _ in range(3):
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            # プロジェクトリンクを抽出
            project_links = self.page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href*="/project/"]').forEach(a => {
                        const href = a.href;
                        if (href.includes('/project/') && !links.includes(href)) {
                            links.push(href);
                        }
                    });
                    return links.slice(0, 10);
                }
            """)

            # プロジェクトカードの情報を抽出
            project_cards = self.page.evaluate("""
                () => {
                    const cards = [];
                    // プロジェクトカードを探す（複数のセレクタを試す）
                    const selectors = [
                        '[class*="project"]',
                        '[class*="card"]',
                        '[class*="item"]'
                    ];

                    for (const selector of selectors) {
                        document.querySelectorAll(selector).forEach(card => {
                            const text = card.innerText;
                            const link = card.querySelector('a[href*="/project/"]');
                            if (link && text.length > 50) {
                                cards.push({
                                    url: link.href,
                                    text: text.substring(0, 500)
                                });
                            }
                        });
                        if (cards.length > 0) break;
                    }
                    return cards.slice(0, 10);
                }
            """)

            if project_links:
                print(f"      ✓ {len(project_links)}件のプロジェクトリンク発見")
                for link in project_links[:5]:
                    projects.append({"url": link, "source": search_url})

            if project_cards:
                print(f"      ✓ {len(project_cards)}件のプロジェクト情報抽出")
                for card in project_cards:
                    # 既存のプロジェクトを更新
                    for p in projects:
                        if p.get("url") == card.get("url"):
                            p["preview_text"] = card.get("text", "")

        except Exception as e:
            print(f"      ⚠️ Makuake検索エラー: {str(e)[:50]}")

        return projects

    def _analyze_with_gpt(self, prompt: str, content: str, output_format: str) -> Dict:
        """GPT-4oでコンテンツを分析"""
        if not self.client:
            return {"error": "OpenAI APIキーが設定されていません"}

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """あなたはWeb情報の分析専門家です。
提供されたWebページのコンテンツから、指定された情報を抽出してJSON形式で回答してください。

重要なルール:
1. 提供されたコンテンツに記載されている情報のみを使用する
2. コンテンツにない情報は「情報なし」または null と記載
3. 推測や架空の情報は絶対に含めない
4. 数値データは可能な限り正確に抽出する
5. 情報源URLを必ず記載する"""
                    },
                    {
                        "role": "user",
                        "content": f"""以下のWebコンテンツから情報を抽出してください。

{prompt}

【Webコンテンツ】
{content[:12000]}

【出力形式】
{output_format}"""
                    }
                ],
                max_tokens=4000,
                temperature=0.2
            )

            response_text = response.choices[0].message.content
            return self._parse_json_response(response_text)
        except Exception as e:
            print(f"  ⚠️ GPT分析エラー: {e}")
            return {"error": str(e)}

    def _parse_json_response(self, response_text: str) -> Dict:
        """レスポンスからJSONを抽出"""
        if not response_text:
            return {}

        # JSONブロックを抽出
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        # 直接JSONとしてパース
        try:
            return json.loads(response_text)
        except:
            pass

        return {"raw_text": response_text}

    def research_product(self, kickstarter_url: str, product_name: str, product_description: str = "") -> Dict:
        """
        製品に関する包括的なWeb調査を実行
        """
        if not self.client:
            return {"error": "OpenAI APIキーが設定されていません"}

        print("\n" + "=" * 60)
        print("🔍 Web調査開始（実Web検索モード）")
        print("=" * 60)

        # ブラウザ初期化
        browser_ok = self._init_browser()
        if not browser_ok:
            print("  ⚠️ ブラウザ初期化失敗 - 検索結果のみで分析します")

        results = {
            "meta": {
                "researched_at": datetime.now().isoformat(),
                "product_name": product_name,
                "kickstarter_url": kickstarter_url,
                "search_mode": "real_web_search"
            },
            "product_analysis": {},
            "kickstarter_details": {},
            "official_info": {},
            "amazon_japan": {},
            "japan_cf_competitors": {},
            "regulations": {},
            "market_info": {}
        }

        try:
            # Step 1: Kickstarterページを取得して製品を分析
            print("\n[Step 1] Kickstarterページを取得・製品分析中...")
            kickstarter_content = ""
            if self.page:
                print(f"  → Kickstarterページを取得中...")
                kickstarter_content = self._fetch_page_content(kickstarter_url, timeout=20000)
                if kickstarter_content:
                    print(f"    ✓ {len(kickstarter_content):,}文字取得")

            # 製品分析（カテゴリ・キーワード抽出）
            self.product_analysis = self._analyze_product(
                kickstarter_content,
                product_name,
                product_description
            )
            results["product_analysis"] = self.product_analysis

            # 分析結果を表示
            category = self.product_analysis.get("category", "不明")
            keywords_jp = self.product_analysis.get("search_keywords_jp", [])
            print(f"  ✓ 製品カテゴリ: {category}")
            print(f"  ✓ 検索キーワード（日本語）: {keywords_jp}")

            # Step 2: Kickstarter詳細情報を抽出
            print("\n[Step 2] Kickstarter詳細情報を抽出中...")
            self.kickstarter_details = self._extract_kickstarter_details(
                kickstarter_content, kickstarter_url, product_name
            )
            results["kickstarter_details"] = self.kickstarter_details

            # Step 3: 公式サイト・SNS情報
            print("\n[Step 3] 公式サイト・SNS情報を調査中...")
            brand_name = self.product_analysis.get("brand_name", product_name.split()[0])
            results["official_info"] = self._research_official_sources(brand_name, product_name)

            # Step 4: Amazon.co.jp流通状況
            print("\n[Step 4] Amazon.co.jp流通状況を調査中...")
            results["amazon_japan"] = self._research_amazon_japan(brand_name, product_name)

            # Step 5: 日本CF競合製品
            print("\n[Step 5] 日本CF競合製品を調査中...")
            results["japan_cf_competitors"] = self._research_japan_cf_competitors()

            # Step 5.5: Amazon.co.jp カテゴリ競合製品
            print("\n[Step 5.5] Amazon.co.jpカテゴリ競合製品を調査中...")
            results["amazon_category_competitors"] = self._research_amazon_category_competitors()

            # Step 6: 規制情報
            print("\n[Step 6] 規制情報を調査中...")
            results["regulations"] = self._research_regulations()

            # Step 7: 市場情報
            print("\n[Step 7] 市場情報を調査中...")
            results["market_info"] = self._research_market_info()

        finally:
            self._close_browser()

        print("\n" + "=" * 60)
        print("✅ Web調査完了")
        print("=" * 60)

        return results

    def _analyze_product(self, kickstarter_content: str, product_name: str, product_description: str) -> Dict:
        """
        Kickstarterページから製品を分析し、カテゴリ・キーワードを動的に抽出
        """
        content = f"""
製品名: {product_name}
説明: {product_description}

【Kickstarterページコンテンツ】
{kickstarter_content[:8000] if kickstarter_content else "取得失敗"}
"""

        result = self._analyze_with_gpt(
            prompt="""この製品について詳細に分析してください。

【重要な指示】
1. 技術仕様（technical_specs）は、ページの内容から具体的な数値を抽出してください
   - 通信方式、通信距離、バッテリー持続時間、重量、サイズ等
   - ページに明示されている数値のみを記載し、推測は「不明」と記載

2. 直接競合ブランド（direct_competitor_brands）は、あなたの知識を活用して記載してください
   - この製品と同じカテゴリ・同じ機能を持つ市場の主要ブランドを3つ以上挙げる
   - ページに記載がなくても、製品タイプから推定して記載すること

3. 直接競合製品（direct_competitor_products）も具体的な製品名を記載
   - 同じ機能・同じターゲット層を持つ競合製品名を3つ以上挙げる
   - これらは日本市場での検索に使用されます""",
            content=content,
            output_format="""```json
{
    "brand_name": "ブランド名（製品名またはメーカー名から抽出）",
    "product_type": "製品の種類（具体的に記載）",
    "category": "大カテゴリ",
    "subcategory": "小カテゴリ（より具体的な分類）",
    "key_features": ["主要な特徴1", "特徴2", "特徴3"],
    "target_users": ["ターゲットユーザー1", "ターゲットユーザー2"],
    "technical_specs": {
        "connectivity": "通信方式（ページから抽出、不明なら「不明」）",
        "range": "通信距離（ページから抽出、不明なら「不明」）",
        "battery_life": "バッテリー持続時間（ページから抽出、不明なら「不明」）",
        "weight": "重量（ページから抽出、不明なら「不明」）",
        "size": "サイズ（ページから抽出、不明なら「不明」）",
        "compatibility": "対応機器（ページから抽出）",
        "other_specs": ["その他の仕様（ページから抽出した具体的数値）"]
    },
    "direct_competitor_brands": ["同カテゴリの競合ブランド名（3つ以上、あなたの知識から）"],
    "direct_competitor_products": ["競合の具体的製品名（3つ以上、あなたの知識から）"],
    "search_keywords_jp": ["日本語検索キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "search_keywords_en": ["英語検索キーワード1", "keyword2"],
    "competitor_search_terms": ["競合検索用語（日本語）"],
    "regulation_keywords": ["規制関連キーワード"],
    "has_electrical_components": true/false,
    "has_wireless_features": true/false,
    "has_battery": true/false,
    "campaign_year": "Kickstarterキャンペーン開始年（ページから読み取れる場合）"
}
```"""
        )

        # デフォルト値を設定
        if not isinstance(result, dict) or "category" not in result:
            result = {
                "brand_name": product_name.split()[0] if product_name else "Unknown",
                "product_type": "不明",
                "category": "その他",
                "subcategory": "不明",
                "key_features": [],
                "target_users": [],
                "technical_specs": {},
                "direct_competitor_brands": [],
                "direct_competitor_products": [],
                "search_keywords_jp": [product_name.split()[0] if product_name else "製品"],
                "search_keywords_en": [product_name.split()[0] if product_name else "product"],
                "competitor_search_terms": [],
                "regulation_keywords": [],
                "has_electrical_components": False,
                "has_wireless_features": False,
                "has_battery": False,
                "campaign_year": ""
            }

        return result

    def _extract_kickstarter_details(self, kickstarter_content: str, kickstarter_url: str, product_name: str) -> Dict:
        """Kickstarterの詳細情報を抽出（強化版：Kicktraq/BackerKit対応）"""
        content = kickstarter_content or ""
        sources = [kickstarter_url]
        extracted_stats = {}

        # URLからプロジェクトスラッグを抽出
        # 例: https://www.kickstarter.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear
        project_slug = ""
        if "/projects/" in kickstarter_url:
            parts = kickstarter_url.split("/projects/")[-1].rstrip("/")
            project_slug = parts  # 例: 726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear

        # ========================================
        # 戦略1: Kicktraq直接アクセス
        # ========================================
        if project_slug:
            kicktraq_url = f"https://www.kicktraq.com/projects/{project_slug}/"
            print(f"  → Kicktraq直接アクセス: {kicktraq_url[:60]}...")
            if self.page:
                kicktraq_content = self._fetch_page_content(kicktraq_url, timeout=15000)
                if kicktraq_content:
                    content += f"\n\n【Kicktraq】\nURL: {kicktraq_url}\n{kicktraq_content}"
                    sources.append(kicktraq_url)
                    print(f"    ✓ {len(kicktraq_content):,}文字取得")

                    # 達成率を直接抽出（Kicktraqは「XXX% funded」形式で表示することが多い）
                    percent_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*%\s*(?:funded|達成)', kicktraq_content, re.IGNORECASE)
                    if percent_match:
                        try:
                            extracted_stats["percent_funded"] = int(percent_match.group(1).replace(',', ''))
                            print(f"    ✓ Kicktraqから達成率抽出: {extracted_stats['percent_funded']}%")
                        except:
                            pass

        # ========================================
        # 戦略2: BackerKit直接アクセス
        # ========================================
        if project_slug:
            backerkit_url = f"https://www.backerkit.com/projects/{project_slug}"
            print(f"  → BackerKit直接アクセス: {backerkit_url[:60]}...")
            if self.page:
                backerkit_content = self._fetch_page_content(backerkit_url, timeout=15000)
                if backerkit_content:
                    content += f"\n\n【BackerKit】\nURL: {backerkit_url}\n{backerkit_content}"
                    sources.append(backerkit_url)
                    print(f"    ✓ {len(backerkit_content):,}文字取得")

                    # BackerKitからの統計抽出
                    # 調達額パターン: $143,110 pledged
                    funding_match = re.search(r'\$\s*([\d,]+)\s*(?:pledged|raised|funded)', backerkit_content, re.IGNORECASE)
                    if funding_match:
                        try:
                            extracted_stats["funding_amount_usd"] = int(funding_match.group(1).replace(',', ''))
                            print(f"    ✓ BackerKitから調達額抽出: ${extracted_stats['funding_amount_usd']:,}")
                        except:
                            pass

                    # バッカー数パターン: 388 backers
                    backers_match = re.search(r'([\d,]+)\s*(?:backers|supporters)', backerkit_content, re.IGNORECASE)
                    if backers_match:
                        try:
                            extracted_stats["backers_count"] = int(backers_match.group(1).replace(',', ''))
                            print(f"    ✓ BackerKitからバッカー数抽出: {extracted_stats['backers_count']}人")
                        except:
                            pass

                    # 平均Pledge: Average $368.84
                    avg_match = re.search(r'(?:average|avg)[^\d]*\$\s*([\d,.]+)', backerkit_content, re.IGNORECASE)
                    if avg_match:
                        try:
                            extracted_stats["average_pledge_usd"] = float(avg_match.group(1).replace(',', ''))
                            print(f"    ✓ BackerKitから平均Pledge抽出: ${extracted_stats['average_pledge_usd']}")
                        except:
                            pass

        # ========================================
        # 戦略3: DuckDuckGo検索でバックアップ
        # ========================================
        if "percent_funded" not in extracted_stats:
            print(f"  → DuckDuckGoで追加検索...")
            search_queries = [
                f'"{product_name}" Kicktraq funded',
                f'"{product_name}" BackerKit stats',
            ]
            for query in search_queries:
                search_results = self._search_duckduckgo(query, max_results=3)
                for r in search_results:
                    url = r.get("url", "")
                    if "kicktraq" in url.lower() or "backerkit" in url.lower():
                        if url not in sources:
                            print(f"    → {url[:50]}... を取得中...")
                            page_content = self._fetch_page_content(url)
                            if page_content:
                                content += f"\n\n【追加ソース】\nURL: {url}\n{page_content[:5000]}"
                                sources.append(url)

                                # 達成率を再度抽出試行
                                percent_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*%', page_content)
                                if percent_match and "percent_funded" not in extracted_stats:
                                    try:
                                        pct = int(percent_match.group(1).replace(',', ''))
                                        if pct > 0 and pct < 100000:  # 妥当な範囲
                                            extracted_stats["percent_funded"] = pct
                                            print(f"      ✓ 達成率抽出: {pct}%")
                                    except:
                                        pass
                time.sleep(0.5)

        if not content:
            return {"error": "コンテンツ取得失敗", "sources": sources}

        # ========================================
        # GPT分析
        # ========================================
        result = self._analyze_with_gpt(
            prompt=f"""製品名「{product_name}」のKickstarterキャンペーン情報を抽出してください。

【重要】
1. 達成率（percent_funded）は非常に重要。「XXX% funded」や「XXX%達成」から数値を抽出
2. 目標額（goal_amount_usd）がない場合、調達額と達成率から逆算を試みる
3. キャンペーン期間（開始日〜終了日）も抽出
4. 全ての数値データに出典URLを紐付ける""",
            content=content,
            output_format="""```json
{
    "funding_amount_usd": 数値または"情報なし",
    "goal_amount_usd": 数値または"情報なし",
    "percent_funded": 数値または"情報なし",
    "backers_count": 数値または"情報なし",
    "average_pledge_usd": 数値または"情報なし",
    "campaign_status": "active/successful/ended/情報なし",
    "campaign_start_date": "開始日または情報なし",
    "campaign_end_date": "終了日または情報なし",
    "campaign_duration_days": 数値または"情報なし",
    "price_tiers": [
        {"tier_name": "名前", "price_usd": 数値, "description": "説明", "backers": 数値}
    ],
    "product_specs": {
        "weight": "重量",
        "dimensions": "サイズ",
        "key_specs": {"仕様名": "値"},
        "features": ["特徴1", "特徴2"],
        "included_items": ["同梱品1", "同梱品2"]
    },
    "shipping_info": {
        "ships_to_japan": true/false/null,
        "estimated_delivery": "配送予定"
    },
    "data_sources": {
        "funding": "データソース（Kickstarter/Kicktraq/BackerKit）",
        "percent_funded": "データソース",
        "backers": "データソース"
    },
    "sources": ["情報源URL"]
}
```"""
        )

        # ========================================
        # 直接抽出した統計でGPT結果を補完
        # ========================================
        if isinstance(result, dict):
            result["sources"] = sources

            # 直接抽出した値でGPT結果を補完（GPTが取得できなかった場合）
            for key, value in extracted_stats.items():
                if key not in result or result.get(key) in [None, "情報なし", 0, "0"]:
                    result[key] = value
                    print(f"  → 直接抽出値で補完: {key} = {value}")

            funding = result.get('funding_amount_usd', '不明')
            backers = result.get('backers_count', '不明')
            percent = result.get('percent_funded', '不明')
            print(f"  ✓ 調達額: ${funding}")
            print(f"  ✓ バッカー数: {backers}人")
            print(f"  ✓ 達成率: {percent}%")

        return result

    def _research_official_sources(self, brand_name: str, product_name: str) -> Dict:
        """公式サイト・SNS情報を調査（強化版：製品スペック重視）"""
        content = ""
        sources = []
        official_url = ""
        product_page_url = ""

        # ========================================
        # ブランド名のバリエーション生成（カテゴリ非依存）
        # ========================================
        brand_variations = set()
        brand_lower = brand_name.lower()
        brand_no_space = brand_lower.replace(" ", "")
        brand_hyphen = brand_lower.replace(" ", "-")
        brand_underscore = brand_lower.replace(" ", "_")

        brand_variations.add(brand_no_space)  # alpinelabs
        brand_variations.add(brand_hyphen)     # alpine-labs
        brand_variations.add(brand_underscore) # alpine_labs

        # 一般的な略語・変換パターン
        common_transforms = [
            ("labs", "laboratories"), ("lab", "laboratory"),
            ("tech", "technology"), ("technologies", "tech"),
            ("co", "company"), ("inc", ""),
            ("llc", ""), ("ltd", ""),
        ]
        for old, new in common_transforms:
            if old in brand_no_space:
                brand_variations.add(brand_no_space.replace(old, new))
            if new and new in brand_no_space:
                brand_variations.add(brand_no_space.replace(new, old))

        # 各単語を追加
        brand_words = brand_lower.split()
        for word in brand_words:
            if len(word) > 3:  # 短すぎる単語は除外
                brand_variations.add(word)

        # 製品名からもバリエーション生成
        product_words = product_name.lower().split() if product_name else []
        product_first = product_words[0] if product_words else ""

        brand_variations = list(brand_variations)
        print(f"  ブランド名バリエーション: {brand_variations[:5]}")

        # ========================================
        # 戦略1: 直接ドメインアクセス（推測）
        # ========================================
        common_tlds = [".com", ".io", ".co", ".net", ".org"]
        direct_domains_to_try = []

        for var in brand_variations[:3]:  # 上位3バリエーション
            for tld in common_tlds:
                direct_domains_to_try.append(f"https://{var}{tld}")
                direct_domains_to_try.append(f"https://www.{var}{tld}")

        print(f"  → 直接ドメインアクセスを試行中...")
        official_found = False

        # 製品カテゴリに関連するキーワードを取得（検証用）
        category_keywords = []
        if hasattr(self, 'product_analysis') and self.product_analysis:
            category = self.product_analysis.get("category", "").lower()
            product_type = self.product_analysis.get("product_type", "").lower()
            if category:
                category_keywords.extend(category.split())
            if product_type:
                category_keywords.extend(product_type.split())
        # 製品名からもキーワードを追加
        if product_name:
            category_keywords.extend([w.lower() for w in product_name.split()[:3]])
        # 一般的な製品関連キーワード（異なる業種を除外するため）
        exclude_industries = ["supplement", "health", "vitamin", "nutrition", "fitness", "food", "pharma", "medicine", "medical", "drug"]

        potential_official_sites = []  # 候補を収集

        for domain in direct_domains_to_try[:8]:  # 最大8ドメイン
            try:
                if self.page:
                    self.page.goto(domain, timeout=8000)
                    time.sleep(1)
                    page_title = self.page.title().lower()
                    page_url = self.page.url.lower()

                    # ブランド名がタイトルまたはURLに含まれているか確認
                    if any(var in page_title or var in page_url for var in brand_variations):
                        page_content = self.page.inner_text("body")[:8000]
                        if page_content and len(page_content) > 500:
                            page_content_lower = page_content.lower()

                            # 異なる業種のサイトかチェック
                            is_different_industry = any(ind in page_content_lower for ind in exclude_industries)

                            # 製品カテゴリのキーワードがあるかチェック
                            has_category_match = any(kw in page_content_lower for kw in category_keywords if len(kw) > 2)

                            if is_different_industry and not has_category_match:
                                print(f"    ⚠ 異なる業種のサイトをスキップ: {domain}")
                                continue  # このサイトはスキップ

                            print(f"    ✓ 公式サイト発見（直接アクセス）: {domain}")
                            content += f"\n【公式サイト】\nURL: {domain}\n{page_content[:5000]}\n"
                            sources.append(domain)
                            official_url = domain
                            official_found = True
                            break
            except:
                pass

        # ========================================
        # 戦略2: 検索エンジンで公式サイトを検索
        # ========================================
        if not official_found:
            official_queries = [
                f"{brand_name} official site",
                f"{brand_name} official website",
                f'"{brand_name}" company',
                f"{brand_name} {product_first}" if product_first else f"{brand_name}",
            ]

            print(f"  → 「{brand_name} official site」を検索中...")

            for query in official_queries[:3]:
                search_results = self._search_duckduckgo(query, max_results=10)
                for r in search_results:
                    url_lower = r["url"].lower()
                    # ブランド名のいずれかのバリエーションがURLに含まれているかチェック
                    if any(x in url_lower for x in brand_variations):
                        # SNSやマーケットプレイスを除外
                        exclude_domains = [
                            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
                            "amazon", "ebay", "youtube.com", "reddit.com", "wikipedia.org",
                            "kickstarter.com", "indiegogo.com", "makuake.com"
                        ]
                        if not any(x in url_lower for x in exclude_domains):
                            print(f"  → 公式サイト候補発見: {r['url'][:60]}...")
                            page_content = self._fetch_page_content(r["url"])
                            if page_content and len(page_content) > 500:
                                content += f"\n【公式サイト】\nURL: {r['url']}\n{page_content[:5000]}\n"
                                sources.append(r["url"])
                                official_url = r["url"]
                                print(f"    ✓ {len(page_content):,}文字取得")
                                official_found = True
                                break
                if official_found:
                    break

        # ========================================
        # 戦略2: 製品ページを直接検索・取得（スペック情報重視）
        # ========================================
        product_first_word = product_name.split()[0] if product_name else ""
        print(f"  → 「{brand_name} {product_first_word} product specifications」を検索中...")
        product_queries = [
            f"{brand_name} {product_first_word} product page",
            f"{brand_name} {product_first_word} specifications",
            f'site:{official_url.split("/")[2]} {product_first_word}' if official_url else f"{brand_name} {product_first_word}",
        ]

        for query in product_queries[:2]:
            product_results = self._search_duckduckgo(query, max_results=3)
            for r in product_results:
                url_lower = r["url"].lower()
                # 製品ページらしいURLを優先
                if any(x in url_lower for x in ["/products/", "/product/", product_first_word.lower()]):
                    if r["url"] not in sources:
                        print(f"  → 製品ページ発見: {r['url'][:60]}...")
                        page_content = self._fetch_page_content(r["url"], timeout=15000, wait_for_js=True)
                        if page_content:
                            content += f"\n【製品ページ（スペック情報）】\nURL: {r['url']}\n{page_content[:8000]}\n"
                            sources.append(r["url"])
                            product_page_url = r["url"]
                            print(f"    ✓ {len(page_content):,}文字取得")
                            break
            if product_page_url:
                break

        # Instagram検索
        print(f"  → 「{brand_name} Instagram」を検索中...")
        ig_results = self._search_duckduckgo(f"{brand_name} Instagram", max_results=2)
        for r in ig_results:
            if "instagram.com" in r["url"]:
                content += f"\n【Instagram】\nURL: {r['url']}\n{r['snippet']}\n"
                sources.append(r["url"])
                break

        # YouTube検索
        print(f"  → 「{brand_name} {product_name} YouTube」を検索中...")
        yt_results = self._search_duckduckgo(f"{brand_name} {product_name} review YouTube", max_results=2)
        for r in yt_results:
            if "youtube.com" in r["url"]:
                content += f"\n【YouTube】\nURL: {r['url']}\nタイトル: {r['title']}\n{r['snippet']}\n"
                sources.append(r["url"])
                break

        # ========================================
        # 戦略3: Kickstarterページからの追加スペック情報
        # ========================================
        # （第三者レビューは取得困難なため削除）

        if not content:
            return {"error": "公式情報が見つかりませんでした", "sources": sources}

        result = self._analyze_with_gpt(
            prompt=f"「{brand_name}」ブランドの公式サイト・製品ページから製品情報を詳細に抽出してください。特に技術スペックは可能な限り具体的な数値で抽出してください。",
            content=content,
            output_format="""```json
{
    "official_website": {
        "url": "公式サイトURL",
        "product_page_url": "製品ページURL（あれば）",
        "msrp_usd": 数値またはnull,
        "msrp_local_currency": {"amount": 数値, "currency": "通貨コード"},
        "product_features": ["主要特徴1", "主要特徴2", "主要特徴3"]
    },
    "tech_specs": {
        "connectivity": "通信方式（例: Bluetooth 4.0 BLE, WiFi, USB等）",
        "wireless_range": "通信距離（例: 100ft / 30m）",
        "battery_life": "バッテリー持続時間（例: 12時間, 500回シャッター等）",
        "battery_type": "バッテリー種別（例: CR2032, 内蔵リチウム, 単4電池等）",
        "weight": "重量（例: 36g, 1.3oz等）",
        "dimensions": "寸法（例: 50x30x10mm）",
        "compatibility": "対応機種/OS（例: Canon, Nikon, iOS/Android等）",
        "water_resistance": "防水性能（例: IPX4, 生活防水等）",
        "app_features": ["アプリ機能1", "アプリ機能2"],
        "other_specs": {"その他仕様名": "値"}
    },
    "social_media": {
        "instagram": {"url": "URL", "followers": 数値またはnull},
        "youtube": {"url": "URL", "channel_name": "チャンネル名"},
        "twitter": {"url": "URL", "followers": 数値またはnull}
    },
    "brand_info": {
        "company_name": "会社名",
        "country": "本社所在国",
        "founded": "設立年またはnull"
    },
    "pricing_info": {
        "kickstarter_price_usd": "Kickstarter価格（記載があれば）",
        "retail_price_usd": "小売価格",
        "price_source_url": "価格情報の出典URL"
    },
    "sources": ["情報源URL（実際に情報を取得したURLのみ）"]
}
```"""
        )

        if isinstance(result, dict):
            result["sources"] = sources
            if result.get("official_website", {}).get("msrp_usd"):
                print(f"  ✓ 公式MSRP: ${result['official_website']['msrp_usd']}")

        return result

    def _research_amazon_japan(self, brand_name: str, product_name: str) -> Dict:
        """Amazon.co.jpでの流通状況を調査（強化版）"""
        content = ""
        sources = []
        product_pages_found = []

        # ========================================
        # 戦略1: 複数のAmazon検索クエリを試す
        # ========================================
        # 製品名の最初の単語のみ抽出（長すぎるクエリを防ぐ）
        product_first_word = product_name.split()[0] if product_name else ""

        amazon_search_queries = [
            brand_name,  # ブランド名のみ（例: "Alpine Labs"）
        ]

        # ブランド名 + 製品名（最初の単語）を追加
        if product_first_word and brand_name:
            amazon_search_queries.append(f"{brand_name} {product_first_word}")

        # カテゴリ情報があれば追加（より精度の高い検索）
        if self.product_analysis:
            category = self.product_analysis.get("category", "")
            product_type = self.product_analysis.get("product_type", "")
            # ブランド名 + 製品タイプ（例: "Alpine Labs カメラコントローラー"）
            if product_type and brand_name:
                amazon_search_queries.append(f"{brand_name} {product_type}")
            # ブランド名 + カテゴリ（例: "Alpine Labs カメラアクセサリー"）
            if category and brand_name and category != product_type:
                amazon_search_queries.append(f"{brand_name} {category}")

        # 重複除去
        amazon_search_queries = list(dict.fromkeys([q for q in amazon_search_queries if q and q.strip()]))[:4]

        print(f"  → Amazon.co.jp検索（{len(amazon_search_queries)}クエリ）...")
        for query in amazon_search_queries:
            amazon_url = f"https://www.amazon.co.jp/s?k={query}"
            print(f"    → 検索: {query}")

            if self.page:
                page_content = self._fetch_page_content(amazon_url, timeout=20000, wait_for_js=True)
                if page_content:
                    content += f"\n【Amazon.co.jp検索「{query}」】\nURL: {amazon_url}\n{page_content}\n"
                    sources.append(amazon_url)
                    print(f"      ✓ {len(page_content):,}文字取得")

                    # 商品リンクを抽出
                    product_links = self.page.evaluate("""
                        () => {
                            const links = [];
                            document.querySelectorAll('a[href*="/dp/"]').forEach(a => {
                                const href = a.href;
                                if (href.includes('/dp/') && !links.some(l => l.url === href)) {
                                    const title = a.innerText.trim().substring(0, 100);
                                    if (title.length > 10) {
                                        links.push({url: href, title: title});
                                    }
                                }
                            });
                            return links.slice(0, 5);
                        }
                    """)
                    if product_links:
                        for pl in product_links:
                            if pl.get("url") and pl["url"] not in [p.get("url") for p in product_pages_found]:
                                product_pages_found.append(pl)
                                print(f"      → 商品発見: {pl.get('title', '')[:40]}...")
                time.sleep(1)

        # ========================================
        # 戦略2: DuckDuckGoでAmazon商品を検索
        # ========================================
        print(f"  → DuckDuckGoでAmazon.co.jp商品を検索中...")
        ddg_queries = [
            f"{brand_name} site:amazon.co.jp",
            f'"{brand_name}" site:amazon.co.jp/dp',
        ]
        if product_name and product_name != brand_name:
            ddg_queries.append(f"{product_name} site:amazon.co.jp")

        for query in ddg_queries[:3]:
            print(f"    → 検索: {query}")
            search_results = self._search_duckduckgo(query, max_results=10)
            for r in search_results:
                url = r.get("url", "")
                if "amazon.co.jp" in url:
                    content += f"\n【DuckDuckGo検索結果】\nタイトル: {r['title']}\nURL: {url}\n{r['snippet']}\n"
                    sources.append(url)
                    # 商品ページ（/dp/）の場合は保存
                    if "/dp/" in url and url not in [p.get("url") for p in product_pages_found]:
                        product_pages_found.append({"url": url, "title": r.get("title", "")})
            time.sleep(0.5)

        # ========================================
        # 戦略3: 見つかった商品ページを実際に取得
        # ========================================
        if product_pages_found and self.page:
            print(f"  → Amazon商品ページ詳細取得（{len(product_pages_found)}件）...")
            for idx, product in enumerate(product_pages_found[:5]):
                url = product.get("url", "")
                if url:
                    print(f"    → {url[:60]}...")
                    page_content = self._fetch_page_content(url, timeout=15000)
                    if page_content:
                        content += f"\n【Amazon商品ページ】\nURL: {url}\n{page_content[:5000]}\n"
                        print(f"      ✓ {len(page_content):,}文字取得")
                    time.sleep(1)

        # 発見した商品ページ数をログ出力
        print(f"  → 発見商品ページ数: {len(product_pages_found)}件")

        if not content:
            return {
                "brand_exists_in_japan": False,
                "same_product_found": False,
                "products_found": [],
                "product_pages_found": [],
                "market_analysis": "",
                "search_queries_used": amazon_search_queries,
                "sources": sources
            }

        result = self._analyze_with_gpt(
            prompt=f"""「{brand_name}」および「{product_name}」のAmazon.co.jpでの流通状況を分析してください。

【重要】
1. ブランド名「{brand_name}」を含む製品が1つでもあれば brand_exists_in_japan = true
2. 製品名の一部が一致する製品（例: SmartConnect, Pro, Airなど別バリエーション）も products_found に含める
3. 同一ブランドの別製品も重要な情報として記録する
4. 価格は「¥」や「円」の後の数値を抽出する""",
            content=content,
            output_format="""```json
{
    "brand_exists_in_japan": true/false,
    "same_product_found": true/false,
    "same_product_details": {
        "product_name": "製品名",
        "price_jpy": 数値またはnull,
        "url": "URL"
    },
    "other_brand_products": [
        {
            "product_name": "同ブランドの別製品名",
            "price_jpy": 数値またはnull,
            "url": "Amazon URL",
            "notes": "関連性・違い"
        }
    ],
    "products_found": [
        {
            "product_name": "製品名",
            "price_jpy": 数値またはnull,
            "review_count": 数値またはnull,
            "rating": 数値またはnull,
            "seller_type": "公式/並行輸入/第三者/不明",
            "url": "Amazon URL"
        }
    ],
    "market_analysis": "日本市場での流通状況の分析",
    "implications_for_exclusive_deal": "独占契約への影響（既存流通があると独占は困難など）",
    "sources": ["情報源URL"]
}
```"""
        )

        if isinstance(result, dict):
            # 発見した商品ページ情報を追加
            result["product_pages_found"] = product_pages_found
            result["search_queries_used"] = amazon_search_queries
            result["sources"] = list(set(sources))

            exists = result.get("brand_exists_in_japan", False)
            same_found = result.get("same_product_found", False)
            products = result.get("products_found", [])
            other_products = result.get("other_brand_products", [])
            print(f"  ✓ ブランド日本流通: {'あり' if exists else 'なし'}")
            print(f"  ✓ 同一製品: {'あり' if same_found else 'なし'}")
            print(f"  ✓ 発見製品数: {len(products)}件")
            if other_products:
                print(f"  ✓ 同ブランド別製品: {len(other_products)}件")

        return result

    def _research_japan_cf_competitors(self) -> Dict:
        """
        日本CFでの競合製品を徹底調査

        複数の検索戦略を使用し、データが見つかるまで粘り強く検索する。
        全てのデータに出典URLを紐付ける。
        """
        if not self.product_analysis:
            return {"error": "製品分析が完了していません"}

        # 動的に取得したキーワードを使用
        keywords_jp = self.product_analysis.get("search_keywords_jp", [])
        competitor_terms = self.product_analysis.get("competitor_search_terms", [])
        category = self.product_analysis.get("category", "")
        product_type = self.product_analysis.get("product_type", "")
        brand_name = self.product_analysis.get("brand_name", "")
        key_features = self.product_analysis.get("key_features", [])
        # 直接競合ブランド/製品名を取得
        direct_competitor_brands = self.product_analysis.get("direct_competitor_brands", [])
        direct_competitor_products = self.product_analysis.get("direct_competitor_products", [])

        print(f"  カテゴリ: {category}")
        print(f"  製品タイプ: {product_type}")

        content = ""
        sources = []
        project_urls = set()
        competitors_data = []

        # ========================================
        # 戦略1: Makuake直接検索（プロジェクトURL抽出）
        # ========================================
        print("\n  [戦略1] Makuakeプロジェクト検索（JavaScript待機あり）...")

        # 動的に抽出したキーワードのみを使用（ハードコード禁止）
        makuake_search_terms = []
        if category:
            makuake_search_terms.append(category)
        if product_type:
            makuake_search_terms.append(product_type)
        # 製品分析から取得した検索キーワードを追加
        makuake_search_terms.extend(keywords_jp[:3])
        # 競合検索用語を追加
        makuake_search_terms.extend(competitor_terms[:2])
        # 重複除去・空文字除去・最大5件
        makuake_search_terms = list(dict.fromkeys([t for t in makuake_search_terms if t]))[:5]

        print(f"  検索キーワード: {makuake_search_terms}")

        for term in makuake_search_terms:
            if self.page:
                # 新しいMakuakeプロジェクト取得関数を使用
                found_projects = self._fetch_makuake_projects(term)
                for p in found_projects:
                    if p.get("url") and p["url"] not in project_urls:
                        project_urls.add(p["url"])
                        sources.append(p["url"])
                        if p.get("preview_text"):
                            content += f"\n【Makuake検索「{term}」で発見】\nURL: {p['url']}\nプレビュー: {p['preview_text']}\n"
                time.sleep(1)

        # ========================================
        # 戦略2: DuckDuckGoでMakuakeプロジェクト検索
        # ========================================
        print("\n  [戦略2] DuckDuckGoでMakuakeプロジェクト検索...")

        # 動的に抽出したキーワードのみを使用（ハードコード禁止）
        ddg_queries = []
        if category:
            ddg_queries.append(f"{category} site:makuake.com")
        if product_type:
            ddg_queries.append(f"{product_type} site:makuake.com")
        # 製品分析から取得したキーワードでクエリを生成
        for kw in keywords_jp[:3]:
            if kw and kw != category and kw != product_type:
                ddg_queries.append(f"{kw} site:makuake.com")
        # 競合検索用語でクエリを生成
        for term in competitor_terms[:2]:
            if term:
                ddg_queries.append(f"{term} site:makuake.com")
        # 重複除去・最大5件
        ddg_queries = list(dict.fromkeys(ddg_queries))[:5]

        for query in ddg_queries:
            print(f"    → 検索: {query}")
            results = self._search_duckduckgo(query, max_results=10)
            for r in results:
                url = r.get("url", "")
                if "makuake.com/project" in url and url not in project_urls:
                    project_urls.add(url)
                    content += f"\n【Makuake検索結果】\nタイトル: {r['title']}\nURL: {url}\n説明: {r['snippet']}\n"
                    sources.append(url)
            time.sleep(0.5)

        # ========================================
        # 戦略3: 見つかったプロジェクトページを実際に取得
        # ========================================
        print(f"\n  [戦略3] プロジェクトページ詳細取得（{len(project_urls)}件）...")

        fetched_projects = 0
        for url in list(project_urls)[:8]:  # 最大8件
            if self.page:
                print(f"    → {url[:60]}...")
                page_content = self._fetch_page_content(url, timeout=15000)
                if page_content and len(page_content) > 500:
                    content += f"\n【Makuakeプロジェクト詳細】\nURL: {url}\n{page_content[:8000]}\n"
                    fetched_projects += 1
                    print(f"      ✓ {len(page_content):,}文字取得")

                    # プロジェクト情報を抽出
                    project_info = self._extract_project_info_from_page(page_content, url, "Makuake")
                    if project_info:
                        competitors_data.append(project_info)
                time.sleep(1)

        print(f"    ✓ {fetched_projects}件のプロジェクトページを取得")

        # ========================================
        # 戦略4: CAMPFIRE検索
        # ========================================
        print("\n  [戦略4] CAMPFIRE検索...")

        # 動的に抽出したキーワードのみを使用（ハードコード禁止）
        cf_queries = []
        if category:
            cf_queries.append(f"{category} site:camp-fire.jp")
        if product_type:
            cf_queries.append(f"{product_type} site:camp-fire.jp")
        # 製品分析から取得したキーワードでクエリを生成
        for kw in keywords_jp[:2]:
            if kw and kw != category and kw != product_type:
                cf_queries.append(f"{kw} site:camp-fire.jp")
        # 重複除去・最大4件
        cf_queries = list(dict.fromkeys(cf_queries))[:4]

        cf_project_urls = set()
        for query in cf_queries:
            print(f"    → 検索: {query}")
            results = self._search_duckduckgo(query, max_results=5)
            for r in results:
                url = r.get("url", "")
                if "camp-fire.jp/projects" in url and url not in cf_project_urls:
                    cf_project_urls.add(url)
                    content += f"\n【CAMPFIRE検索結果】\nタイトル: {r['title']}\nURL: {url}\n説明: {r['snippet']}\n"
                    sources.append(url)

        # CAMPFIREプロジェクトページを取得
        for url in list(cf_project_urls)[:3]:
            if self.page:
                print(f"    → {url[:60]}...")
                page_content = self._fetch_page_content(url, timeout=15000)
                if page_content and len(page_content) > 500:
                    content += f"\n【CAMPFIREプロジェクト詳細】\nURL: {url}\n{page_content[:5000]}\n"
                    project_info = self._extract_project_info_from_page(page_content, url, "CAMPFIRE")
                    if project_info:
                        competitors_data.append(project_info)
                time.sleep(1)

        # ========================================
        # 戦略5: 同一ブランド検索
        # ========================================
        if brand_name:
            print(f"\n  [戦略5] 同一ブランド「{brand_name}」検索...")
            brand_queries = [
                f"{brand_name} site:makuake.com",
                f"{brand_name} site:camp-fire.jp",
                f"{brand_name} クラウドファンディング 日本",
            ]
            for query in brand_queries:
                print(f"    → 検索: {query}")
                results = self._search_duckduckgo(query, max_results=5)
                for r in results:
                    content += f"\n【ブランド検索結果】\nクエリ: {query}\nタイトル: {r['title']}\nURL: {r['url']}\n説明: {r['snippet']}\n"
                    if r['url'] not in sources:
                        sources.append(r['url'])

        # ========================================
        # 戦略6: 直接競合ブランド/製品検索（重要な追加）
        # ========================================
        # 無効な値をフィルタリング
        invalid_values = ["情報なし", "不明", "なし", "N/A", "", None]
        valid_brands = [b for b in direct_competitor_brands if b and b not in invalid_values]
        valid_products = [p for p in direct_competitor_products if p and p not in invalid_values]

        if valid_brands or valid_products:
            print(f"\n  [戦略6] 直接競合ブランド検索...")
            print(f"    競合ブランド: {valid_brands}")
            print(f"    競合製品: {valid_products}")

            # 競合ブランドをMakuake/CAMPFIRE/Amazonで検索
            all_competitors = list(set(valid_brands + valid_products))[:6]
            for competitor in all_competitors:
                if not competitor or competitor in invalid_values:
                    continue
                # Makuake検索
                print(f"    → Makuake: {competitor}")
                mak_results = self._search_duckduckgo(f"{competitor} site:makuake.com", max_results=3)
                for r in mak_results:
                    if "makuake.com/project" in r["url"]:
                        content += f"\n【直接競合: {competitor}】\nプラットフォーム: Makuake\nタイトル: {r['title']}\nURL: {r['url']}\n説明: {r['snippet']}\n"
                        if r['url'] not in sources:
                            sources.append(r['url'])
                        # ページ詳細取得
                        page_content = self._fetch_page_content(r['url'], timeout=10000)
                        if page_content:
                            content += f"詳細: {page_content[:2000]}\n"
                            project_info = self._extract_project_info_from_page(page_content, r['url'], "Makuake")
                            if project_info:
                                project_info["is_direct_competitor"] = True
                                project_info["competitor_brand"] = competitor
                                competitors_data.append(project_info)

                # Amazon.co.jp検索
                print(f"    → Amazon.co.jp: {competitor}")
                amz_results = self._search_duckduckgo(f"{competitor} site:amazon.co.jp", max_results=3)
                for r in amz_results:
                    if "amazon.co.jp" in r["url"]:
                        content += f"\n【直接競合Amazon: {competitor}】\nURL: {r['url']}\nタイトル: {r['title']}\n価格情報: {r['snippet']}\n"
                        if r['url'] not in sources:
                            sources.append(r['url'])

        # ========================================
        # GPTで分析（実データのみ使用を厳格に指示）
        # ========================================
        print(f"\n  [分析] 取得データをGPT-4oで分析中...")
        print(f"    取得コンテンツ: {len(content):,}文字")
        print(f"    ソース数: {len(sources)}件")

        if len(content) < 500:
            return {
                "same_product_found": {"makuake": False, "campfire": False, "details": "十分なデータが取得できませんでした"},
                "competitors": competitors_data,
                "competitors_count": len(competitors_data),
                "category_analysis": "データ不足のため分析できません",
                "differentiation_points": [],
                "data_reliability": "低",
                "search_attempts": {
                    "makuake_direct": len(makuake_search_terms),
                    "ddg_makuake": len(ddg_queries),
                    "project_pages_fetched": fetched_projects,
                    "campfire": len(cf_queries)
                },
                "sources": list(set(sources))
            }

        result = self._analyze_with_gpt(
            prompt=f"""「{product_type}」（{category}カテゴリ）の日本クラウドファンディング競合製品を分析してください。

【重要ルール】
1. 提供されたWebコンテンツに実際に記載されている情報のみを使用すること
2. 推測や一般知識での補完は絶対に禁止
3. データがない項目は「データなし」「不明」と正直に記載
4. 各データに対応する出典URLを必ず記載
5. 競合製品は実際にコンテンツに登場するもののみをリストアップ""",
            content=content,
            output_format="""```json
{
    "same_product_found": {
        "makuake": true/false,
        "campfire": true/false,
        "details": "根拠となるURLと説明"
    },
    "competitors": [
        {
            "platform": "Makuake/CAMPFIRE",
            "product_name": "製品名（コンテンツから抽出した実際の名前）",
            "url": "プロジェクトURL",
            "funding_amount_jpy": "調達額（コンテンツに記載があれば数値、なければ「不明」）",
            "backers_count": "支援者数（コンテンツに記載があれば数値、なければ「不明」）",
            "price_jpy": "支援価格（コンテンツに記載があれば数値、なければ「不明」）",
            "features": "特徴（コンテンツから抽出）",
            "source_url": "この情報の出典URL"
        }
    ],
    "category_analysis": "カテゴリの分析（実データに基づく場合のみ、なければ「データ不足」）",
    "differentiation_points": ["コンテンツから読み取れる差別化ポイント"],
    "data_reliability": "高（プロジェクトページ取得成功）/中（検索結果のみ）/低（データ不足）",
    "sources": ["実際に使用した情報源URL一覧"]
}
```"""
        )

        if isinstance(result, dict):
            # 直接抽出したデータとGPT分析結果をマージ
            if competitors_data and not result.get("competitors"):
                result["competitors"] = competitors_data

            result["sources"] = list(set(sources))
            result["search_attempts"] = {
                "makuake_direct": len(makuake_search_terms),
                "ddg_makuake": len(ddg_queries),
                "project_pages_fetched": fetched_projects,
                "campfire": len(cf_queries),
                "total_sources": len(sources)
            }

            competitors = result.get("competitors", [])
            reliability = result.get("data_reliability", "不明")
            print(f"\n  ✓ 競合製品: {len(competitors)}件発見")
            print(f"  ✓ データ信頼度: {reliability}")
            print(f"  ✓ ソース数: {len(sources)}件")

        return result

    def _extract_project_info_from_page(self, page_content: str, url: str, platform: str) -> Optional[Dict]:
        """ページコンテンツからプロジェクト情報を直接抽出"""
        import re

        info = {
            "platform": platform,
            "url": url,
            "source_url": url
        }

        # 金額パターン（例: 1,234,567円、¥1,234,567）
        amount_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*円',
            r'¥\s*(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s*JPY',
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, page_content)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = int(amount_str)
                    if amount > 100000:  # 10万円以上なら調達額の可能性
                        info["funding_amount_jpy"] = amount
                        break
                except:
                    pass

        # 支援者数パターン
        backer_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*人',
            r'支援者\s*(\d{1,3}(?:,\d{3})*)',
        ]

        for pattern in backer_patterns:
            match = re.search(pattern, page_content)
            if match:
                try:
                    info["backers_count"] = int(match.group(1).replace(',', ''))
                    break
                except:
                    pass

        # 達成率パターン
        percent_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*%',
            r'達成率\s*(\d+)',
        ]

        for pattern in percent_patterns:
            match = re.search(pattern, page_content)
            if match:
                try:
                    info["percent_funded"] = int(match.group(1).replace(',', ''))
                    break
                except:
                    pass

        # 最低限の情報があれば返す
        if len(info) > 3:
            return info
        return None

    def _research_amazon_category_competitors(self) -> Dict:
        """
        Amazon.co.jpでカテゴリベースの競合製品を検索
        製品カテゴリに基づいて、日本市場の競合製品を調査し、
        製品名、価格、URLを取得する
        """
        if not self.product_analysis:
            return {"competitors": [], "sources": []}

        category = self.product_analysis.get("category", "")
        product_type = self.product_analysis.get("product_type", "")
        keywords_jp = self.product_analysis.get("search_keywords_jp", [])
        direct_competitor_brands = self.product_analysis.get("direct_competitor_brands", [])

        content = ""
        sources = []
        competitors = []

        print(f"\n[Amazon競合製品検索]")
        print(f"  カテゴリ: {category}")
        print(f"  製品タイプ: {product_type}")

        # ========================================
        # 価格フィルタリング設定（Kickstarter平均Pledgeベース）
        # 下限: 50%、上限: 300%
        # ========================================
        price_filter_min = None
        price_filter_max = None

        if hasattr(self, 'kickstarter_details') and self.kickstarter_details:
            avg_pledge_usd = self.kickstarter_details.get("average_pledge_usd", 0)
            exchange_rate = 155.0  # デフォルト為替レート（後で更新される可能性あり）

            if avg_pledge_usd and avg_pledge_usd > 0:
                avg_pledge_jpy = avg_pledge_usd * exchange_rate
                price_filter_min = int(avg_pledge_jpy * 0.5)   # 50%
                price_filter_max = int(avg_pledge_jpy * 3.0)   # 300%
                print(f"  価格フィルタ: ¥{price_filter_min:,}〜¥{price_filter_max:,}（Pledge ${avg_pledge_usd:.0f}の50%〜300%）")

        # ========================================
        # 戦略1: インテリジェントキーワード生成（カテゴリ非依存）
        # ========================================
        search_terms = []

        # 1. 直接競合製品名を最優先（具体的な製品名は最も精度が高い）
        direct_competitor_products = self.product_analysis.get("direct_competitor_products", [])
        for prod in direct_competitor_products[:3]:
            if prod and len(prod) > 2:
                search_terms.append(prod)

        # 2. 直接競合ブランド名
        for brand in direct_competitor_brands[:2]:
            if brand and len(brand) > 2:
                search_terms.append(brand)

        # 3. 製品の主要特徴を組み合わせた検索キーワード
        key_features = self.product_analysis.get("key_features", [])
        tech_specs = self.product_analysis.get("technical_specs", {})

        # 特徴的な技術キーワードを抽出
        tech_keywords = []
        if tech_specs.get("connectivity") and tech_specs["connectivity"] != "不明":
            tech_keywords.append(tech_specs["connectivity"].split()[0])  # 例: "Bluetooth"
        if tech_specs.get("compatibility"):
            compat = tech_specs["compatibility"]
            if isinstance(compat, str) and "不明" not in compat:
                tech_keywords.append(compat.split(",")[0].strip())  # 例: "DSLR"

        # 製品タイプと特徴を組み合わせる
        if product_type and tech_keywords:
            for tk in tech_keywords[:2]:
                combined = f"{tk} {product_type}"
                if combined not in search_terms:
                    search_terms.append(combined)

        # 4. 日本語キーワード（GPTが生成した検索向けキーワード）
        for kw in keywords_jp[:3]:
            if kw and kw not in search_terms:
                search_terms.append(kw)

        # 5. 製品タイプ単体（フォールバック）
        if product_type and product_type not in search_terms:
            search_terms.append(product_type)

        # 重複削除と上限設定
        search_terms = list(dict.fromkeys([t for t in search_terms if t and len(t) > 2]))[:6]
        print(f"  検索キーワード: {search_terms}")

        import re
        import urllib.parse

        # ========================================
        # Playwrightで直接Amazon.co.jpをスクレイピング
        # ========================================
        for term in search_terms[:3]:  # 最大3キーワード
            print(f"  → Amazon.co.jp直接検索: {term}")

            try:
                # Amazon検索URLを構築
                encoded_term = urllib.parse.quote(term)
                amazon_search_url = f"https://www.amazon.co.jp/s?k={encoded_term}"

                if self.page:
                    self.page.goto(amazon_search_url, timeout=30000)
                    time.sleep(2)  # ページ読み込み待機

                    # 製品カードを抽出（JavaScriptで実行）
                    products = self.page.evaluate("""
                        () => {
                            const results = [];
                            // 製品カードを取得（複数のセレクタを試す）
                            let cards = document.querySelectorAll('[data-component-type="s-search-result"]');
                            if (cards.length === 0) {
                                cards = document.querySelectorAll('.s-result-item[data-asin]');
                            }

                            Array.from(cards).slice(0, 15).forEach((card, idx) => {
                                try {
                                    // 製品名を取得（複数のセレクタを試す）
                                    let titleEl = card.querySelector('h2 a span');
                                    if (!titleEl) titleEl = card.querySelector('h2 span');
                                    if (!titleEl) titleEl = card.querySelector('.a-size-medium.a-color-base.a-text-normal');
                                    if (!titleEl) titleEl = card.querySelector('.a-size-base-plus.a-color-base.a-text-normal');
                                    const title = titleEl ? titleEl.textContent.trim() : '';

                                    // ASINを取得
                                    const asin = card.getAttribute('data-asin') || '';

                                    // URLを取得（ASINがあれば/dp/形式で構築）
                                    let url = '';
                                    if (asin) {
                                        url = 'https://www.amazon.co.jp/dp/' + asin;
                                    } else {
                                        const linkEl = card.querySelector('h2 a');
                                        url = linkEl ? linkEl.href : '';
                                    }

                                    // 価格を取得
                                    let priceEl = card.querySelector('.a-price .a-offscreen');
                                    if (!priceEl) priceEl = card.querySelector('.a-price-whole');
                                    let price = priceEl ? priceEl.textContent.trim() : '';

                                    // 整数価格（a-price-whole）の場合
                                    if (price && !price.includes('￥') && !price.includes('¥')) {
                                        price = '¥' + price;
                                    }

                                    if (title && url && url.includes('/dp/')) {
                                        results.push({
                                            title: title.substring(0, 100),
                                            url: url,
                                            price: price
                                        });
                                    }
                                } catch (e) {}
                            });

                            return results;
                        }
                    """)

                    print(f"    取得件数: {len(products)}件")

                    for prod in products:
                        title = prod.get("title", "")
                        url = prod.get("url", "")
                        price_str = prod.get("price", "")

                        # /dp/を含まないURLはスキップ（検索結果ページなど）
                        if "/dp/" not in url:
                            continue

                        # URLを正規化（/dp/を抽出）
                        dp_match = re.search(r'/dp/([A-Z0-9]+)', url)
                        if dp_match:
                            url = f"https://www.amazon.co.jp/dp/{dp_match.group(1)}"
                        else:
                            continue

                        # 価格を数値に変換
                        price = None
                        if price_str:
                            price_match = re.search(r'[¥￥]?\s*([\d,]+)', price_str)
                            if price_match:
                                try:
                                    price = int(price_match.group(1).replace(',', ''))
                                    if price < 100 or price > 1000000:
                                        price = None
                                except:
                                    pass

                        # 関連性フィルタ（明らかに無関係なカテゴリを除外）
                        # これはカテゴリ非依存：タイトルに含まれる特定キーワードで判定
                        title_lower = title.lower()
                        irrelevant_indicators = [
                            "車載", "カーナビ", "ドライブレコーダー", "車用", "バイク用",
                            "監視カメラ", "防犯カメラ", "セキュリティカメラ", "業務用監視",
                            "ペット用", "ベビーモニター", "介護", "見守り",
                            "rc ", "ラジコン", "ドローン用", "産業用",
                            "car ", "vehicle", "surveillance", "cctv", "security cam",
                            "baby monitor", "pet cam",
                        ]

                        # 検索キーワードに含まれている場合は除外しない（意図的な検索）
                        search_term_lower = term.lower()
                        is_irrelevant = any(ind in title_lower for ind in irrelevant_indicators)
                        is_intentional = any(ind in search_term_lower for ind in irrelevant_indicators)

                        if is_irrelevant and not is_intentional:
                            continue  # 無関係な製品をスキップ

                        competitor_info = {
                            "product_name": title[:80] if title else "不明",
                            "price_jpy": price,
                            "url": url,
                            "source": "Amazon.co.jp",
                            "search_term": term,
                            "is_product_page": True
                        }

                        # 価格フィルタリング（50%〜300%の範囲外は除外）
                        if price and price_filter_min and price_filter_max:
                            if price < price_filter_min or price > price_filter_max:
                                # 価格範囲外 - スキップ
                                continue

                        # 重複チェック（URLベース）
                        if url not in [c.get("url") for c in competitors]:
                            competitors.append(competitor_info)
                            content += f"\n【Amazon競合: {term}】\nタイトル: {title}\nURL: {url}\n価格: {price_str}\n"
                            sources.append(url)
                            price_display = f"¥{price:,}" if price else "価格不明"
                            print(f"    ✓ {title[:40]}... ({price_display})")

            except Exception as e:
                print(f"    ✗ エラー: {str(e)[:50]}")

            time.sleep(1)  # リクエスト間隔

        # ========================================
        # 戦略2: 発見した製品ページから詳細取得
        # ========================================
        if competitors and self.page:
            print(f"\n  → 競合製品ページ詳細取得（上位{min(5, len(competitors))}件）...")
            for idx, comp in enumerate(competitors[:5]):
                url = comp.get("url", "")
                if url:
                    page_content = self._fetch_page_content(url, timeout=15000)
                    if page_content:
                        # 価格を再抽出（より正確な情報）
                        import re
                        price_patterns = [
                            r'[¥￥]\s*([\d,]+)',
                            r'([\d,]+)\s*円',
                            r'参考価格.*?[¥￥]\s*([\d,]+)',
                        ]
                        for pattern in price_patterns:
                            match = re.search(pattern, page_content)
                            if match:
                                try:
                                    price = int(match.group(1).replace(',', ''))
                                    if 500 <= price <= 500000:  # 妥当な価格範囲
                                        comp["price_jpy"] = price
                                        break
                                except:
                                    pass

                        content += f"\n【Amazon製品詳細】\nURL: {url}\n{page_content[:3000]}\n"
                        print(f"      ✓ 詳細取得: ¥{comp.get('price_jpy', '不明'):,}" if comp.get("price_jpy") else f"      ✓ 詳細取得")
                    time.sleep(1)

        # 詳細取得後の価格フィルタリング（更新された価格が範囲外の場合は除外）
        if price_filter_min and price_filter_max and competitors:
            original_count = len(competitors)
            competitors = [
                c for c in competitors
                if not c.get("price_jpy") or (price_filter_min <= c["price_jpy"] <= price_filter_max)
            ]
            filtered_count = original_count - len(competitors)
            if filtered_count > 0:
                print(f"  ⚠️ 価格範囲外として{filtered_count}件を除外（残り{len(competitors)}件）")

        # GPTで競合分析
        if content:
            result = self._analyze_with_gpt(
                prompt=f"""「{product_type}」（{category}カテゴリ）の日本Amazon市場の競合製品を分析してください。

【重要ルール】
1. 提供されたWebコンテンツに実際に記載されている情報のみを使用
2. 価格は「¥」「円」の後の数値を正確に抽出
3. 製品名はタイトルから抽出（ブランド名＋製品名）
4. 推測や一般知識での補完は禁止""",
                content=content,
                output_format="""```json
{
    "amazon_competitors": [
        {
            "product_name": "製品名（ブランド名＋製品名）",
            "brand": "ブランド名",
            "price_jpy": 数値またはnull,
            "price_range": "価格帯（例: ¥4,000〜6,000）",
            "url": "Amazon URL",
            "key_features": ["特徴1", "特徴2"],
            "relevance": "高/中/低（対象製品との類似度）"
        }
    ],
    "market_price_range": {
        "low": 最低価格,
        "high": 最高価格,
        "average": 平均価格
    },
    "market_analysis": "日本市場の競合状況の分析",
    "sources": ["情報源URL"]
}
```"""
            )

            if isinstance(result, dict):
                result["raw_competitors"] = competitors
                result["sources"] = list(set(sources))

                # 低関連度の競合を除外（「低」は表示しない）
                original_comps = result.get('amazon_competitors', [])
                filtered_comps = [
                    c for c in original_comps
                    if c.get('relevance', '中') in ['高', '中']
                ]
                if len(filtered_comps) < len(original_comps):
                    print(f"    ⚠ 低関連度の製品を{len(original_comps) - len(filtered_comps)}件除外")
                result['amazon_competitors'] = filtered_comps

                print(f"\n  ✓ 競合製品: {len(result.get('amazon_competitors', []))}件分析完了")
                return result

        return {
            "amazon_competitors": competitors,
            "raw_competitors": competitors,
            "sources": sources,
            "market_analysis": "競合データ不足"
        }

    def _research_regulations(self) -> Dict:
        """規制情報を調査（動的キーワード使用）"""
        if not self.product_analysis:
            return {"error": "製品分析が完了していません"}

        content = ""
        sources = []

        # 製品特性に基づく規制検索
        has_electrical = self.product_analysis.get("has_electrical_components", False)
        has_wireless = self.product_analysis.get("has_wireless_features", False)
        has_battery = self.product_analysis.get("has_battery", False)
        product_type = self.product_analysis.get("product_type", "製品")
        regulation_keywords = self.product_analysis.get("regulation_keywords", [])

        # PSE情報検索（電気製品の場合）
        if has_electrical or has_battery or "電" in product_type:
            print(f"  → PSE（電気用品安全法）を検索中...")
            pse_results = self._search_duckduckgo("PSE 電気用品安全法 輸入 認証 費用 期間", max_results=3)
            for r in pse_results:
                content += f"\n【PSE情報】\nタイトル: {r['title']}\nURL: {r['url']}\n{r['snippet']}\n"
                sources.append(r["url"])
        else:
            print(f"  → PSE: 電気製品ではない可能性（スキップ）")

        # 技適情報検索（無線機能がある場合）
        if has_wireless or any(w in product_type.lower() for w in ["bluetooth", "wifi", "wireless", "ワイヤレス"]):
            print(f"  → 技適（技術基準適合証明）を検索中...")
            telec_results = self._search_duckduckgo("技適 Bluetooth WiFi 認証 費用 期間", max_results=3)
            for r in telec_results:
                content += f"\n【技適情報】\nタイトル: {r['title']}\nURL: {r['url']}\n{r['snippet']}\n"
                sources.append(r["url"])
        else:
            print(f"  → 技適: 無線機能なしの可能性（スキップ）")

        # 製品カテゴリに基づく規制検索
        category = self.product_analysis.get("category", "")
        if category:
            print(f"  → 「{category} 輸入 規制 認証」を検索中...")
            cat_results = self._search_duckduckgo(f"{category} 日本 輸入 規制 認証", max_results=2)
            for r in cat_results:
                content += f"\n【カテゴリ規制】\n{r['title']}\n{r['snippet']}\n"
                sources.append(r["url"])

        # 追加の規制キーワード検索
        for keyword in regulation_keywords[:2]:
            print(f"  → 「{keyword}」を検索中...")
            kw_results = self._search_duckduckgo(f"{keyword} 日本 輸入 認証", max_results=2)
            for r in kw_results:
                content += f"\n【{keyword}情報】\n{r['title']}\n{r['snippet']}\n"

        if not content:
            content = "規制に関する情報が見つかりませんでした。"

        result = self._analyze_with_gpt(
            prompt=f"「{product_type}」（電気: {has_electrical}, 無線: {has_wireless}, バッテリー: {has_battery}）の日本輸入に必要な規制・認証を分析してください。",
            content=content,
            output_format="""```json
{
    "pse": {
        "required": "必要/条件付き/不要/要確認",
        "reason": "判断理由",
        "type": "特定電気用品/特定電気用品以外/対象外",
        "estimated_cost_jpy": "費用目安",
        "estimated_period": "期間目安",
        "notes": "注意事項"
    },
    "telec": {
        "required": "必要/条件付き/不要/要確認",
        "reason": "判断理由",
        "estimated_cost_jpy": "費用目安",
        "estimated_period": "期間目安",
        "certified_module_option": "既認証モジュール使用可否",
        "notes": "注意事項"
    },
    "other_certifications": [
        {"name": "認証名", "required": "必要/不要/要確認", "reason": "理由"}
    ],
    "recommendation": "規制対応の推奨事項",
    "sources": ["情報源URL"]
}
```"""
        )

        if isinstance(result, dict):
            pse = result.get("pse", {}).get("required", "不明")
            telec = result.get("telec", {}).get("required", "不明")
            print(f"  ✓ PSE: {pse}")
            print(f"  ✓ 技適: {telec}")

        return result

    def _fetch_exchange_rate(self) -> Dict:
        """為替レートをAPIから直接取得"""
        import urllib.request
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                jpy_rate = data.get("rates", {}).get("JPY")
                if jpy_rate:
                    return {
                        "usd_jpy": round(jpy_rate, 2),
                        "source": "exchangerate-api.com",
                        "as_of": datetime.now().strftime("%Y-%m-%d")
                    }
        except Exception as e:
            print(f"    ⚠️ 為替API取得エラー: {e}")
        return {"usd_jpy": None, "source": "取得失敗", "as_of": None}

    def _research_market_info(self) -> Dict:
        """市場情報を調査（動的キーワード使用）"""
        if not self.product_analysis:
            return {"error": "製品分析が完了していません"}

        content = ""
        sources = []

        category = self.product_analysis.get("category", "")

        # 為替レートをAPIから直接取得
        print(f"  → 為替レート（USD/JPY）をAPIから取得中...")
        exchange_rate = self._fetch_exchange_rate()
        if exchange_rate.get("usd_jpy"):
            print(f"    ✓ 為替レート: $1 = ¥{exchange_rate['usd_jpy']}")
        content += f"\n【為替情報】\nUSD/JPY: {exchange_rate.get('usd_jpy', '不明')}\n"

        # Makuake手数料を公式情報から取得（固定値として設定）
        print(f"  → Makuake手数料情報...")
        # Makuakeの手数料は公開情報: 20%（税込22%）
        makuake_fees = {
            "platform_fee_percent": 20,
            "total_fee_percent": 22,
            "notes": "手数料20%（税込22%）。決済手数料込み。"
        }
        content += f"\n【Makuake手数料】\n手数料: {makuake_fees['total_fee_percent']}%（税込）\n"
        print(f"    ✓ 手数料: {makuake_fees['total_fee_percent']}%")

        # カテゴリ別市場検索（複数クエリで精度向上）
        if category:
            search_queries = [
                f"{category} 市場規模 日本 2024",
                f"{category} 業界 成長率 日本",
                f"日本 {category} マーケット レポート"
            ]

            for query in search_queries:
                print(f"  → 「{query}」を検索中...")
                market_results = self._search_duckduckgo(query, max_results=3)
                for r in market_results:
                    # 検索結果のページを実際に取得
                    if self.page and any(x in r["url"] for x in ["statista", "report", "research", "market", "news"]):
                        print(f"    → {r['url'][:50]}... を取得中...")
                        page_content = self._fetch_page_content(r["url"])
                        if page_content:
                            content += f"\n【市場レポート】\nURL: {r['url']}\n{page_content[:3000]}\n"
                            sources.append(r["url"])
                            print(f"      ✓ {len(page_content):,}文字取得")
                    else:
                        content += f"\n【市場情報検索結果】\nタイトル: {r['title']}\n{r['snippet']}\nURL: {r['url']}\n"
                        sources.append(r["url"])

        # 市場情報をGPTで分析
        result = self._analyze_with_gpt(
            prompt=f"「{category}」カテゴリの日本市場情報を抽出してください。数値データがある場合は必ず抽出してください。",
            content=content,
            output_format="""```json
{
    "market_info": {
        "category": "カテゴリ名",
        "market_size_jpy": "市場規模（具体的な数値があれば記載、なければ「データなし」）",
        "growth_rate": "成長率（具体的な数値があれば記載、なければ「データなし」）",
        "trends": ["トレンド1", "トレンド2"],
        "demand_outlook": "需要見通し",
        "data_reliability": "高/中/低（実データに基づくか推測か）"
    },
    "sources": ["情報源URL"]
}
```"""
        )

        # 為替レートとMakuake手数料は確定値として設定
        if isinstance(result, dict):
            result["exchange_rate"] = exchange_rate
            result["makuake_fees"] = makuake_fees
            result["sources"] = sources

            market = result.get("market_info", {})
            reliability = market.get("data_reliability", "不明")
            print(f"  ✓ 市場データ信頼度: {reliability}")
        else:
            result = {
                "exchange_rate": exchange_rate,
                "makuake_fees": makuake_fees,
                "market_info": {
                    "category": category,
                    "market_size_jpy": "データなし",
                    "growth_rate": "データなし",
                    "trends": [],
                    "demand_outlook": "データなし",
                    "data_reliability": "低"
                },
                "sources": sources
            }

        return result


def test_web_researcher():
    """テスト実行"""
    from dotenv import load_dotenv
    load_dotenv()

    researcher = WebResearcher()

    results = researcher.research_product(
        kickstarter_url="https://www.kickstarter.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear",
        product_name="MAXPRO Air",
        product_description="100+lbs of Resistance. Just 2.5lbs of Gear. A full-body workout anywhere you go."
    )

    # 結果を保存
    with open("web_research_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n結果をweb_research_results.jsonに保存しました")


if __name__ == "__main__":
    test_web_researcher()
