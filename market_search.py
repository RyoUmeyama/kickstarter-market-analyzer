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

        # HTTPセッション設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        })

    def extract_product_keywords(self, kickstarter_url, product_name=''):
        """
        Kickstarter URLから製品カテゴリとキーワードを抽出

        Args:
            kickstarter_url (str): Kickstarter URL
            product_name (str): 製品名/メーカー名

        Returns:
            dict: キーワード情報
        """
        if not self.api_available:
            return {"keywords": [product_name], "category": "製品"}

        try:
            prompt = f"""以下のKickstarter製品について、日本のクラウドファンディング（MakuakeやCAMPFIRE）で
類似製品を検索するための適切な日本語キーワードを提案してください。

Kickstarter URL: {kickstarter_url}
製品名/メーカー: {product_name}

回答形式（JSON）:
{{"keywords": ["検索キーワード1", "検索キーワード2"], "category": "製品カテゴリ"}}

注意:
- Makuake/CAMPFIREの検索で使える具体的なキーワード（1-2語）
- 例: 「知育玩具」「ブロック」「ガジェット」「スマートウォッチ」など
- カテゴリは「知育玩具」「ガジェット」「生活用品」「アウトドア」などの分類
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "JSON形式で回答してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"keywords": [product_name], "category": "製品"}

        except Exception as e:
            print(f"  ⚠️ キーワード抽出エラー: {e}")
            return {"keywords": [product_name], "category": "製品"}

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
            print(f"     ⚠️ Makuake検索エラー: {e}")
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

    def search_campfire(self, keyword):
        """
        CAMPFIREで類似製品を検索（ウェブスクレイピング）

        Args:
            keyword (str): 検索キーワード

        Returns:
            dict: 検索結果
        """
        try:
            # CAMPFIRE検索URL
            search_url = f"https://camp-fire.jp/projects/search?word={requests.utils.quote(keyword)}"
            print(f"     CAMPFIRE検索: {keyword}")

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')
            projects = []

            # プロジェクトリンクを検索（パターン: /projects/ID/view）
            project_links = soup.select('a[href*="/projects/"][href*="/view"]')

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

                    # プロジェクト詳細を取得
                    project_info = self._get_campfire_project_details(project_url)
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
            print(f"     ⚠️ CAMPFIRE検索エラー: {e}")
            return {"found": False, "projects": [], "search_note": str(e)}

    def _get_campfire_project_details(self, project_url):
        """
        CAMPFIREプロジェクトの詳細を取得

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

            # 無効なタイトルを除外（通知ページなど非プロジェクト）
            invalid_titles = [
                "プロジェクト公開の通知を受け取ろう",
                "通知を受け取る",
                "お気に入り",
                "ログイン",
            ]

            if title and title != "不明":
                # 無効なタイトルかチェック
                if any(invalid in title for invalid in invalid_titles):
                    return None

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

        print(f"     カテゴリ: {category}")
        print(f"     キーワード: {', '.join(keywords)}")

        all_makuake_projects = []
        all_campfire_projects = []

        # 2. 各キーワードで検索
        for keyword in keywords[:2]:  # 最大2キーワード
            # Makuakeで検索
            makuake_results = self.search_makuake(keyword)
            if makuake_results.get('found'):
                for p in makuake_results['projects']:
                    if not any(existing['url'] == p['url'] for existing in all_makuake_projects):
                        all_makuake_projects.append(p)

            # CAMPFIREで検索
            campfire_results = self.search_campfire(keyword)
            if campfire_results.get('found'):
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
                "projects": all_campfire_projects
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
        if campfire.get('found', False) and campfire.get('projects'):
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
