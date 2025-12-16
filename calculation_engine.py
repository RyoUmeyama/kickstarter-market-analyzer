#!/usr/bin/env python3
"""
計算エンジンモジュール（Phase 2）
収集データを基に、収支シミュレーション等の計算を実行

計算内容:
1. FOB（仕入単価）推定
2. 収支シミュレーション（3価格帯 × 3仕入パターン）
3. 損益分岐点
4. 利益100万円達成条件
"""

import json
from datetime import datetime


class CalculationEngine:
    """
    収支計算エンジン

    Makuake手数料: 22%（税込）
    FOB推定: MSRPの40-55%
    """

    # 固定コスト
    MAKUAKE_FEE_RATE = 0.22  # Makuake手数料22%（税込）
    DOMESTIC_SHIPPING = 1200  # 国内配送料（円/台）
    IMPORT_COST_BASE = 1500  # 輸入諸掛（国際送料・通関等、円/台）
    PSE_TELEC_COST_PER_UNIT = 1000  # PSE/技適案分（円/台）、0〜2000の中間値

    # FOB推定の係数
    FOB_RATE_LOW = 0.40  # MSRPの40%
    FOB_RATE_MID = 0.475  # MSRPの47.5%
    FOB_RATE_HIGH = 0.55  # MSRPの55%

    def __init__(self, collected_data):
        """
        Args:
            collected_data: DataCollectorで収集したデータ（dict）
        """
        self.data = collected_data
        self.results = {
            "meta": {
                "calculated_at": datetime.now().isoformat(),
            },
            "exchange_rate": {
                "usd_jpy": 150.0,
                "source": "",
            },
            "kickstarter_stats": {},
            "fob_estimate": {},
            "price_recommendations": [],
            "simulations": [],
            "breakeven_analysis": {},
            "profit_target_analysis": {},
            "regulation_assessment": {},  # 規制情報
            "summary": {},
        }

        # 為替レートを設定
        fx_data = self.data.get("exchange_rate", {})
        if fx_data.get("usd_jpy"):
            self.results["exchange_rate"]["usd_jpy"] = fx_data["usd_jpy"]
            self.results["exchange_rate"]["source"] = fx_data.get("source_url", "")

    def _safe_numeric(self, value, default=0):
        """文字列や None を安全に数値に変換"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            # 数字以外の文字を除去して変換を試みる
            cleaned = ''.join(c for c in value if c.isdigit() or c == '.' or c == '-')
            if cleaned:
                try:
                    return float(cleaned) if '.' in cleaned else int(cleaned)
                except ValueError:
                    return default
        return default

    def calculate_all(self):
        """全ての計算を実行"""
        print("\n" + "=" * 60)
        print("📊 収支計算開始")
        print("=" * 60)

        # 1. Kickstarter統計の整理
        print("\n[1/6] Kickstarter統計整理中...")
        self._calculate_kickstarter_stats()

        # 2. FOB推定
        print("\n[2/6] FOB（仕入単価）推定中...")
        self._estimate_fob()

        # 3. 価格帯推奨
        print("\n[3/6] 推奨価格帯算出中...")
        self._recommend_prices()

        # 4. 収支シミュレーション
        print("\n[4/6] 収支シミュレーション実行中...")
        self._run_simulations()

        # 5. 利益目標分析
        print("\n[5/6] 利益目標分析中...")
        self._analyze_profit_targets()

        # 6. 規制情報の判定
        print("\n[6/6] 規制情報（PSE/技適）判定中...")
        self._assess_regulations()

        print("\n" + "=" * 60)
        print("✅ 収支計算完了")
        print("=" * 60)

        return self.results

    def _calculate_kickstarter_stats(self):
        """Kickstarter統計を整理（web_researchデータを優先）"""
        ks_data = self.data.get("kickstarter", {})
        kt_data = self.data.get("kicktraq", {})
        bk_data = self.data.get("backerkit", {})
        # Phase 1.5 Web調査データを取得（優先度高）
        web_research = self.data.get("web_research", {})
        ks_details = web_research.get("kickstarter_details", {})
        usd_jpy = self.results["exchange_rate"]["usd_jpy"]

        stats = {
            "title": ks_data.get("title", ""),
            "funding_amount_usd": 0,
            "funding_amount_jpy": 0,
            "goal_amount_usd": 0,
            "goal_amount_jpy": 0,
            "backers_count": 0,
            "average_pledge_usd": 0,
            "average_pledge_jpy": 0,
            "percent_funded": 0,
            "campaign_status": ks_data.get("campaign_status", ""),
            "data_sources": [],
        }

        # 調達額（web_research優先、次にKickstarter, Kicktraq, BackerKit）
        sources = [
            ("WebResearch", ks_details.get("funding_amount_usd", 0)),
            ("Kickstarter", ks_data.get("funding_amount_usd", 0)),
            ("Kicktraq", kt_data.get("funding_amount_usd", 0)),
            ("BackerKit", bk_data.get("funding_amount_usd", 0)),
        ]
        for name, amount in sources:
            amount = self._safe_numeric(amount)
            if amount > 0:
                stats["funding_amount_usd"] = amount
                stats["funding_amount_jpy"] = int(amount * usd_jpy)
                stats["data_sources"].append(f"{name}: 調達額")
                print(f"  ✓ 調達額: ${amount:,} (約{stats['funding_amount_jpy']:,}円) [{name}]")
                break

        # 目標金額
        if ks_data.get("goal_amount_usd"):
            stats["goal_amount_usd"] = ks_data["goal_amount_usd"]
            stats["goal_amount_jpy"] = int(ks_data["goal_amount_usd"] * usd_jpy)
            stats["data_sources"].append("Kickstarter: 目標額")
            print(f"  ✓ 目標額: ${stats['goal_amount_usd']:,}")

        # バッカー数（web_research優先）
        sources_backers = [
            ("WebResearch", ks_details.get("backers_count", 0)),
            ("Kickstarter", ks_data.get("backers_count", 0)),
            ("Kicktraq", kt_data.get("backers_count", 0)),
            ("BackerKit", bk_data.get("backers_count", 0)),
        ]
        for name, count in sources_backers:
            count = self._safe_numeric(count)
            if count > 0:
                stats["backers_count"] = count
                stats["data_sources"].append(f"{name}: バッカー数")
                print(f"  ✓ バッカー数: {count:,}人 [{name}]")
                break

        # 平均Pledge（web_research優先）
        sources_avg = [
            ("WebResearch", ks_details.get("average_pledge_usd", 0)),
            ("BackerKit", bk_data.get("average_pledge_usd", 0)),
            ("Kicktraq", kt_data.get("average_pledge_usd", 0)),
        ]
        for name, avg in sources_avg:
            avg = self._safe_numeric(avg)
            if avg > 0:
                stats["average_pledge_usd"] = avg
                stats["average_pledge_jpy"] = int(avg * usd_jpy)
                stats["data_sources"].append(f"{name}: 平均Pledge")
                print(f"  ✓ 平均Pledge: ${avg:.2f} (約{stats['average_pledge_jpy']:,}円) [{name}]")
                break

        # 計算で求める（平均Pledgeがない場合）
        if not stats["average_pledge_usd"] and stats["funding_amount_usd"] and stats["backers_count"]:
            avg = stats["funding_amount_usd"] / stats["backers_count"]
            stats["average_pledge_usd"] = round(avg, 2)
            stats["average_pledge_jpy"] = int(avg * usd_jpy)
            stats["data_sources"].append("計算: 平均Pledge")
            print(f"  ✓ 平均Pledge（計算）: ${stats['average_pledge_usd']:.2f}")

        # 達成率（web_research優先 - 重要！）
        pct_wr = self._safe_numeric(ks_details.get("percent_funded"))
        pct_ks = self._safe_numeric(ks_data.get("percent_funded"))
        if pct_wr > 0:
            stats["percent_funded"] = pct_wr
            stats["data_sources"].append("WebResearch: 達成率")
            print(f"  ✓ 達成率: {stats['percent_funded']}% [WebResearch]")
        elif pct_ks > 0:
            stats["percent_funded"] = pct_ks
            stats["data_sources"].append("Kickstarter: 達成率")
            print(f"  ✓ 達成率: {stats['percent_funded']}% [Kickstarter]")
        elif stats["funding_amount_usd"] and stats["goal_amount_usd"]:
            stats["percent_funded"] = int((stats["funding_amount_usd"] / stats["goal_amount_usd"]) * 100)
            stats["data_sources"].append("計算: 達成率")
            print(f"  ✓ 達成率: {stats['percent_funded']}% [計算]")

        self.results["kickstarter_stats"] = stats

    def _estimate_fob(self):
        """FOB（仕入単価）を推定（web_researchデータを優先）"""
        ks_stats = self.results["kickstarter_stats"]
        usd_jpy = self.results["exchange_rate"]["usd_jpy"]

        # Phase 1.5 Web調査データを取得
        web_research = self.data.get("web_research", {})
        official_info = web_research.get("official_info", {})

        # MSRP（定価）の推定
        # 優先順位: web_research公式情報 > official_site > Kickstarter平均Pledgeの1.35倍
        msrp_usd = 0
        msrp_source = ""

        # web_researchから公式MSRPを取得（最優先）
        wr_msrp = self._safe_numeric(official_info.get("msrp_usd"))
        if wr_msrp > 0:
            msrp_usd = wr_msrp
            msrp_source = "公式サイト（WebResearch）"

        # official_siteからのMSRP
        if not msrp_usd:
            official_data = self.data.get("official_site", {})
            off_msrp = self._safe_numeric(official_data.get("msrp_usd"))
            if off_msrp > 0:
                msrp_usd = off_msrp
                msrp_source = "公式サイト"

        # Kickstarter平均Pledgeから推定
        if not msrp_usd and ks_stats.get("average_pledge_usd"):
            avg = ks_stats["average_pledge_usd"]
            # 通常、Kickstarter価格はMSRPの70-80%程度
            msrp_usd = round(avg * 1.35, 2)  # 中央値
            msrp_source = f"平均Pledge ${avg:.2f} × 1.35（推定）"

        if not msrp_usd:
            print("  ⚠️ MSRP推定不可（データ不足）")
            self.results["fob_estimate"] = {"error": "MSRP推定不可"}
            return

        print(f"  ✓ MSRP（推定）: ${msrp_usd:.2f} (約{int(msrp_usd * usd_jpy):,}円) [{msrp_source}]")

        # FOB推定（3パターン）
        fob_low_usd = round(msrp_usd * self.FOB_RATE_LOW, 2)
        fob_mid_usd = round(msrp_usd * self.FOB_RATE_MID, 2)
        fob_high_usd = round(msrp_usd * self.FOB_RATE_HIGH, 2)

        fob_estimate = {
            "msrp_usd": msrp_usd,
            "msrp_jpy": int(msrp_usd * usd_jpy),
            "msrp_source": msrp_source,
            "fob_low": {
                "usd": fob_low_usd,
                "jpy": int(fob_low_usd * usd_jpy),
                "rate": f"{self.FOB_RATE_LOW * 100:.0f}%",
                "label": "楽観（大量発注/強い交渉力）"
            },
            "fob_mid": {
                "usd": fob_mid_usd,
                "jpy": int(fob_mid_usd * usd_jpy),
                "rate": f"{self.FOB_RATE_MID * 100:.1f}%",
                "label": "標準"
            },
            "fob_high": {
                "usd": fob_high_usd,
                "jpy": int(fob_high_usd * usd_jpy),
                "rate": f"{self.FOB_RATE_HIGH * 100:.0f}%",
                "label": "悲観（小ロット/ブランド力）"
            },
            "note": "FOBはMSRPの40-55%が一般的なディストリビュータ価格"
        }

        print(f"  ✓ FOB楽観: ${fob_low_usd:.2f} (約{fob_estimate['fob_low']['jpy']:,}円)")
        print(f"  ✓ FOB標準: ${fob_mid_usd:.2f} (約{fob_estimate['fob_mid']['jpy']:,}円)")
        print(f"  ✓ FOB悲観: ${fob_high_usd:.2f} (約{fob_estimate['fob_high']['jpy']:,}円)")

        self.results["fob_estimate"] = fob_estimate

    def _recommend_prices(self):
        """推奨販売価格帯を算出"""
        fob_data = self.results.get("fob_estimate", {})
        if "error" in fob_data:
            return

        ks_stats = self.results["kickstarter_stats"]
        usd_jpy = self.results["exchange_rate"]["usd_jpy"]

        # 推奨価格の計算根拠
        # 1. Kickstarter平均Pledgeの日本円換算 × 1.1〜1.3（日本プレミアム）
        # 2. 競合価格との比較（Makuakeの類似製品）

        base_prices = []

        # Kickstarter価格ベース
        if ks_stats.get("average_pledge_jpy"):
            avg_jpy = ks_stats["average_pledge_jpy"]
            # 日本市場では10-30%上乗せが一般的
            price_low = self._round_price(avg_jpy * 1.0)  # 同等
            price_mid = self._round_price(avg_jpy * 1.15)  # 15%増
            price_high = self._round_price(avg_jpy * 1.3)  # 30%増
            base_prices = [price_low, price_mid, price_high]

        # Makuake競合ベースで調整
        makuake_data = self.data.get("makuake", {})
        similar_products = makuake_data.get("similar_products", [])
        if similar_products:
            # 類似製品の価格帯を参考
            competitor_prices = [p.get("funding_amount_jpy", 0) for p in similar_products if p.get("funding_amount_jpy")]
            if competitor_prices:
                avg_competitor = sum(competitor_prices) / len(competitor_prices)
                print(f"  参考: Makuake類似製品平均調達額 {int(avg_competitor):,}円")

        # 最終的な推奨価格
        if base_prices:
            recommendations = []
            labels = ["競争力重視", "バランス型", "プレミアム型"]
            for i, price in enumerate(base_prices):
                rec = {
                    "price_jpy": price,
                    "price_tax_included": price,  # 税込表示
                    "label": labels[i],
                    "basis": f"Kickstarter平均Pledge ¥{ks_stats.get('average_pledge_jpy', 0):,}ベース"
                }
                recommendations.append(rec)
                print(f"  ✓ {labels[i]}: ¥{price:,}（税込）")

            self.results["price_recommendations"] = recommendations
        else:
            print("  ⚠️ 価格推奨計算不可（データ不足）")

    def _round_price(self, price):
        """価格を見栄えの良い数字に丸める（下3桁を800に）"""
        base = int(price / 1000) * 1000
        return base + 800 if price % 1000 >= 400 else base - 200

    def _run_simulations(self):
        """収支シミュレーションを実行"""
        fob_data = self.results.get("fob_estimate", {})
        if "error" in fob_data:
            return

        price_recs = self.results.get("price_recommendations", [])
        if not price_recs:
            return

        simulations = []

        # 3価格 × 3仕入パターン = 9パターン
        fob_cases = [
            ("楽観", fob_data["fob_low"]["jpy"]),
            ("標準", fob_data["fob_mid"]["jpy"]),
            ("悲観", fob_data["fob_high"]["jpy"]),
        ]

        for price_rec in price_recs:
            price = price_rec["price_jpy"]
            price_label = price_rec["label"]

            for fob_label, fob_jpy in fob_cases:
                # 収支計算
                makuake_fee = int(price * self.MAKUAKE_FEE_RATE)
                logistics_cost = self.DOMESTIC_SHIPPING + self.IMPORT_COST_BASE
                regulation_cost = self.PSE_TELEC_COST_PER_UNIT

                total_cost = fob_jpy + makuake_fee + logistics_cost + regulation_cost
                gross_profit = price - total_cost
                profit_margin = (gross_profit / price * 100) if price > 0 else 0

                sim = {
                    "price_label": price_label,
                    "price_jpy": price,
                    "fob_label": fob_label,
                    "fob_jpy": fob_jpy,
                    "breakdown": {
                        "販売価格（税込）": price,
                        "Makuake手数料（22%）": makuake_fee,
                        "仕入原価（FOB）": fob_jpy,
                        "国内物流費": self.DOMESTIC_SHIPPING,
                        "輸入諸掛": self.IMPORT_COST_BASE,
                        "PSE/技適案分": regulation_cost,
                        "総コスト": total_cost,
                    },
                    "gross_profit": gross_profit,
                    "profit_margin": round(profit_margin, 1),
                }
                simulations.append(sim)

        self.results["simulations"] = simulations

        # サマリー表示
        print("\n  【収支シミュレーション結果（1台あたり）】")
        print(f"  {'価格':<12} {'仕入':<8} {'粗利':>10} {'利益率':>8}")
        print("  " + "-" * 44)
        for sim in simulations:
            print(f"  {sim['price_label']:<10} {sim['fob_label']:<6} "
                  f"¥{sim['gross_profit']:>8,} {sim['profit_margin']:>7.1f}%")

    def _analyze_profit_targets(self):
        """利益目標（100万円）達成条件を分析"""
        simulations = self.results.get("simulations", [])
        if not simulations:
            return

        target_profit = 1_000_000  # 100万円

        analysis = {
            "target_profit": target_profit,
            "target_profit_formatted": "100万円",
            "achievable_cases": [],
            "best_case": None,
            "recommendation": "",
        }

        for sim in simulations:
            if sim["gross_profit"] <= 0:
                continue

            # 必要台数
            units_needed = int(target_profit / sim["gross_profit"]) + 1
            total_revenue = units_needed * sim["price_jpy"]

            case = {
                "price_label": sim["price_label"],
                "price_jpy": sim["price_jpy"],
                "fob_label": sim["fob_label"],
                "gross_profit_per_unit": sim["gross_profit"],
                "units_needed": units_needed,
                "total_revenue": total_revenue,
                "total_revenue_formatted": f"{total_revenue / 10000:.0f}万円",
            }
            analysis["achievable_cases"].append(case)

        # ベストケースを特定（最も少ない販売台数で達成）
        if analysis["achievable_cases"]:
            best = min(analysis["achievable_cases"], key=lambda x: x["units_needed"])
            analysis["best_case"] = best
            analysis["recommendation"] = (
                f"最小必要台数は{best['units_needed']}台（{best['price_label']}×{best['fob_label']}）。"
                f"目標調達額は約{best['total_revenue_formatted']}。"
            )
            print(f"\n  【利益100万円達成条件】")
            print(f"  ベストケース: {best['price_label']}（¥{best['price_jpy']:,}）× {best['fob_label']}")
            print(f"  → 必要台数: {best['units_needed']}台")
            print(f"  → 必要調達額: 約{best['total_revenue_formatted']}")

        # 損益分岐点
        breakeven = {}
        for sim in simulations:
            key = f"{sim['price_label']}_{sim['fob_label']}"
            if sim["gross_profit"] > 0:
                # 固定費がないため、1台目から利益が出る
                breakeven[key] = {
                    "units": 1,
                    "note": "変動費モデルのため1台目から利益発生"
                }
            else:
                breakeven[key] = {
                    "units": "N/A",
                    "note": "赤字（価格設定見直し必要）"
                }

        self.results["breakeven_analysis"] = breakeven
        self.results["profit_target_analysis"] = analysis

    def _assess_regulations(self):
        """製品カテゴリに基づく規制情報（PSE/技適）を判定"""
        ks_data = self.data.get("kickstarter", {})
        title = ks_data.get("title", "").lower()
        description = ks_data.get("description", "").lower()
        combined = f"{title} {description}"

        # 規制判定結果
        assessment = {
            "pse": {
                "required": "unknown",
                "reason": "",
                "type": "",
                "estimated_cost_jpy": 0,
                "notes": ""
            },
            "telec": {
                "required": "unknown",
                "reason": "",
                "estimated_cost_jpy": 0,
                "notes": ""
            },
            "product_category": "",
            "recommendation": ""
        }

        # カテゴリ判定キーワード
        wireless_keywords = ["bluetooth", "wifi", "wi-fi", "wireless", "ワイヤレス", "2.4ghz", "5ghz", "app", "smart"]
        electric_keywords = ["charger", "battery", "usb", "power", "adapter", "ac", "電源", "充電"]
        no_electric_keywords = ["manual", "mechanical", "手動", "non-electric"]

        # 無線機能の判定（技適）
        has_wireless = any(kw in combined for kw in wireless_keywords)
        # 電気製品の判定（PSE）
        has_electric = any(kw in combined for kw in electric_keywords)
        is_manual = any(kw in combined for kw in no_electric_keywords)

        # 製品カテゴリの推定
        if "fitness" in combined or "workout" in combined or "exercise" in combined or "resistance" in combined:
            assessment["product_category"] = "フィットネス器具"
        elif "speaker" in combined or "audio" in combined:
            assessment["product_category"] = "オーディオ機器"
        elif "watch" in combined or "wearable" in combined:
            assessment["product_category"] = "ウェアラブル機器"
        elif "light" in combined or "lamp" in combined:
            assessment["product_category"] = "照明器具"
        elif "charger" in combined or "power bank" in combined:
            assessment["product_category"] = "充電器/電源機器"
        else:
            assessment["product_category"] = "一般電子機器"

        # 技適（TELEC）判定
        if has_wireless:
            assessment["telec"]["required"] = "yes"
            assessment["telec"]["reason"] = "Bluetooth/WiFi等の無線機能を搭載"
            assessment["telec"]["estimated_cost_jpy"] = 450000  # 約$3,000相当
            assessment["telec"]["notes"] = "技適取得費用: 約30〜50万円（認証機関・製品複雑度による）。既認証モジュール使用の場合は低減可能。"
            print(f"  ✓ 技適: 必要（無線機能あり）")
        else:
            assessment["telec"]["required"] = "no"
            assessment["telec"]["reason"] = "無線機能なし"
            assessment["telec"]["estimated_cost_jpy"] = 0
            assessment["telec"]["notes"] = "無線機能がないため技適は不要"
            print(f"  ✓ 技適: 不要（無線機能なし）")

        # PSE判定
        if is_manual and not has_electric:
            assessment["pse"]["required"] = "no"
            assessment["pse"]["reason"] = "手動式/非電気製品"
            assessment["pse"]["type"] = "対象外"
            assessment["pse"]["estimated_cost_jpy"] = 0
            assessment["pse"]["notes"] = "電気を使用しない製品のためPSE対象外"
            print(f"  ✓ PSE: 不要（非電気製品）")
        elif has_electric:
            assessment["pse"]["required"] = "conditional"
            assessment["pse"]["reason"] = "電源アダプタ/充電機能の有無による"
            assessment["pse"]["type"] = "特定電気用品以外（USB充電式の場合）"
            assessment["pse"]["estimated_cost_jpy"] = 200000  # 約20万円
            assessment["pse"]["notes"] = "USB充電のみ: 不要の可能性。AC電源アダプタ同梱: PSE必要（約10〜30万円）"
            print(f"  ✓ PSE: 条件付き（電源仕様による）")
        else:
            assessment["pse"]["required"] = "unknown"
            assessment["pse"]["reason"] = "電源仕様の詳細確認が必要"
            assessment["pse"]["type"] = "要確認"
            assessment["pse"]["estimated_cost_jpy"] = 0
            assessment["pse"]["notes"] = "製品の電源仕様を確認してください"
            print(f"  ✓ PSE: 要確認（電源仕様不明）")

        # 総合推奨
        total_cost = assessment["pse"]["estimated_cost_jpy"] + assessment["telec"]["estimated_cost_jpy"]
        if total_cost > 0:
            assessment["recommendation"] = f"規制対応費用の目安: 約{total_cost:,}円。輸入前にメーカーに製品仕様（電源方式・無線機能）を確認し、必要な認証を特定してください。"
        else:
            assessment["recommendation"] = "規制対応は軽微または不要の可能性がありますが、製品の最終仕様を確認してください。"

        self.results["regulation_assessment"] = assessment

    def get_summary_for_prompt(self):
        """AI分析用のサマリーを取得"""
        usd_jpy = self.results["exchange_rate"]["usd_jpy"]
        ks = self.results["kickstarter_stats"]
        fob = self.results.get("fob_estimate", {})
        prices = self.results.get("price_recommendations", [])
        profit_analysis = self.results.get("profit_target_analysis", {})

        summary = []
        summary.append("=" * 50)
        summary.append("【計算結果サマリー】")
        summary.append("=" * 50)
        summary.append(f"為替レート: $1 = ¥{usd_jpy}")
        summary.append("")

        # Kickstarter実績
        summary.append("【Kickstarter実績】")
        summary.append(f"  調達額: ${ks.get('funding_amount_usd', 0):,} (約{ks.get('funding_amount_jpy', 0):,}円)")
        summary.append(f"  バッカー数: {ks.get('backers_count', 0):,}人")
        summary.append(f"  平均Pledge: ${ks.get('average_pledge_usd', 0):.2f} (約{ks.get('average_pledge_jpy', 0):,}円)")
        summary.append(f"  達成率: {ks.get('percent_funded', 0)}%")
        summary.append("")

        # FOB推定
        if fob and "error" not in fob:
            summary.append("【FOB（仕入単価）推定】")
            summary.append(f"  MSRP: ${fob['msrp_usd']:.2f} (約{fob['msrp_jpy']:,}円)")
            summary.append(f"  FOB楽観（40%）: ${fob['fob_low']['usd']:.2f} (約{fob['fob_low']['jpy']:,}円)")
            summary.append(f"  FOB標準（47.5%）: ${fob['fob_mid']['usd']:.2f} (約{fob['fob_mid']['jpy']:,}円)")
            summary.append(f"  FOB悲観（55%）: ${fob['fob_high']['usd']:.2f} (約{fob['fob_high']['jpy']:,}円)")
            summary.append("")

        # 推奨価格
        if prices:
            summary.append("【推奨販売価格（税込）】")
            for p in prices:
                summary.append(f"  {p['label']}: ¥{p['price_jpy']:,}")
            summary.append("")

        # 利益目標
        if profit_analysis.get("best_case"):
            best = profit_analysis["best_case"]
            summary.append("【利益100万円達成条件】")
            summary.append(f"  ベストケース: {best['price_label']} × {best['fob_label']}")
            summary.append(f"  必要台数: {best['units_needed']}台")
            summary.append(f"  必要調達額: 約{best['total_revenue_formatted']}")
            summary.append("")

        return "\n".join(summary)

    def to_json(self, filepath=None):
        """計算結果をJSONとして出力"""
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"✓ 計算結果を {filepath} に保存しました")

        return json.dumps(self.results, ensure_ascii=False, indent=2)


def test_calculation():
    """テスト用関数"""
    # テスト用のダミーデータ
    test_data = {
        "kickstarter": {
            "title": "MAXPRO Air",
            "funding_amount_usd": 143110,
            "backers_count": 388,
            "goal_amount_usd": 15000,
            "percent_funded": 957,
        },
        "kicktraq": {
            "funding_amount_usd": 143110,
            "backers_count": 388,
            "average_pledge_usd": 368.84,
        },
        "backerkit": {
            "funding_amount_usd": 143110,
            "backers_count": 388,
            "average_pledge_usd": 368.84,
        },
        "exchange_rate": {
            "usd_jpy": 152.0,
            "source_url": "https://api.exchangerate-api.com/v4/latest/USD",
        },
        "makuake": {
            "similar_products": [
                {"title": "INNODIGYM", "funding_amount_jpy": 5000000}
            ]
        }
    }

    engine = CalculationEngine(test_data)
    results = engine.calculate_all()

    print("\n" + engine.get_summary_for_prompt())


if __name__ == '__main__':
    test_calculation()
