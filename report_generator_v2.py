#!/usr/bin/env python3
"""
レポート生成モジュール V2（Phase 3）
収集データと計算結果を基に、15項目の評価レポートを生成

出力形式:
- プレーンテキスト（マークダウン記法なし）
- 全データに出典URL付き
- 表形式はプレーンテキストで表現
"""

import os
import json
import re
from datetime import datetime
from openai import OpenAI


class ReportGeneratorV2:
    """
    15項目評価レポート生成クラス

    評価項目:
    ① 製品特徴・日本市場での通用度評価
    ② Kickstarter販売価格（支援時価格）
    ③ 調達総額（実績）
    ④ 日本CFでの既出可否
    ⑤ 日本EC（Amazon等）での既出可否
    ⑥ 日本CFにおける主要競合比較
    ⑦ （予備）
    ⑧ 日本での独占販売契約の可能性
    ⑨ 規制（PSE/技適）
    ⑩ 想定仕入単価（FOB）
    ⑪ 収支シミュレーション
    ⑫ 日本EC（Amazon等）での成功可能性
    ⑬ 量販（ドンキ等）への卸の可能性
    ⑭ Makuakeで利益100万円超の可否
    ⑮ 最終判定
    """

    def __init__(self, api_key=None, model='gpt-4o'):
        """
        Args:
            api_key: OpenAI APIキー
            model: 使用モデル（gpt-4oを推奨）
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ OpenAI APIキーが設定されていません")

    def generate_report(self, collected_data, calculation_results):
        """
        15項目評価レポートを生成

        Args:
            collected_data: DataCollectorで収集したデータ
            calculation_results: CalculationEngineで計算した結果

        Returns:
            str: 生成されたレポート（プレーンテキスト）
        """
        if not self.client:
            return "エラー: OpenAI APIキーが設定されていません"

        print("\n" + "=" * 60)
        print("📝 レポート生成開始")
        print("=" * 60)

        # プロンプトを構築
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(collected_data, calculation_results)

        print(f"  プロンプト長: {len(system_prompt) + len(user_prompt):,}文字")

        try:
            print("  🤖 OpenAI API呼び出し中...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=16000,
                temperature=0.3,  # 事実ベースの出力のため低めに設定
            )

            report = response.choices[0].message.content.strip()
            print(f"  ✓ レポート生成完了 ({len(report):,}文字)")

            # 後処理
            report = self._post_process(report)

            return report

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return f"レポート生成エラー: {str(e)}"

    def _build_system_prompt(self):
        """システムプロンプトを構築"""
        return """あなたは日本市場参入コンサルタントです。
Kickstarter製品の日本クラウドファンディング（主にMakuake）での展開可否を、事業者目線で厳しく評価するレポートを作成します。

=========================================
【最重要ルール - 絶対遵守】
=========================================

■ データ捏造の絶対禁止
  - 提供されたデータ以外の数値を絶対に使用しない
  - 「〜と推測される」「〜の可能性がある」という形で架空の数値を作らない
  - データがない場合は必ず「データなし」「取得失敗」と明記する
  - 特に以下の項目は提供データのみ使用:
    * 調達額、バッカー数、達成率
    * 類似製品の情報（製品名、URL、金額）
    * Amazon検索結果
  - 「例えば」「仮に」として具体的な金額を示すことも禁止

■ Kickstarter価格について
  - 提供データに「rewards」(リワード価格一覧)がない場合、個別の価格帯は記載しない
  - 「平均Pledge金額」のみを根拠として使用する
  - 「Early Bird」「Super Early Bird」等の価格は、データにない限り記載しない

■ 類似製品について
  - 提供データの「similar_products」リストに含まれる製品のみを記載する
  - 自分の知識で類似製品を追加しない
  - 類似製品がない場合は「Makuake/CAMPFIREでの類似製品: 検索結果なし」と記載

■ キャンペーンステータスについて
  - 提供データの「campaign_status」をそのまま使用する
  - 「active」「successful」「failed」「ended」以外のステータスを推測しない
  - 達成率が0%の場合、目標額が取得できていない可能性がある旨を記載

=========================================
【出力ルール】
=========================================

1. 出力形式
   - プレーンテキストのみ（マークダウン記法禁止）
   - 見出しは「① 製品特徴」のように丸数字を使用
   - 箇条書きは「・」を使用
   - 表は「|」で区切ったテキスト形式
   - URLは文中に自然に記載

2. 評価基準
   - 「高」「中」「低」の3段階評価を使用
   - 評価には必ず根拠を添えること
   - 厳しめの評価を心がけること（楽観的な予測は禁止）

3. 金額表記
   - 為替レートを明記（例: $1 = ¥152）
   - USDと日本円を併記（例: $143,110（約2,176万円））
   - 日本円は千円単位で丸める

4. 文体
   - 敬体は使わない（である調）
   - 冗長な表現を避け、簡潔に
   - 事実と分析を明確に分ける

5. 詳細度
   - 各項目は最低3行以上の分析を含めること
   - 単なるデータの羅列ではなく、意味のある分析を加えること
   - 競合比較では具体的な差別化ポイントを記載すること"""

    def _build_user_prompt(self, collected_data, calculation_results):
        """ユーザープロンプトを構築"""
        # データを整形
        ks_data = collected_data.get("kickstarter", {})
        kt_data = collected_data.get("kicktraq", {})
        bk_data = collected_data.get("backerkit", {})
        fx_data = collected_data.get("exchange_rate", {})
        az_data = collected_data.get("amazon_jp", {})
        mk_data = collected_data.get("makuake", {})
        cf_data = collected_data.get("campfire", {})

        calc = calculation_results
        ks_stats = calc.get("kickstarter_stats", {})
        fob_est = calc.get("fob_estimate", {})
        prices = calc.get("price_recommendations", [])
        sims = calc.get("simulations", [])
        profit_analysis = calc.get("profit_target_analysis", {})

        usd_jpy = fx_data.get("usd_jpy", 150)

        prompt = f"""以下のデータを基に、15項目の評価レポートを作成してください。

==================================================
【入力データ】為替レート: $1 = ¥{usd_jpy}
==================================================

【1. Kickstarter情報】
URL: {collected_data.get("meta", {}).get("kickstarter_url", "")}
製品名: {ks_data.get("title", "不明")}
説明: {ks_data.get("description", "なし")[:300]}
カテゴリ: {ks_data.get("category", "不明")}
調達額: ${ks_stats.get("funding_amount_usd", 0):,}（約{ks_stats.get("funding_amount_jpy", 0):,}円）
目標額: ${ks_stats.get("goal_amount_usd", 0):,}（約{ks_stats.get("goal_amount_jpy", 0):,}円）
達成率: {ks_stats.get("percent_funded", 0)}%
バッカー数: {ks_stats.get("backers_count", 0):,}人
平均Pledge: ${ks_stats.get("average_pledge_usd", 0):.2f}（約{ks_stats.get("average_pledge_jpy", 0):,}円）
キャンペーン状態: {ks_data.get("campaign_status", "不明")}
出典: {ks_data.get("source_url", "")}

【2. Kicktraq統計】
調達額: {kt_data.get("funding_amount", "未取得")}
バッカー数: {kt_data.get("backers_count", 0)}人
平均Pledge: {kt_data.get("average_pledge", "未取得")}
出典: {kt_data.get("source_url", "")}

【3. BackerKit統計】
調達額: {bk_data.get("funding_amount", "未取得")}
バッカー数: {bk_data.get("backers_count", 0)}人
平均Pledge: {bk_data.get("average_pledge", "未取得")}
出典: {bk_data.get("source_url", "")}

【4. Amazon.co.jp検索結果】
検索キーワード: {az_data.get("search_keywords", [])}
同一ブランド発見: {"あり" if az_data.get("same_brand_found") else "なし"}
検索URL: {az_data.get("source_url", "")}
"""
        # Amazon製品一覧
        az_products = az_data.get("products", [])
        if az_products:
            prompt += "発見した製品:\n"
            for p in az_products[:5]:
                prompt += f"  ・{p.get('title', '')[:50]} / {p.get('price', '')} / レビュー{p.get('reviews', 0)}件\n"
                prompt += f"    URL: {p.get('url', '')}\n"
        else:
            prompt += "発見した製品: なし\n"

        prompt += f"""
【5. Makuake検索結果】
検索キーワード: {mk_data.get("search_keywords", [])}
同一製品発見: {"あり" if mk_data.get("same_product_found") else "なし"}
検索URL: {mk_data.get("source_url", "")}
"""
        # Makuake類似製品一覧
        mk_products = mk_data.get("similar_products", [])
        if mk_products:
            prompt += "類似製品:\n"
            for p in mk_products[:5]:
                prompt += f"  ・{p.get('title', '')[:50]} / {p.get('funding_amount', '')} / {p.get('percent_funded', 0)}%達成\n"
                prompt += f"    URL: {p.get('url', '')}\n"
        else:
            prompt += "類似製品: なし\n"

        prompt += f"""
【6. CAMPFIRE検索結果】
検索キーワード: {cf_data.get("search_keywords", [])}
同一製品発見: {"あり" if cf_data.get("same_product_found") else "なし"}
海外IP制限: {"あり" if cf_data.get("geo_restricted") else "なし"}
検索URL: {cf_data.get("source_url", "")}
"""
        # CAMPFIRE類似製品一覧
        cf_products = cf_data.get("similar_products", [])
        if cf_products:
            prompt += "類似製品:\n"
            for p in cf_products[:5]:
                prompt += f"  ・{p.get('title', '')[:50]} / {p.get('funding_amount', '')} / {p.get('percent_funded', 0)}%達成\n"
                prompt += f"    URL: {p.get('url', '')}\n"
        else:
            prompt += "類似製品: なし\n"

        # FOB推定
        if fob_est and "error" not in fob_est:
            prompt += f"""
【7. FOB（仕入単価）推定】
MSRP（推定）: ${fob_est.get("msrp_usd", 0):.2f}（約{fob_est.get("msrp_jpy", 0):,}円）
MSRP根拠: {fob_est.get("msrp_source", "")}
FOB楽観（40%）: ${fob_est.get("fob_low", {}).get("usd", 0):.2f}（約{fob_est.get("fob_low", {}).get("jpy", 0):,}円）
FOB標準（47.5%）: ${fob_est.get("fob_mid", {}).get("usd", 0):.2f}（約{fob_est.get("fob_mid", {}).get("jpy", 0):,}円）
FOB悲観（55%）: ${fob_est.get("fob_high", {}).get("usd", 0):.2f}（約{fob_est.get("fob_high", {}).get("jpy", 0):,}円）
"""
        else:
            prompt += "\n【7. FOB推定】\nデータ不足のため推定不可\n"

        # 推奨価格
        if prices:
            prompt += "\n【8. 推奨販売価格（税込）】\n"
            for p in prices:
                prompt += f"  {p['label']}: ¥{p['price_jpy']:,}\n"

        # 収支シミュレーション
        if sims:
            prompt += "\n【9. 収支シミュレーション（1台あたり）】\n"
            prompt += "| 価格タイプ | 仕入タイプ | 販売価格 | 仕入原価 | 粗利 | 利益率 |\n"
            for sim in sims:
                prompt += f"| {sim['price_label']} | {sim['fob_label']} | ¥{sim['price_jpy']:,} | ¥{sim['fob_jpy']:,} | ¥{sim['gross_profit']:,} | {sim['profit_margin']}% |\n"

        # 利益目標分析
        if profit_analysis.get("best_case"):
            best = profit_analysis["best_case"]
            prompt += f"""
【10. 利益100万円達成分析】
ベストケース: {best['price_label']} × {best['fob_label']}
1台あたり粗利: ¥{best['gross_profit_per_unit']:,}
必要台数: {best['units_needed']}台
必要調達額: 約{best['total_revenue_formatted']}
"""

        # 固定コスト情報
        prompt += """
【固定情報】
・Makuake手数料: 22%（税込）
・国内配送料: 約1,200円/台
・輸入諸掛: 約1,500円/台（国際送料・通関等）
・PSE/技適: 製品による（0〜2,000円/台相当を案分）

==================================================
【出力指示 - 必ず守ること】
==================================================

以下の15項目で評価レポートを作成してください。

■ 必須ルール（違反厳禁）
1. 各項目には必ず【評価: 高/中/低】を入れてください
2. データがない場合は「データなし」「取得失敗」と明記
3. 推測で数値を作らない（「〜と思われる」で数字を作ることも禁止）
4. URLは提供されたもののみを記載
5. 各項目は3行以上の分析を含めること
6. 類似製品は提供されたリストのもののみを使用

■ 特に注意すべき点
- 「Kickstarter販売価格」: rewardsデータがない場合は「価格詳細: Kickstarterページでご確認ください」と記載
- 「調達総額」: 達成率が0%の場合は「目標額データ取得失敗のため達成率算出不可」と記載
- 「類似製品比較」: 提供リストが空の場合は「検索結果なし（別キーワードでの再検索推奨）」と記載
- 「Amazon検索結果」: productsが空の場合は「該当ブランドの商品は検出されず」と記載

① 製品特徴・日本市場での通用度評価
   - 製品スペック・訴求ポイント（タイトルと説明文から抽出）
   - 新規性・革新性・訴求力（各:高/中/低）
   - 日本市場での受容性分析（フィットネス需要、価格帯の妥当性等）
   - 総合評価

② Kickstarter販売価格（支援時価格）
   - 平均Pledge金額（提供データのみ使用）
   - 推定MSRP（定価）= 平均Pledge × 1.35の計算根拠を明記
   - リワード価格詳細がデータにない場合は「Kickstarterページでご確認ください」と記載

③ 調達総額（実績）
   - 調達額、バッカー数、達成率（提供データそのまま）
   - キャンペーン状態（active/successful等）
   - 出典URLを必ず明記
   - 達成率0%の場合は「目標額データ取得失敗」と注記

④ 日本CFでの既出可否（同一メーカー/同一製品）
   - Makuake検索結果: 同一製品の有無を明記
   - CAMPFIRE検索結果: 同一製品の有無を明記
   - 検索URLを記載

⑤ 日本EC（Amazon等）での既出可否
   - Amazon.co.jp検索結果（提供データのproductsリストを使用）
   - 同一ブランド/製品の有無
   - 検索URLを記載

⑥ 日本CFにおける主要競合比較
   - 提供された類似製品のみを表形式で比較
   - データがない場合は「類似製品: 検索結果なし」と明記
   - 差別化ポイントの分析

⑧ 日本での独占販売契約の可能性
   - 既存流通状況からの分析
   - Amazon/日本CFでの取扱状況を根拠に評価
   - 交渉難易度

⑨ 規制（PSE/技適）
   - 製品カテゴリに基づく規制要件の推定
   - 電気製品の場合: PSE要否
   - 無線機能ありの場合: 技適要否
   - 必要な認証と費用感

⑩ 想定仕入単価（FOB）
   - MSRP推定根拠を明記
   - FOB楽観/標準/悲観の3パターン（提供データ使用）

⑪ 収支シミュレーション（Makuake）
   - 提供された3価格帯×3仕入パターンの表を記載
   - コスト内訳（Makuake手数料22%、物流費等）
   - 推奨価格帯とその理由

⑫ 日本EC（Amazon等）での成功可能性・課題
   - 市場性評価
   - 具体的な課題（競合、価格、認知度等）

⑬ 量販（ドン・キホーテ等）への卸の可能性・課題
   - 卸価格帯の検討
   - 量販店向けの課題

⑭ Makuakeで利益100万円超の可否
   - 達成条件（価格×台数）を具体的に記載
   - 達成難易度の評価

⑮ 最終判定（事業者目線・厳しめ）
   - Makuake成功確度: 高/中/低
   - Go条件（どんな条件なら進めるべきか）
   - NG条件（どんな場合は見送るべきか）
   - 推奨アクション（次に取るべき具体的なステップ）

最後に「情報源URL一覧」として、提供されたURLのみをリストアップしてください。
"""
        return prompt

    def _post_process(self, report):
        """レポートの後処理"""
        # マークダウン記法を削除
        # **太字** → 太字
        report = re.sub(r'\*\*([^*]+)\*\*', r'\1', report)
        # *斜体* → 斜体
        report = re.sub(r'\*([^*]+)\*', r'\1', report)
        # # 見出し → 見出し
        report = re.sub(r'^#{1,6}\s+', '', report, flags=re.MULTILINE)
        # - 箇条書き → ・箇条書き
        report = re.sub(r'^-\s+', '・', report, flags=re.MULTILINE)

        # 連続する空行を整理
        report = re.sub(r'\n{3,}', '\n\n', report)

        return report.strip()


def test_report_generator():
    """テスト用関数"""
    from dotenv import load_dotenv
    load_dotenv()

    # テスト用ダミーデータ
    collected_data = {
        "meta": {
            "kickstarter_url": "https://www.kickstarter.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear"
        },
        "kickstarter": {
            "title": "MAXPRO Air: 100+lbs of Resistance. Just 2.5lbs of Gear.",
            "description": "Ultra-portable resistance training system",
            "funding_amount_usd": 143110,
            "backers_count": 388,
            "goal_amount_usd": 15000,
            "percent_funded": 957,
            "campaign_status": "successful",
            "source_url": "https://www.kickstarter.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear"
        },
        "kicktraq": {
            "funding_amount": "$143,110",
            "backers_count": 388,
            "average_pledge": "$368.84",
            "source_url": "https://www.kicktraq.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear/"
        },
        "backerkit": {
            "funding_amount": "$143,110",
            "backers_count": 388,
            "average_pledge": "$368.84",
            "average_pledge_usd": 368.84,
            "source_url": "https://www.backerkit.com/projects/726629114/maxpro-air-100-lbs-of-resistance-just-2lbs-of-gear"
        },
        "exchange_rate": {
            "usd_jpy": 152.0,
            "source_url": "https://api.exchangerate-api.com/v4/latest/USD"
        },
        "amazon_jp": {
            "search_keywords": ["MAXPRO"],
            "same_brand_found": True,
            "source_url": "https://www.amazon.co.jp/s?k=MAXPRO",
            "products": [
                {
                    "title": "MAXPRO SmartConnect",
                    "price": "¥89,800",
                    "reviews": 150,
                    "url": "https://www.amazon.co.jp/dp/B08KSGVP12"
                }
            ]
        },
        "makuake": {
            "search_keywords": ["MAXPRO", "fitness"],
            "same_product_found": False,
            "source_url": "https://www.makuake.com/discover/projects/?keyword=MAXPRO",
            "similar_products": [
                {
                    "title": "INNODIGYM",
                    "funding_amount": "5,000,000円",
                    "funding_amount_jpy": 5000000,
                    "percent_funded": 500,
                    "url": "https://www.makuake.com/project/innodigym/"
                }
            ]
        },
        "campfire": {
            "search_keywords": ["fitness"],
            "same_product_found": False,
            "geo_restricted": False,
            "source_url": "https://camp-fire.jp/projects/search?word=fitness",
            "similar_products": []
        }
    }

    calculation_results = {
        "exchange_rate": {"usd_jpy": 152.0},
        "kickstarter_stats": {
            "funding_amount_usd": 143110,
            "funding_amount_jpy": 21752720,
            "goal_amount_usd": 15000,
            "goal_amount_jpy": 2280000,
            "backers_count": 388,
            "average_pledge_usd": 368.84,
            "average_pledge_jpy": 56064,
            "percent_funded": 957
        },
        "fob_estimate": {
            "msrp_usd": 499,
            "msrp_jpy": 75848,
            "msrp_source": "平均Pledge × 1.35（推定）",
            "fob_low": {"usd": 199.6, "jpy": 30339},
            "fob_mid": {"usd": 237.0, "jpy": 36027},
            "fob_high": {"usd": 274.5, "jpy": 41719}
        },
        "price_recommendations": [
            {"label": "競争力重視", "price_jpy": 55800},
            {"label": "バランス型", "price_jpy": 64800},
            {"label": "プレミアム型", "price_jpy": 72800}
        ],
        "simulations": [
            {"price_label": "競争力重視", "fob_label": "楽観", "price_jpy": 55800, "fob_jpy": 30339, "gross_profit": 10165, "profit_margin": 18.2},
            {"price_label": "競争力重視", "fob_label": "標準", "price_jpy": 55800, "fob_jpy": 36027, "gross_profit": 4477, "profit_margin": 8.0},
            {"price_label": "バランス型", "fob_label": "楽観", "price_jpy": 64800, "fob_jpy": 30339, "gross_profit": 17705, "profit_margin": 27.3},
            {"price_label": "バランス型", "fob_label": "標準", "price_jpy": 64800, "fob_jpy": 36027, "gross_profit": 12017, "profit_margin": 18.5},
            {"price_label": "プレミアム型", "fob_label": "楽観", "price_jpy": 72800, "fob_jpy": 30339, "gross_profit": 24469, "profit_margin": 33.6},
            {"price_label": "プレミアム型", "fob_label": "標準", "price_jpy": 72800, "fob_jpy": 36027, "gross_profit": 18781, "profit_margin": 25.8},
        ],
        "profit_target_analysis": {
            "target_profit": 1000000,
            "best_case": {
                "price_label": "プレミアム型",
                "price_jpy": 72800,
                "fob_label": "楽観",
                "gross_profit_per_unit": 24469,
                "units_needed": 41,
                "total_revenue_formatted": "299万円"
            }
        }
    }

    generator = ReportGeneratorV2()
    report = generator.generate_report(collected_data, calculation_results)

    print("\n" + "=" * 60)
    print("【生成されたレポート】")
    print("=" * 60)
    print(report[:3000] + "..." if len(report) > 3000 else report)


if __name__ == '__main__':
    test_report_generator()
