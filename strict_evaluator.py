#!/usr/bin/env python3
"""
厳格評価モジュール

全ての分析結果を統合し、厳格で偏りのない評価を実施。
- レッドフラグの特定
- ディールブレイカーの評価
- 情報ギャップの可視化
- Go/No-Go推奨
- 楽観的バイアスの排除

※厳格かつ正直な評価を重視
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI


class StrictEvaluator:
    """
    厳格評価クラス

    全ての分析結果を入力として、
    楽観的バイアスを排除した厳格な評価を提供
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ OpenAI APIキーが設定されていません")

    def evaluate(
        self,
        web_research_data: Dict,
        calculation_data: Dict = None,
        industry_analysis: Dict = None,
        competitor_analysis: Dict = None
    ) -> Dict:
        """
        厳格評価を実行

        Args:
            web_research_data: WebResearcherの出力
            calculation_data: CalculationEngineの結果
            industry_analysis: IndustryAnalyzerの結果
            competitor_analysis: CompetitorAnalyzerの結果

        Returns:
            厳格評価結果の辞書
        """
        if not self.client:
            return {"error": "OpenAI APIキーが設定されていません"}

        print("\n" + "=" * 60)
        print("⚠️ 厳格評価開始")
        print("=" * 60)

        results = {
            "meta": {
                "evaluated_at": datetime.now().isoformat(),
                "evaluation_approach": "conservative_unbiased"
            },
            "data_quality_assessment": {},
            "red_flags": [],
            "deal_breakers": [],
            "information_gaps": [],
            "risk_reality_check": {},
            "profit_reality_check": {},
            "market_reality_check": {},
            "go_nogo_assessment": {},
            "critical_questions": [],
            "summary": {}
        }

        # Step 1: データ品質評価
        print("\n[Step 1] データ品質を評価中...")
        results["data_quality_assessment"] = self._assess_data_quality(
            web_research_data, calculation_data
        )

        # Step 2: レッドフラグ特定
        print("\n[Step 2] レッドフラグを特定中...")
        results["red_flags"] = self._identify_red_flags(
            web_research_data, calculation_data, industry_analysis, competitor_analysis
        )

        # Step 3: ディールブレイカー評価
        print("\n[Step 3] ディールブレイカーを評価中...")
        results["deal_breakers"] = self._identify_deal_breakers(
            web_research_data, results["red_flags"]
        )

        # Step 4: 情報ギャップ特定
        print("\n[Step 4] 情報ギャップを特定中...")
        results["information_gaps"] = self._identify_information_gaps(
            web_research_data, calculation_data
        )

        # Step 5: リスク現実チェック
        print("\n[Step 5] リスクの現実チェック中...")
        results["risk_reality_check"] = self._reality_check_risks(
            web_research_data, industry_analysis, competitor_analysis
        )

        # Step 6: 利益現実チェック
        print("\n[Step 6] 利益の現実チェック中...")
        results["profit_reality_check"] = self._reality_check_profits(
            calculation_data, web_research_data
        )

        # Step 7: 市場現実チェック
        print("\n[Step 7] 市場の現実チェック中...")
        results["market_reality_check"] = self._reality_check_market(
            web_research_data, industry_analysis
        )

        # Step 8: Go/No-Go評価
        print("\n[Step 8] Go/No-Go評価中...")
        results["go_nogo_assessment"] = self._assess_go_nogo(
            results, web_research_data
        )

        # Step 9: 重要質問リスト
        print("\n[Step 9] 重要質問をリストアップ中...")
        results["critical_questions"] = self._generate_critical_questions(
            results, web_research_data
        )

        # Step 10: 総合サマリー
        print("\n[Step 10] 総合サマリーを生成中...")
        results["summary"] = self._generate_strict_summary(results)

        print("\n" + "=" * 60)
        print("✅ 厳格評価完了")
        print("=" * 60)

        return results

    def _analyze_with_gpt(self, system_prompt: str, user_prompt: str) -> Dict:
        """GPT-4oで分析を実行"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.2  # より保守的に
            )

            response_text = response.choices[0].message.content
            return self._parse_json_response(response_text)
        except Exception as e:
            print(f"  ⚠️ GPT分析エラー: {e}")
            return {"error": str(e)}

    def _parse_json_response(self, response_text: str) -> Dict:
        """レスポンスからJSONを抽出"""
        import re
        if not response_text:
            return {}

        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        try:
            return json.loads(response_text)
        except:
            pass

        return {"raw_text": response_text}

    def _assess_data_quality(self, web_research_data: Dict, calculation_data: Dict = None) -> Dict:
        """データ品質を評価"""
        quality_issues = []
        completeness_scores = {}

        # Web調査データの完全性チェック
        pa = web_research_data.get("product_analysis", {})
        if not pa or pa.get("category") == "不明":
            quality_issues.append("製品分析データが不完全")
            completeness_scores["product_analysis"] = 0
        else:
            completeness_scores["product_analysis"] = 80

        kd = web_research_data.get("kickstarter_details", {})
        if not kd or not kd.get("funding_amount_usd"):
            quality_issues.append("Kickstarterデータが不完全")
            completeness_scores["kickstarter_details"] = 0
        else:
            completeness_scores["kickstarter_details"] = 90

        aj = web_research_data.get("amazon_japan", {})
        if not aj or "error" in aj:
            quality_issues.append("Amazon.co.jp調査データが不完全")
            completeness_scores["amazon_japan"] = 0
        else:
            completeness_scores["amazon_japan"] = 70

        jcf = web_research_data.get("japan_cf_competitors", {})
        if not jcf or "error" in jcf:
            quality_issues.append("日本CF競合データが不完全")
            completeness_scores["japan_cf_competitors"] = 0
        else:
            completeness_scores["japan_cf_competitors"] = 60

        reg = web_research_data.get("regulations", {})
        if not reg or "error" in reg:
            quality_issues.append("規制情報が不完全")
            completeness_scores["regulations"] = 0
        else:
            completeness_scores["regulations"] = 70

        # 計算データのチェック
        if calculation_data:
            if not calculation_data.get("simulations"):
                quality_issues.append("利益シミュレーションデータがない")
                completeness_scores["calculations"] = 50
            else:
                completeness_scores["calculations"] = 85
        else:
            quality_issues.append("計算データが提供されていない")
            completeness_scores["calculations"] = 0

        # 総合スコア計算
        if completeness_scores:
            overall_score = sum(completeness_scores.values()) / len(completeness_scores)
        else:
            overall_score = 0

        result = {
            "overall_quality_score": round(overall_score, 1),
            "quality_rating": self._get_quality_rating(overall_score),
            "completeness_by_section": completeness_scores,
            "quality_issues": quality_issues,
            "data_reliability": "低" if overall_score < 50 else ("中" if overall_score < 75 else "高"),
            "recommendation": self._get_quality_recommendation(overall_score, quality_issues)
        }

        print(f"  ✓ データ品質スコア: {result['overall_quality_score']}/100")
        print(f"  ✓ 品質評価: {result['quality_rating']}")
        print(f"  ✓ 問題点: {len(quality_issues)}件")

        return result

    def _get_quality_rating(self, score: float) -> str:
        """品質スコアを評価に変換"""
        if score >= 80:
            return "良好"
        elif score >= 60:
            return "許容範囲"
        elif score >= 40:
            return "要注意"
        else:
            return "不十分"

    def _get_quality_recommendation(self, score: float, issues: List[str]) -> str:
        """品質に基づく推奨を生成"""
        if score >= 80:
            return "データ品質は良好。分析結果は信頼性が高い。"
        elif score >= 60:
            return f"データ品質は許容範囲だが、以下の点で追加調査を推奨: {', '.join(issues[:2])}"
        elif score >= 40:
            return f"データ品質に問題あり。以下の追加調査が必須: {', '.join(issues)}"
        else:
            return "データ品質が不十分。分析結果の信頼性は低い。追加のデータ収集が必要。"

    def _identify_red_flags(
        self,
        web_research_data: Dict,
        calculation_data: Dict,
        industry_analysis: Dict,
        competitor_analysis: Dict
    ) -> List[Dict]:
        """レッドフラグを特定"""
        red_flags = []

        # 1. 既存流通チェック
        aj = web_research_data.get("amazon_japan", {})
        if aj.get("same_product_found"):
            red_flags.append({
                "flag": "同一製品がAmazon.co.jpで販売済み",
                "severity": "高",
                "category": "市場",
                "implication": "クラウドファンディングの新規性訴求が困難。価格競争リスク。",
                "action_required": "価格差別化または付加価値の明確化が必須"
            })

        # 2. 日本CF既出チェック
        jcf = web_research_data.get("japan_cf_competitors", {})
        if jcf.get("same_product_found", {}).get("makuake"):
            red_flags.append({
                "flag": "同一製品がMakuakeで既出",
                "severity": "致命的",
                "category": "市場",
                "implication": "同一プラットフォームでの重複は審査通過困難。",
                "action_required": "別プラットフォームの検討または製品差別化"
            })

        # 3. 規制リスクチェック
        reg = web_research_data.get("regulations", {})
        pse = reg.get("pse", {})
        telec = reg.get("telec", {})

        if pse.get("required") == "必要" and pse.get("type") == "特定電気用品":
            red_flags.append({
                "flag": "特定電気用品のPSE認証が必要",
                "severity": "高",
                "category": "規制",
                "implication": "認証取得に時間とコストがかかる。スケジュールに影響。",
                "action_required": "PSE認証の事前取得計画が必須"
            })

        if telec.get("required") == "必要":
            red_flags.append({
                "flag": "技適認証が必要",
                "severity": "中",
                "category": "規制",
                "implication": "無線機能がある場合、技適なしでの販売は違法。",
                "action_required": "技適認証または既認証モジュールの使用確認"
            })

        # 4. 利益率チェック
        if calculation_data:
            simulations = calculation_data.get("simulations", [])
            profitable_cases = [s for s in simulations if s.get("profit_margin", 0) > 10]
            if len(profitable_cases) < len(simulations) / 2:
                red_flags.append({
                    "flag": "半数以上のシナリオで利益率10%未満",
                    "severity": "高",
                    "category": "財務",
                    "implication": "価格設定またはFOBコストに問題がある可能性。",
                    "action_required": "価格戦略の見直しまたはFOB交渉"
                })

            # 赤字シナリオチェック
            loss_cases = [s for s in simulations if s.get("profit_margin", 0) < 0]
            if loss_cases:
                red_flags.append({
                    "flag": f"{len(loss_cases)}件のシナリオで赤字",
                    "severity": "高",
                    "category": "財務",
                    "implication": "悲観シナリオでの赤字リスク。",
                    "action_required": "価格下限の設定と原価管理の徹底"
                })

        # 5. 競合脅威チェック
        if competitor_analysis:
            threat = competitor_analysis.get("threat_assessment", {})
            if threat.get("overall_threat_level") == "高":
                red_flags.append({
                    "flag": "競合脅威レベルが高",
                    "severity": "中",
                    "category": "競合",
                    "implication": "激しい競争環境。差別化が不十分だと埋没リスク。",
                    "action_required": "明確な差別化戦略の策定"
                })

        # 6. Kickstarter実績チェック
        kd = web_research_data.get("kickstarter_details", {})
        backers = kd.get("backers_count", 0)
        if backers and backers < 100:
            red_flags.append({
                "flag": f"Kickstarterバッカー数が少ない（{backers}人）",
                "severity": "中",
                "category": "実績",
                "implication": "製品の市場需要に疑問。日本市場でも同様の可能性。",
                "action_required": "需要検証とマーケティング強化"
            })

        print(f"  ✓ レッドフラグ: {len(red_flags)}件検出")
        for rf in red_flags:
            print(f"    ⚠️ {rf['flag']} (重大度: {rf['severity']})")

        return red_flags

    def _identify_deal_breakers(self, web_research_data: Dict, red_flags: List[Dict]) -> List[Dict]:
        """ディールブレイカーを特定"""
        deal_breakers = []

        # 致命的なレッドフラグを抽出
        for rf in red_flags:
            if rf.get("severity") == "致命的":
                deal_breakers.append({
                    "issue": rf["flag"],
                    "category": rf["category"],
                    "reason": rf["implication"],
                    "can_be_resolved": False,
                    "resolution_path": None
                })

        # 追加のディールブレイカーチェック
        jcf = web_research_data.get("japan_cf_competitors", {})
        if jcf.get("same_product_found", {}).get("makuake"):
            deal_breakers.append({
                "issue": "Makuakeで同一製品が既に展開済み",
                "category": "重複",
                "reason": "プラットフォームポリシーにより同一製品の重複掲載は認められない",
                "can_be_resolved": True,
                "resolution_path": "CAMPFIREなど別プラットフォームでの展開、または製品の大幅な差別化"
            })

        # 規制面でのディールブレイカー
        reg = web_research_data.get("regulations", {})
        pa = web_research_data.get("product_analysis", {})

        if pa.get("has_wireless_features") and reg.get("telec", {}).get("required") == "必要":
            if not reg.get("telec", {}).get("certified_module_option"):
                deal_breakers.append({
                    "issue": "技適認証が必要だが認証取得の見通しが不明",
                    "category": "規制",
                    "reason": "無線機能を持つ製品の日本販売には技適認証が法的に必須",
                    "can_be_resolved": True,
                    "resolution_path": "既認証モジュールの使用確認、または認証取得計画の策定"
                })

        if deal_breakers:
            print(f"  ⚠️ ディールブレイカー: {len(deal_breakers)}件")
            for db in deal_breakers:
                print(f"    🚫 {db['issue']}")
        else:
            print(f"  ✓ ディールブレイカー: なし")

        return deal_breakers

    def _identify_information_gaps(self, web_research_data: Dict, calculation_data: Dict = None) -> List[Dict]:
        """情報ギャップを特定"""
        gaps = []

        # 製品情報のギャップ
        pa = web_research_data.get("product_analysis", {})
        if not pa.get("key_features"):
            gaps.append({
                "gap": "製品の主要機能が不明",
                "importance": "高",
                "impact": "正確な競合比較・価格設定ができない",
                "how_to_fill": "Kickstarterページの詳細確認、メーカーへの問い合わせ"
            })

        # 価格情報のギャップ
        kd = web_research_data.get("kickstarter_details", {})
        if not kd.get("price_tiers"):
            gaps.append({
                "gap": "Kickstarter価格帯が不明",
                "importance": "高",
                "impact": "日本価格設定の根拠が不十分",
                "how_to_fill": "Kickstarterページで価格帯を直接確認"
            })

        # 公式情報のギャップ
        oi = web_research_data.get("official_info", {})
        if not oi.get("official_website", {}).get("msrp_usd"):
            gaps.append({
                "gap": "公式MSRP（希望小売価格）が不明",
                "importance": "中",
                "impact": "FOB推定精度が低下",
                "how_to_fill": "公式サイトまたはメーカーへの確認"
            })

        # 規制情報のギャップ
        reg = web_research_data.get("regulations", {})
        if reg.get("pse", {}).get("required") == "要確認":
            gaps.append({
                "gap": "PSE認証要否が未確定",
                "importance": "高",
                "impact": "規制対応コスト・期間が不明確",
                "how_to_fill": "製品の電源仕様を確認し、PSE対象か判定"
            })

        if reg.get("telec", {}).get("required") == "要確認":
            gaps.append({
                "gap": "技適認証要否が未確定",
                "importance": "高",
                "impact": "無線機能の有無と認証要否が不明",
                "how_to_fill": "製品の通信機能（Bluetooth/WiFi等）を確認"
            })

        # 市場情報のギャップ
        mi = web_research_data.get("market_info", {})
        if not mi or mi.get("market_info", {}).get("market_size_jpy") == "情報なし":
            gaps.append({
                "gap": "日本市場規模が不明",
                "importance": "中",
                "impact": "市場機会の定量評価が困難",
                "how_to_fill": "業界レポートまたは市場調査データの取得"
            })

        # FOB情報のギャップ
        if calculation_data:
            fob = calculation_data.get("fob_estimate", {})
            if fob.get("msrp_source", "").startswith("平均Pledge"):
                gaps.append({
                    "gap": "FOB価格が推定値",
                    "importance": "高",
                    "impact": "利益率計算の精度が低い",
                    "how_to_fill": "メーカーからの正式見積もり取得"
                })

        print(f"  ✓ 情報ギャップ: {len(gaps)}件")
        for gap in gaps:
            print(f"    📋 {gap['gap']} (重要度: {gap['importance']})")

        return gaps

    def _reality_check_risks(
        self,
        web_research_data: Dict,
        industry_analysis: Dict,
        competitor_analysis: Dict
    ) -> Dict:
        """リスクの現実チェック"""
        context = self._build_evaluation_context(web_research_data, industry_analysis, competitor_analysis)

        result = self._analyze_with_gpt(
            system_prompt="""あなたは厳格なリスク評価者です。
楽観的なバイアスを排除し、現実的なリスク評価を行ってください。
「最悪のケース」を常に考慮し、見落とされがちなリスクを指摘してください。""",
            user_prompt=f"""以下の情報を基に、リスクの現実チェックを行ってください。
楽観的な見方を排除し、現実的な評価をしてください。

{context}

【出力形式】
```json
{{
    "optimistic_biases_detected": [
        {{
            "area": "領域",
            "bias": "検出された楽観バイアス",
            "reality": "現実的な見方"
        }}
    ],
    "underestimated_risks": [
        {{
            "risk": "見落とされているリスク",
            "probability": "発生確率（高/中/低）",
            "impact": "影響度（高/中/低）",
            "why_underestimated": "なぜ見落とされやすいか"
        }}
    ],
    "worst_case_scenarios": [
        {{
            "scenario": "最悪のシナリオ",
            "trigger": "トリガー",
            "consequence": "結果",
            "probability": "発生確率"
        }}
    ],
    "risk_adjusted_assessment": {{
        "original_success_probability": "元の成功確率推定",
        "adjusted_success_probability": "リスク調整後の成功確率",
        "adjustment_reason": "調整理由"
    }},
    "critical_assumptions": [
        {{
            "assumption": "前提条件",
            "validity": "妥当性（高/中/低）",
            "if_wrong": "前提が崩れた場合の影響"
        }}
    ]
}}
```"""
        )

        if isinstance(result, dict):
            biases = result.get("optimistic_biases_detected", [])
            underestimated = result.get("underestimated_risks", [])
            print(f"  ✓ 楽観バイアス: {len(biases)}件検出")
            print(f"  ✓ 過小評価リスク: {len(underestimated)}件")

        return result

    def _reality_check_profits(self, calculation_data: Dict, web_research_data: Dict) -> Dict:
        """利益の現実チェック"""
        if not calculation_data:
            return {"error": "計算データがありません"}

        # 計算データから情報を抽出
        simulations = calculation_data.get("simulations", [])
        fob = calculation_data.get("fob_estimate", {})
        price_recs = calculation_data.get("price_recommendations", [])

        sim_summary = ""
        if simulations:
            for s in simulations[:3]:
                sim_summary += f"- {s.get('price_label', '')} × {s.get('fob_label', '')}: 利益率{s.get('profit_margin', 0)}%\n"

        fob_summary = f"""
FOB推定:
- 楽観: ¥{fob.get('fob_low', {}).get('jpy', 'N/A')}
- 標準: ¥{fob.get('fob_mid', {}).get('jpy', 'N/A')}
- 悲観: ¥{fob.get('fob_high', {}).get('jpy', 'N/A')}
- 根拠: {fob.get('msrp_source', '不明')}
"""

        result = self._analyze_with_gpt(
            system_prompt="""あなたは厳格な財務評価者です。
利益計算の前提条件を厳しくチェックし、現実的な利益見通しを評価してください。
楽観的な数字に騙されないよう注意してください。""",
            user_prompt=f"""以下の利益計算を厳格にチェックしてください。

【シミュレーション結果】
{sim_summary}

{fob_summary}

【出力形式】
```json
{{
    "fob_estimate_reliability": {{
        "rating": "高/中/低",
        "concerns": ["懸念点1", "懸念点2"],
        "realistic_fob_range": {{"low": "楽観的FOB", "high": "現実的FOB"}}
    }},
    "hidden_costs": [
        {{
            "cost_item": "コスト項目",
            "estimated_amount_jpy": "推定額",
            "often_overlooked": true/false
        }}
    ],
    "margin_pressure_factors": [
        {{
            "factor": "マージン圧迫要因",
            "impact_percent": "影響度（%ポイント）",
            "likelihood": "発生可能性"
        }}
    ],
    "realistic_profit_scenario": {{
        "scenario": "現実的シナリオ",
        "expected_margin_percent": "期待利益率",
        "confidence_level": "信頼度"
    }},
    "breakeven_risk": {{
        "level": "高/中/低",
        "units_at_risk": "損益分岐リスクのある販売台数",
        "conditions": "リスク発生条件"
    }},
    "recommendation": "利益面での推奨事項"
}}
```"""
        )

        if isinstance(result, dict):
            fob_reliability = result.get("fob_estimate_reliability", {}).get("rating", "不明")
            realistic = result.get("realistic_profit_scenario", {})
            print(f"  ✓ FOB信頼度: {fob_reliability}")
            print(f"  ✓ 現実的利益率: {realistic.get('expected_margin_percent', '不明')}%")

        return result

    def _reality_check_market(self, web_research_data: Dict, industry_analysis: Dict) -> Dict:
        """市場の現実チェック"""
        context = ""

        # 製品情報
        pa = web_research_data.get("product_analysis", {})
        kd = web_research_data.get("kickstarter_details", {})

        context += f"""
【製品】
- カテゴリ: {pa.get('category', '不明')}
- Kickstarter調達額: ${kd.get('funding_amount_usd', '不明')}
- バッカー数: {kd.get('backers_count', '不明')}人
"""

        # 業界分析結果
        if industry_analysis:
            japan_market = industry_analysis.get("japan_market_analysis", {})
            context += f"""
【業界分析結果】
- CF適性スコア: {japan_market.get('crowdfunding_potential', {}).get('score', '不明')}/10
- 市場成熟度: {japan_market.get('market_maturity', '不明')}
"""

        result = self._analyze_with_gpt(
            system_prompt="""あなたは厳格な市場評価者です。
日本市場での成功可能性を現実的に評価してください。
海外での成功が日本での成功を保証しないことを常に念頭に置いてください。""",
            user_prompt=f"""以下の情報を基に、日本市場での現実チェックを行ってください。

{context}

【出力形式】
```json
{{
    "japan_market_reality": {{
        "transferability_from_us": "米国成功の日本への移転可能性（高/中/低）",
        "cultural_fit": "日本文化との適合性（高/中/低）",
        "price_acceptance": "価格受容性（高/中/低）",
        "concerns": ["懸念点1", "懸念点2"]
    }},
    "demand_validation": {{
        "evidence_strength": "需要実証の強さ（強/中/弱）",
        "concerns": ["懸念点"],
        "additional_validation_needed": ["必要な追加検証1", "検証2"]
    }},
    "competitive_reality": {{
        "actual_competition_level": "実際の競争レベル",
        "differentiation_sustainability": "差別化の持続可能性",
        "market_entry_timing": "参入タイミングの評価"
    }},
    "success_probability_adjustment": {{
        "factor": "調整係数",
        "reasoning": "理由"
    }},
    "key_assumptions_to_validate": ["検証すべき主要前提1", "前提2"]
}}
```"""
        )

        if isinstance(result, dict):
            transferability = result.get("japan_market_reality", {}).get("transferability_from_us", "不明")
            evidence = result.get("demand_validation", {}).get("evidence_strength", "不明")
            print(f"  ✓ 日本移転可能性: {transferability}")
            print(f"  ✓ 需要実証強度: {evidence}")

        return result

    def _build_evaluation_context(
        self,
        web_research_data: Dict,
        industry_analysis: Dict,
        competitor_analysis: Dict
    ) -> str:
        """評価用のコンテキストを構築"""
        context = ""

        pa = web_research_data.get("product_analysis", {})
        context += f"""
【製品情報】
- ブランド: {pa.get('brand_name', '不明')}
- カテゴリ: {pa.get('category', '不明')}
- 製品タイプ: {pa.get('product_type', '不明')}
"""

        kd = web_research_data.get("kickstarter_details", {})
        if kd:
            context += f"""
【Kickstarter実績】
- 調達額: ${kd.get('funding_amount_usd', '不明')}
- バッカー数: {kd.get('backers_count', '不明')}人
"""

        if industry_analysis:
            io = industry_analysis.get("industry_overview", {})
            context += f"""
【業界分析】
- 成長段階: {io.get('growth_stage', '不明')}
- 競争強度: {industry_analysis.get('japan_market_analysis', {}).get('market_maturity', '不明')}
"""

        if competitor_analysis:
            cl = competitor_analysis.get("competitive_landscape", {})
            context += f"""
【競合状況】
- 競争強度: {cl.get('competition_intensity', '不明')}
- 参入タイミング: {cl.get('entry_timing', {}).get('assessment', '不明')}
"""

        return context

    def _assess_go_nogo(self, evaluation_results: Dict, web_research_data: Dict) -> Dict:
        """Go/No-Go評価"""
        # スコアリング
        scores = {
            "data_quality": 0,
            "red_flags": 0,
            "deal_breakers": 0,
            "risks": 0,
            "profit_potential": 0
        }

        # データ品質スコア
        dq = evaluation_results.get("data_quality_assessment", {})
        quality_score = dq.get("overall_quality_score", 50)
        scores["data_quality"] = quality_score / 100 * 20  # 最大20点

        # レッドフラグスコア（減点方式）
        red_flags = evaluation_results.get("red_flags", [])
        rf_penalty = 0
        for rf in red_flags:
            if rf.get("severity") == "致命的":
                rf_penalty += 15
            elif rf.get("severity") == "高":
                rf_penalty += 8
            elif rf.get("severity") == "中":
                rf_penalty += 4
        scores["red_flags"] = max(0, 25 - rf_penalty)  # 最大25点

        # ディールブレイカースコア
        deal_breakers = evaluation_results.get("deal_breakers", [])
        if deal_breakers:
            scores["deal_breakers"] = 0  # ディールブレイカーがあれば0点
        else:
            scores["deal_breakers"] = 25  # 最大25点

        # リスクスコア（現実チェック結果から）
        risk_check = evaluation_results.get("risk_reality_check", {})
        underestimated = len(risk_check.get("underestimated_risks", []))
        biases = len(risk_check.get("optimistic_biases_detected", []))
        risk_penalty = underestimated * 3 + biases * 2
        scores["risks"] = max(0, 15 - risk_penalty)  # 最大15点

        # 利益ポテンシャルスコア
        profit_check = evaluation_results.get("profit_reality_check", {})
        fob_reliability = profit_check.get("fob_estimate_reliability", {}).get("rating", "中")
        if fob_reliability == "高":
            scores["profit_potential"] = 15
        elif fob_reliability == "中":
            scores["profit_potential"] = 10
        else:
            scores["profit_potential"] = 5

        total_score = sum(scores.values())

        # 判定
        if deal_breakers:
            recommendation = "No-Go"
            confidence = "高"
            reasoning = f"ディールブレイカーが{len(deal_breakers)}件存在。"
        elif total_score >= 70:
            recommendation = "Go"
            confidence = "高" if total_score >= 80 else "中"
            reasoning = f"総合スコア{total_score}点。主要な障害なし。"
        elif total_score >= 50:
            recommendation = "Conditional Go"
            confidence = "中"
            reasoning = f"総合スコア{total_score}点。条件付きで進行可能。"
        else:
            recommendation = "No-Go"
            confidence = "高" if total_score < 35 else "中"
            reasoning = f"総合スコア{total_score}点。リスクが高い。"

        # 条件付きGoの場合の条件
        conditions = []
        if recommendation == "Conditional Go":
            for gap in evaluation_results.get("information_gaps", [])[:3]:
                if gap.get("importance") == "高":
                    conditions.append(gap["how_to_fill"])
            for rf in red_flags[:2]:
                if rf.get("severity") in ["高", "致命的"]:
                    conditions.append(rf["action_required"])

        result = {
            "recommendation": recommendation,
            "confidence": confidence,
            "total_score": total_score,
            "score_breakdown": scores,
            "reasoning": reasoning,
            "conditions": conditions if recommendation == "Conditional Go" else [],
            "immediate_actions": self._get_immediate_actions(evaluation_results, recommendation),
            "warning": "この評価は提供されたデータに基づく自動評価です。最終判断は人間が行ってください。"
        }

        print(f"  ✓ 推奨: {recommendation}")
        print(f"  ✓ 信頼度: {confidence}")
        print(f"  ✓ 総合スコア: {total_score}/100")

        return result

    def _get_immediate_actions(self, evaluation_results: Dict, recommendation: str) -> List[str]:
        """即時アクションを取得"""
        actions = []

        if recommendation == "No-Go":
            actions.append("プロジェクトの中止または大幅な見直しを検討")
            deal_breakers = evaluation_results.get("deal_breakers", [])
            for db in deal_breakers:
                if db.get("can_be_resolved"):
                    actions.append(f"解決策の検討: {db.get('resolution_path', '')}")
        elif recommendation == "Conditional Go":
            gaps = evaluation_results.get("information_gaps", [])
            for gap in gaps[:3]:
                if gap.get("importance") == "高":
                    actions.append(gap["how_to_fill"])
        else:  # Go
            actions.append("詳細な事業計画の策定")
            actions.append("メーカーとの交渉開始")

        return actions

    def _generate_critical_questions(self, evaluation_results: Dict, web_research_data: Dict) -> List[Dict]:
        """重要質問を生成"""
        questions = []

        # 情報ギャップから質問を生成
        for gap in evaluation_results.get("information_gaps", []):
            if gap.get("importance") == "高":
                questions.append({
                    "question": f"{gap['gap']}について確認が必要",
                    "why_important": gap["impact"],
                    "who_to_ask": "メーカー/関係者"
                })

        # レッドフラグから質問を生成
        for rf in evaluation_results.get("red_flags", []):
            if rf.get("severity") in ["高", "致命的"]:
                questions.append({
                    "question": f"{rf['flag']}に対する対策は?",
                    "why_important": rf["implication"],
                    "who_to_ask": "事業判断者"
                })

        # 規制関連
        reg = web_research_data.get("regulations", {})
        if reg.get("pse", {}).get("required") == "要確認":
            questions.append({
                "question": "製品にACアダプタや電源コードは含まれるか?",
                "why_important": "PSE認証の要否判断に必須",
                "who_to_ask": "メーカー"
            })

        if reg.get("telec", {}).get("required") == "要確認":
            questions.append({
                "question": "製品にBluetooth/WiFi/その他無線機能はあるか?",
                "why_important": "技適認証の要否判断に必須",
                "who_to_ask": "メーカー"
            })

        print(f"  ✓ 重要質問: {len(questions)}件")

        return questions[:10]  # 最大10件

    def _generate_strict_summary(self, evaluation_results: Dict) -> Dict:
        """厳格なサマリーを生成"""
        go_nogo = evaluation_results.get("go_nogo_assessment", {})
        red_flags = evaluation_results.get("red_flags", [])
        deal_breakers = evaluation_results.get("deal_breakers", [])
        gaps = evaluation_results.get("information_gaps", [])

        summary = {
            "recommendation": go_nogo.get("recommendation", "評価不能"),
            "total_score": go_nogo.get("total_score", 0),
            "key_concerns": [rf["flag"] for rf in red_flags if rf.get("severity") in ["高", "致命的"]][:5],
            "deal_breakers_count": len(deal_breakers),
            "information_gaps_count": len([g for g in gaps if g.get("importance") == "高"]),
            "bottom_line": self._get_bottom_line(go_nogo, red_flags, deal_breakers),
            "next_steps": go_nogo.get("immediate_actions", [])[:3]
        }

        print(f"\n  📊 最終評価: {summary['recommendation']}")
        print(f"  📊 スコア: {summary['total_score']}/100")
        print(f"  📊 結論: {summary['bottom_line']}")

        return summary

    def _get_bottom_line(self, go_nogo: Dict, red_flags: List, deal_breakers: List) -> str:
        """結論を一言で"""
        rec = go_nogo.get("recommendation", "")

        if rec == "No-Go":
            if deal_breakers:
                return f"ディールブレイカーあり。{deal_breakers[0]['issue']}の解決なしには進行不可。"
            else:
                return "リスクが高く、現状での進行は推奨しない。"
        elif rec == "Conditional Go":
            conditions = go_nogo.get("conditions", [])
            if conditions:
                return f"条件付き進行可能。優先: {conditions[0]}"
            else:
                return "条件付き進行可能。追加調査後に最終判断を。"
        elif rec == "Go":
            return "進行推奨。ただし特定されたリスクへの対策は必要。"
        else:
            return "評価に必要なデータが不足。追加調査を推奨。"


def test_strict_evaluator():
    """テスト実行"""
    from dotenv import load_dotenv
    load_dotenv()

    # テストデータを読み込み
    try:
        with open("web_research_results.json", "r", encoding="utf-8") as f:
            web_research_data = json.load(f)
    except FileNotFoundError:
        print("web_research_results.jsonが見つかりません")
        return

    evaluator = StrictEvaluator()
    results = evaluator.evaluate(web_research_data)

    # 結果を保存
    with open("strict_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n結果をstrict_evaluation_results.jsonに保存しました")


if __name__ == "__main__":
    test_strict_evaluator()
