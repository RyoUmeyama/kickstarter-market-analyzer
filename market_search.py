#!/usr/bin/env python3
"""
市場調査用ウェブ検索モジュール
Makuake/CAMPFIREで類似製品を検索し、実在するデータを取得
ウェブスクレイピングによるリアルタイムデータ取得
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI


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

    def _fetch_kickstarter_info(self, kickstarter_url):
        """
        Kickstarterページから製品情報を取得

        Args:
            kickstarter_url (str): Kickstarter URL

        Returns:
            dict: 製品情報（title, description, category）
        """
        try:
            # /creator を除去してプロジェクトページを取得
            project_url = kickstarter_url.replace('/creator', '').split('?')[0]
            print(f"     Kickstarter製品情報を取得中...")

            response = self.session.get(project_url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # タイトル取得
            title = ""
            title_elem = soup.select_one('h2.project-name, meta[property="og:title"]')
            if title_elem:
                if title_elem.name == 'meta':
                    title = title_elem.get('content', '')
                else:
                    title = title_elem.get_text(strip=True)

            # 説明取得
            description = ""
            desc_elem = soup.select_one('meta[property="og:description"], meta[name="description"]')
            if desc_elem:
                description = desc_elem.get('content', '')

            # カテゴリ取得
            category = ""
            category_elem = soup.select_one('a.category-name, span.project-category')
            if category_elem:
                category = category_elem.get_text(strip=True)

            print(f"       タイトル: {title[:50]}..." if title else "       タイトル: 取得失敗")
            print(f"       カテゴリ: {category}" if category else "       カテゴリ: 取得失敗")

            return {
                "title": title,
                "description": description[:500] if description else "",
                "category": category
            }

        except Exception as e:
            print(f"     ⚠️ Kickstarter情報取得エラー: {e}")
            return {"title": "", "description": "", "category": ""}

    def extract_product_keywords(self, kickstarter_url, product_name=''):
        """
        Kickstarter URLから製品カテゴリとキーワードを抽出

        Args:
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            dict: キーワード情報（keywords, category, filter_keywords）
        """
        if not self.api_available:
            return {"keywords": [product_name], "category": "製品", "filter_keywords": []}

        try:
            # Kickstarterから製品情報を取得
            ks_info = self._fetch_kickstarter_info(kickstarter_url)

            prompt = f"""以下のKickstarter製品について、日本のクラウドファンディング（MakuakeやCAMPFIRE）で
類似製品を検索するための情報を提供してください。

【Kickstarter製品情報】
URL: {kickstarter_url}
製品名/メーカー: {product_name}
タイトル: {ks_info.get('title', '不明')}
カテゴリ: {ks_info.get('category', '不明')}
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
                print(f"     フィルタキーワード: {result.get('filter_keywords', [])}")
                return result
            return {"keywords": [product_name], "category": "製品", "filter_keywords": []}

        except Exception as e:
            print(f"  ⚠️ キーワード抽出エラー: {e}")
            return {"keywords": [product_name], "category": "製品", "filter_keywords": []}

    def search_makuake(self, keyword):
        """
        Makuakeで類似製品を検索
        MakuakeはJavaScript動的ページのため、RSSフィードから取得してキーワードフィルタリング

        Args:
            keyword (str): 検索キーワード

        Returns:
            dict: 検索結果
        """
        try:
            # MakuakeのRSSフィードを取得
            rss_url = "https://www.makuake.com/rss/"
            print(f"     Makuake検索（via RSS）: {keyword}")

            response = self.session.get(rss_url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'xml')
            projects = []

            # RSSアイテムを処理
            items = soup.find_all('item')
            print(f"       → RSSから{len(items)}件のアイテムを取得")
            for item in items:
                try:
                    title = item.find('title').get_text(strip=True) if item.find('title') else ""
                    description = item.find('description').get_text(strip=True) if item.find('description') else ""
                    link = item.find('link').get_text(strip=True) if item.find('link') else ""

                    # キーワードマッチング（タイトルに含まれる場合のみ - より厳密）
                    # 説明文は長いため誤マッチが多い、タイトルのみで判定
                    if keyword.lower() in title.lower():
                        if link and '/project/' in link:
                            # プロジェクト詳細を取得（メタタグから）
                            project_info = self._get_makuake_project_details(link)
                            if project_info:
                                projects.append(project_info)

                            if len(projects) >= 3:
                                break

                except Exception:
                    continue

            # キーワードマッチしなかった場合は0件として正直に返す（嘘をつかない）

            return {
                "found": len(projects) > 0,
                "projects": projects,
                "search_note": f"Makuakeで{len(projects)}件の類似製品を発見" if projects else "該当する製品が見つかりませんでした"
            }

        except Exception as e:
            print(f"     ⚠️ Makuake検索エラー: {type(e).__name__}: {e}")
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
        CAMPFIREで類似製品を検索（ウェブスクレイピング）

        Args:
            keyword (str): 検索キーワード
            filter_keywords (list): 結果フィルタリング用キーワード（動的に生成）

        Returns:
            dict: 検索結果
        """
        if filter_keywords is None:
            filter_keywords = []
        try:
            # CAMPFIRE検索URL
            search_url = f"https://camp-fire.jp/projects/search?word={requests.utils.quote(keyword)}"
            print(f"     CAMPFIRE検索: {keyword}")

            # 日本語サイトを強制するためのヘッダー追加
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
            dict: 検索結果
        """
        print(f"  🔍 類似製品を検索中...")

        # 1. 製品カテゴリとキーワードを抽出
        keyword_info = self.extract_product_keywords(kickstarter_url, product_name)
        keywords = keyword_info.get('keywords', [product_name])
        category = keyword_info.get('category', '製品')
        filter_keywords = keyword_info.get('filter_keywords', [])

        print(f"     カテゴリ: {category}")
        print(f"     キーワード: {', '.join(keywords)}")

        all_makuake_projects = []
        all_campfire_projects = []
        campfire_geo_restricted = False

        # 2. 各キーワードで検索
        for keyword in keywords[:2]:  # 最大2キーワード
            # Makuakeで検索
            makuake_results = self.search_makuake(keyword)
            if makuake_results.get('found'):
                for p in makuake_results['projects']:
                    if not any(existing['url'] == p['url'] for existing in all_makuake_projects):
                        all_makuake_projects.append(p)

            # CAMPFIREで検索（フィルタキーワードを渡す）
            campfire_results = self.search_campfire(keyword, filter_keywords)
            if campfire_results.get('geo_restricted'):
                campfire_geo_restricted = True
            elif campfire_results.get('found'):
                for p in campfire_results['projects']:
                    if not any(existing['url'] == p['url'] for existing in all_campfire_projects):
                        all_campfire_projects.append(p)

        # 3. 結果を制限
        all_makuake_projects = all_makuake_projects[:3]
        all_campfire_projects = all_campfire_projects[:3]

        has_results = len(all_makuake_projects) > 0 or len(all_campfire_projects) > 0

        if has_results:
            summary = f"Makuakeで{len(all_makuake_projects)}件、CAMPFIREで{len(all_campfire_projects)}件の類似製品を発見"
        else:
            summary = "日本のクラウドファンディングで類似製品は見つかりませんでした。これは市場における先行者利益の可能性を示しています。"

        if campfire_geo_restricted:
            summary += "（CAMPFIRE: 海外IPアクセス制限のためスキップ）"

        print(f"  ✓ 検索完了: {summary}")

        return {
            "category": category,
            "keywords": keywords,
            "makuake": {
                "found": len(all_makuake_projects) > 0,
                "projects": all_makuake_projects
            },
            "campfire": {
                "found": len(all_campfire_projects) > 0,
                "projects": all_campfire_projects,
                "geo_restricted": campfire_geo_restricted
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
        if not search_results.get('has_results', False):
            return """
【日本クラウドファンディング市場調査結果】

調査の結果、日本のクラウドファンディングプラットフォーム（Makuake、CAMPFIRE）において、
この製品に直接類似したキャンペーンは見つかりませんでした。

これは以下のポジティブな意味を持ちます：
・日本市場において、この製品カテゴリは未開拓である可能性が高い
・先行者利益（First Mover Advantage）を得られる大きなチャンス
・競合が少ないため、適切なマーケティングで市場リーダーになれる可能性
・新規性が高く、メディアや消費者の注目を集めやすい

レポートでは、類似製品が見つからなかったことを「未開拓市場への参入チャンス」として
前向きに伝えてください。架空の製品名やURLは絶対に記載しないでください。
"""

        lines = ["【日本クラウドファンディング市場調査結果 - 実在データ】\n"]
        lines.append(f"製品カテゴリ: {search_results.get('category', '製品')}\n")
        lines.append("以下は実際にウェブサイトから取得した実在するプロジェクト情報です。\n")

        # Makuake結果
        makuake = search_results.get('makuake', {})
        if makuake.get('found', False) and makuake.get('projects'):
            lines.append("■ Makuakeの類似製品（実在）:")
            for p in makuake['projects']:
                lines.append(f"  ・製品名: {p.get('name', '不明')}")
                lines.append(f"    URL: {p.get('url', '')}")
                lines.append(f"    資金調達額: {p.get('funding_amount', '非公開')}")
                if p.get('backers'):
                    lines.append(f"    支援者数: {p.get('backers')}人")
                lines.append("")
        else:
            lines.append("■ Makuake: 類似製品は見つかりませんでした\n")

        # CAMPFIRE結果
        campfire = search_results.get('campfire', {})
        if campfire.get('geo_restricted'):
            lines.append("■ CAMPFIRE: 海外IPからのアクセス制限のため取得できませんでした")
            lines.append("  （GitHub Actions環境からの実行のため、日本国外のIPアドレスが使用されています）\n")
        elif campfire.get('found', False) and campfire.get('projects'):
            lines.append("■ CAMPFIREの類似製品（実在）:")
            for p in campfire['projects']:
                lines.append(f"  ・製品名: {p.get('name', '不明')}")
                lines.append(f"    URL: {p.get('url', '')}")
                lines.append(f"    資金調達額: {p.get('funding_amount', '非公開')}")
                if p.get('backers'):
                    lines.append(f"    支援者数: {p.get('backers')}人")
                lines.append("")
        else:
            lines.append("■ CAMPFIRE: 類似製品は見つかりませんでした\n")

        lines.append("【重要な指示】")
        lines.append("・上記の製品情報のみをレポートに使用してください")
        lines.append("・URLは上記のものをそのまま使用してください")
        lines.append("・記載されていない架空の製品名やURLは絶対に生成しないでください")
        lines.append("・類似製品が見つからなかったプラットフォームについては、「見つからなかった」と正直に記載してください")

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
