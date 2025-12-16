#!/usr/bin/env python3
"""
競合分析モジュール

WebResearcherで取得した競合情報を詳細分析。
- 直接競合・間接競合の分類
- 競合製品の強み・弱み分析
- 価格ポジショニングマップ
- 差別化戦略の提案

※特定の業界にハードコードしない汎用設計
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI


class CompetitorAnalyzer:
    """
    競合分析クラス

    WebResearcherの出力を入力として、
    競合状況の詳細分析と差別化戦略を提案
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ OpenAI APIキーが設定されていません")

    def analyze(self, web_research_data: Dict, calculation_data: Dict = None) -> Dict:
        """
        競合分析を実行

        Args:
            web_research_data: WebResearcherの出力結果
            calculation_data: CalculationEngineの結果（価格情報など）

        Returns:
            競合分析結果の辞書
        """
        if not self.client:
            return {"error": "OpenAI APIキーが設定されていません"}

        print("\n" + "=" * 60)
        print("🎯 競合分析開始")
        print("=" * 60)

        results = {
            "meta": {
                "analyzed_at": datetime.now().isoformat()
            },
            "competitive_landscape": {},
            "direct_competitors": [],
            "indirect_competitors": [],
            "price_positioning": {},
            "feature_comparison": {},
            "competitive_advantages": {},
            "differentiation_strategy": {},
            "threat_assessment": {}
        }

        # 製品分析結果を取得
        product_analysis = web_research_data.get("product_analysis", {})
        category = product_analysis.get("category", "不明")
        product_type = product_analysis.get("product_type", "不明")

        print(f"  カテゴリ: {category}")
        print(f"  製品タイプ: {product_type}")

        # Step 1: 競合ランドスケープ分析
        print("\n[Step 1] 競合ランドスケープを分析中...")
        results["competitive_landscape"] = self._analyze_competitive_landscape(
            web_research_data
        )

        # Step 2: 直接競合分析
        print("\n[Step 2] 直接競合を分析中...")
        results["direct_competitors"] = self._analyze_direct_competitors(
            web_research_data
        )

        # Step 3: 間接競合分析
        print("\n[Step 3] 間接競合を分析中...")
        results["indirect_competitors"] = self._analyze_indirect_competitors(
            web_research_data
        )

        # Step 4: 価格ポジショニング分析
        print("\n[Step 4] 価格ポジショニングを分析中...")
        results["price_positioning"] = self._analyze_price_positioning(
            web_research_data, calculation_data
        )

        # Step 5: 機能比較分析
        print("\n[Step 5] 機能比較を分析中...")
        results["feature_comparison"] = self._analyze_feature_comparison(
            web_research_data
        )

        # Step 6: 競争優位性分析
        print("\n[Step 6] 競争優位性を分析中...")
        results["competitive_advantages"] = self._analyze_competitive_advantages(
            web_research_data
        )

        # Step 7: 差別化戦略提案
        print("\n[Step 7] 差別化戦略を策定中...")
        results["differentiation_strategy"] = self._develop_differentiation_strategy(
            web_research_data, results
        )

        # Step 8: 脅威評価
        print("\n[Step 8] 競合脅威を評価中...")
        results["threat_assessment"] = self._assess_competitive_threats(
            web_research_data, results
        )

        print("\n" + "=" * 60)
        print("✅ 競合分析完了")
        print("=" * 60)

        return results

    def _build_competitor_context(self, web_research_data: Dict) -> str:
        """競合分析用のコンテキストを構築"""
        context = ""

        # 製品情報
        pa = web_research_data.get("product_analysis", {})
        if pa:
            context += f"""
【分析対象製品】
- ブランド: {pa.get('brand_name', '不明')}
- 製品タイプ: {pa.get('product_type', '不明')}
- カテゴリ: {pa.get('category', '不明')}
- 主な特徴: {', '.join(pa.get('key_features', []))}
- ターゲット: {', '.join(pa.get('target_users', []))}
"""

        # Kickstarter情報
        kd = web_research_data.get("kickstarter_details", {})
        if kd:
            context += f"""
【Kickstarter実績】
- 調達額: ${kd.get('funding_amount_usd', '不明')}
- バッカー数: {kd.get('backers_count', '不明')}人
- 平均Pledge: ${kd.get('average_pledge_usd', '不明')}
"""
            price_tiers = kd.get("price_tiers", [])
            if price_tiers:
                context += "- 価格帯:\n"
                for tier in price_tiers[:5]:
                    if isinstance(tier, dict):
                        context += f"  ・{tier.get('tier_name', '')}: ${tier.get('price_usd', 0)}"
                        backers = tier.get('backers')
                        if backers:
                            context += f" ({backers}人)"
                        context += "\n"

        # Amazon Japan競合
        aj = web_research_data.get("amazon_japan", {})
        if aj:
            context += f"""
【Amazon.co.jp競合状況】
- ブランド存在: {'あり' if aj.get('brand_exists_in_japan') else 'なし'}
- 同一製品: {'あり' if aj.get('same_product_found') else 'なし'}
- 市場分析: {aj.get('market_analysis', '情報なし')}
"""
            products = aj.get("products_found", [])
            if products:
                context += "- 発見製品:\n"
                for p in products:
                    if isinstance(p, dict):
                        context += f"  ・{p.get('product_name', '')}\n"
                        context += f"    価格: ¥{p.get('price_jpy', 'N/A')}\n"
                        context += f"    評価: {p.get('rating', 'N/A')}★ ({p.get('review_count', 0)}件)\n"
                        context += f"    販売者: {p.get('seller_type', '不明')}\n"

        # 日本CF競合
        jcf = web_research_data.get("japan_cf_competitors", {})
        if jcf:
            competitors = jcf.get("competitors", [])
            context += f"""
【日本クラウドファンディング競合】
- Makuake同一製品: {'あり' if jcf.get('same_product_found', {}).get('makuake') else 'なし'}
- CAMPFIRE同一製品: {'あり' if jcf.get('same_product_found', {}).get('campfire') else 'なし'}
- 競合製品数: {len(competitors)}件
- カテゴリ分析: {jcf.get('category_analysis', '情報なし')}
- 差別化ポイント: {', '.join(jcf.get('differentiation_points', []))}
"""
            if competitors:
                context += "- 競合製品詳細:\n"
                for c in competitors:
                    if isinstance(c, dict):
                        context += f"  ・{c.get('product_name', '不明')}\n"
                        context += f"    プラットフォーム: {c.get('platform', '不明')}\n"
                        context += f"    調達額: ¥{c.get('funding_amount_jpy', 'N/A')}\n"
                        context += f"    達成率: {c.get('percent_funded', 'N/A')}%\n"
                        context += f"    価格: ¥{c.get('price_jpy', 'N/A')}\n"
                        context += f"    特徴: {c.get('features', '情報なし')}\n"

        return context

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
                temperature=0.3
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

    def _analyze_competitive_landscape(self, web_research_data: Dict) -> Dict:
        """競合ランドスケープを分析"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        category = pa.get("category", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたは競合分析のエキスパートです。
提供された情報を基に、日本市場での競合状況の全体像を分析してください。
情報がない場合は推測せず「情報不足」と記載してください。""",
            user_prompt=f"""以下の情報を基に、「{category}」カテゴリの競合ランドスケープを分析してください。

{context}

【出力形式】
```json
{{
    "market_structure": "寡占/分散/集中など",
    "competition_intensity": "高/中/低",
    "market_leaders": ["リーダー企業・製品1", "リーダー2"],
    "market_challengers": ["チャレンジャー1", "チャレンジャー2"],
    "market_nichers": ["ニッチプレイヤー1", "ニッチプレイヤー2"],
    "competitive_dynamics": {{
        "price_competition": "激しい/中程度/穏やか",
        "innovation_pace": "速い/中程度/遅い",
        "brand_importance": "高/中/低"
    }},
    "entry_timing": {{
        "assessment": "早い/適切/遅い",
        "reasoning": "理由"
    }},
    "white_space_opportunities": ["空白地帯1", "空白地帯2"],
    "summary": "競合ランドスケープの要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            intensity = result.get("competition_intensity", "不明")
            timing = result.get("entry_timing", {}).get("assessment", "不明")
            print(f"  ✓ 競争強度: {intensity}")
            print(f"  ✓ 参入タイミング: {timing}")

        return result

    def _analyze_direct_competitors(self, web_research_data: Dict) -> List[Dict]:
        """直接競合を分析（厳格フィルタリング版）"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")
        category = pa.get("category", "不明")
        key_features = pa.get("key_features", [])
        brand_name = pa.get("brand_name", "不明")

        # 製品特性を詳細に記述（厳格なフィルタリング用）
        product_characteristics = f"""
【分析対象製品の詳細】
- ブランド: {brand_name}
- 製品タイプ: {product_type}
- カテゴリ: {category}
- 主要特徴: {', '.join(key_features[:5]) if key_features else '不明'}

【直接競合の定義（厳格）】
直接競合とは、以下の条件を【全て】満たす製品のみ:
1. 同じ製品タイプ（「{product_type}」と同等の機能・形態）
2. 同じ使用目的・ユースケース
3. 同じターゲットユーザー層
4. 価格帯が大きく乖離しない（0.3倍〜3倍程度）

【除外すべき製品】
- 同じカテゴリだが製品タイプが異なるもの（例: フィットネスカテゴリでも、ダンベル≠ケーブルマシン）
- 関連製品・アクセサリー類
- 完全に異なる使用目的の製品
"""

        result = self._analyze_with_gpt(
            system_prompt="""あなたは競合分析のエキスパートです。
提供された情報から【直接競合製品のみ】を厳格に特定してください。

【重要ルール】
1. 「直接競合」の定義を厳格に適用すること
2. 関連性の低い製品は絶対に含めない
3. 迷った場合は「間接競合」または「除外」とする
4. 各製品に「relevance_score」(0-100)を付与し、80以上のみを直接競合とする""",
            user_prompt=f"""{product_characteristics}

{context}

【出力形式】
```json
{{
    "direct_competitors": [
        {{
            "name": "競合製品名",
            "brand": "ブランド名",
            "platform": "販売チャネル（Amazon/Makuake/CAMPFIREなど）",
            "price_jpy": 数値またはnull,
            "price_usd": 数値またはnull,
            "relevance_score": 80-100の数値,
            "relevance_reason": "なぜ直接競合と判断したか（製品タイプ・機能が同等など）",
            "market_position": "リーダー/チャレンジャー/フォロワー/ニッチャー",
            "strengths": ["強み1", "強み2"],
            "weaknesses": ["弱み1", "弱み2"],
            "key_features": ["特徴1", "特徴2"],
            "target_segment": "ターゲット層",
            "threat_level": "高/中/低",
            "url": "製品URL",
            "notes": "補足情報"
        }}
    ],
    "excluded_products": [
        {{
            "name": "除外した製品名",
            "reason": "除外理由（製品タイプが異なる、関連製品に過ぎない等）",
            "relevance_score": 79以下の数値
        }}
    ],
    "competitor_count": 数値,
    "most_threatening": "最も脅威となる競合名",
    "filtering_note": "厳格フィルタリングにより、関連性80点以上の製品のみを直接競合として抽出",
    "summary": "直接競合の要約"
}}
```"""
        )

        if isinstance(result, dict):
            competitors = result.get("direct_competitors", [])
            excluded = result.get("excluded_products", [])
            most_threatening = result.get("most_threatening", "なし")
            print(f"  ✓ 直接競合数: {len(competitors)}件")
            print(f"  ✓ 除外製品数: {len(excluded)}件")
            print(f"  ✓ 最大脅威: {most_threatening}")
            return competitors

        return []

    def _analyze_indirect_competitors(self, web_research_data: Dict) -> List[Dict]:
        """間接競合を分析"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")
        key_features = pa.get("key_features", [])

        result = self._analyze_with_gpt(
            system_prompt="""あなたは競合分析のエキスパートです。
提供された情報から間接競合を特定してください。
間接競合とは、異なる形態だが同じニーズを満たす代替製品・サービスです。""",
            user_prompt=f"""以下の情報から「{product_type}」（特徴: {', '.join(key_features)}）の間接競合を分析してください。

{context}

【出力形式】
```json
{{
    "indirect_competitors": [
        {{
            "category": "カテゴリ名",
            "examples": ["製品例1", "製品例2"],
            "substitution_risk": "高/中/低",
            "price_range_jpy": {{"low": 数値, "high": 数値}},
            "advantages_over_target": ["優位点1", "優位点2"],
            "disadvantages": ["劣位点1", "劣位点2"],
            "target_overlap": "ターゲット重複度（高/中/低）"
        }}
    ],
    "total_substitution_threat": "総合代替脅威（高/中/低）",
    "summary": "間接競合の要約"
}}
```"""
        )

        if isinstance(result, dict):
            competitors = result.get("indirect_competitors", [])
            threat = result.get("total_substitution_threat", "不明")
            print(f"  ✓ 間接競合カテゴリ数: {len(competitors)}件")
            print(f"  ✓ 代替脅威: {threat}")
            return competitors

        return []

    def _analyze_price_positioning(self, web_research_data: Dict, calculation_data: Dict = None) -> Dict:
        """価格ポジショニングを分析"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")

        # 計算データから価格情報を追加
        price_info = ""
        if calculation_data:
            recommendations = calculation_data.get("price_recommendations", [])
            if recommendations:
                price_info = "\n【推奨価格】\n"
                for r in recommendations:
                    price_info += f"- {r.get('label', '')}: ¥{r.get('price_jpy', 'N/A')}\n"

        result = self._analyze_with_gpt(
            system_prompt="""あなたは価格戦略のエキスパートです。
競合製品との価格ポジショニングを分析し、最適な価格帯を提案してください。""",
            user_prompt=f"""以下の情報から「{product_type}」の価格ポジショニングを分析してください。
{price_info}

{context}

【出力形式】
```json
{{
    "price_map": {{
        "premium": {{
            "range_jpy": {{"low": 数値, "high": 数値}},
            "competitors": ["競合1", "競合2"],
            "characteristics": "特徴"
        }},
        "mid_range": {{
            "range_jpy": {{"low": 数値, "high": 数値}},
            "competitors": ["競合1", "競合2"],
            "characteristics": "特徴"
        }},
        "budget": {{
            "range_jpy": {{"low": 数値, "high": 数値}},
            "competitors": ["競合1", "競合2"],
            "characteristics": "特徴"
        }}
    }},
    "target_product_positioning": {{
        "recommended_tier": "premium/mid_range/budget",
        "recommended_price_jpy": 数値,
        "price_premium_percent": "競合平均比プレミアム率",
        "justification": "価格設定の根拠"
    }},
    "price_sensitivity": {{
        "level": "高/中/低",
        "price_elasticity": "弾力的/中程度/非弾力的",
        "safe_price_range_jpy": {{"low": 数値, "high": 数値}}
    }},
    "competitive_pricing_tactics": ["戦術1", "戦術2"],
    "summary": "価格ポジショニングの要約"
}}
```"""
        )

        if isinstance(result, dict):
            rec_tier = result.get("target_product_positioning", {}).get("recommended_tier", "不明")
            rec_price = result.get("target_product_positioning", {}).get("recommended_price_jpy", "不明")
            print(f"  ✓ 推奨ポジション: {rec_tier}")
            print(f"  ✓ 推奨価格: ¥{rec_price}")

        return result

    def _analyze_feature_comparison(self, web_research_data: Dict) -> Dict:
        """機能比較を分析"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")
        key_features = pa.get("key_features", [])

        result = self._analyze_with_gpt(
            system_prompt="""あなたは製品分析のエキスパートです。
ターゲット製品と競合製品の機能を比較分析してください。""",
            user_prompt=f"""以下の情報から「{product_type}」（主な特徴: {', '.join(key_features)}）と競合の機能比較を行ってください。

{context}

【出力形式】
```json
{{
    "feature_matrix": [
        {{
            "feature": "機能名",
            "importance": "高/中/低",
            "target_product": "優/良/可/不可/情報なし",
            "competitor_average": "優/良/可/不可/情報なし",
            "competitive_gap": "優位/同等/劣位/情報不足"
        }}
    ],
    "unique_features": ["ターゲット製品固有の特徴1", "特徴2"],
    "missing_features": ["競合にあってターゲットにない機能1", "機能2"],
    "feature_parity_score": "1-10のスコア",
    "innovation_level": "革新的/差別化あり/同等/遅れている",
    "summary": "機能比較の要約"
}}
```"""
        )

        if isinstance(result, dict):
            unique = result.get("unique_features", [])
            innovation = result.get("innovation_level", "不明")
            print(f"  ✓ 固有機能数: {len(unique)}件")
            print(f"  ✓ イノベーションレベル: {innovation}")

        return result

    def _analyze_competitive_advantages(self, web_research_data: Dict) -> Dict:
        """競争優位性を分析"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")
        brand_name = pa.get("brand_name", "不明")

        # Kickstarter実績を追加
        kd = web_research_data.get("kickstarter_details", {})
        ks_info = ""
        if kd:
            funding = kd.get('funding_amount_usd')
            backers = kd.get('backers_count')
            percent = kd.get('percent_funded')
            if funding:
                ks_info = f"\nKickstarter実績: ${funding}調達, {backers}人のバッカー, {percent}%達成"

        result = self._analyze_with_gpt(
            system_prompt="""あなたは競争戦略のエキスパートです。
ターゲット製品の競争優位性を分析し、持続可能な優位性を特定してください。""",
            user_prompt=f"""以下の情報から「{product_type}」（ブランド: {brand_name}）の競争優位性を分析してください。
{ks_info}

{context}

【出力形式】
```json
{{
    "competitive_advantages": [
        {{
            "advantage": "優位性名",
            "type": "コスト/差別化/集中/技術/ブランド/その他",
            "description": "詳細説明",
            "sustainability": "高/中/低",
            "defensibility": "高/中/低",
            "evidence": "根拠"
        }}
    ],
    "competitive_disadvantages": [
        {{
            "disadvantage": "劣位点",
            "severity": "高/中/低",
            "mitigation_possible": true/false,
            "mitigation_strategy": "緩和策"
        }}
    ],
    "overall_competitive_position": "強い/やや強い/中立/やや弱い/弱い",
    "sustainable_advantages": ["持続可能な優位性1", "優位性2"],
    "summary": "競争優位性の要約"
}}
```"""
        )

        if isinstance(result, dict):
            position = result.get("overall_competitive_position", "不明")
            advantages = result.get("sustainable_advantages", [])
            print(f"  ✓ 競争ポジション: {position}")
            print(f"  ✓ 持続的優位性: {len(advantages)}件")

        return result

    def _develop_differentiation_strategy(self, web_research_data: Dict, analysis_results: Dict) -> Dict:
        """差別化戦略を策定"""
        context = self._build_competitor_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")

        # これまでの分析結果を追加
        analysis_summary = f"""
【これまでの分析結果】
- 競争強度: {analysis_results.get('competitive_landscape', {}).get('competition_intensity', '不明')}
- 直接競合数: {len(analysis_results.get('direct_competitors', []))}件
- 価格ポジション推奨: {analysis_results.get('price_positioning', {}).get('target_product_positioning', {}).get('recommended_tier', '不明')}
- イノベーションレベル: {analysis_results.get('feature_comparison', {}).get('innovation_level', '不明')}
- 競争ポジション: {analysis_results.get('competitive_advantages', {}).get('overall_competitive_position', '不明')}
"""

        result = self._analyze_with_gpt(
            system_prompt="""あなたは競争戦略のエキスパートです。
これまでの競合分析結果を総合し、最適な差別化戦略を提案してください。
Makuakeでのクラウドファンディングを前提として戦略を策定してください。""",
            user_prompt=f"""以下の情報から「{product_type}」の差別化戦略を策定してください。
{analysis_summary}

{context}

【出力形式】
```json
{{
    "primary_differentiation": {{
        "strategy": "差別化戦略名",
        "description": "詳細説明",
        "key_message": "コアメッセージ",
        "target_perception": "目指すポジショニング"
    }},
    "secondary_differentiations": [
        {{
            "strategy": "戦略名",
            "description": "説明"
        }}
    ],
    "value_proposition": {{
        "headline": "バリュープロポジションのヘッドライン",
        "subheadline": "サブヘッドライン",
        "key_benefits": ["ベネフィット1", "ベネフィット2", "ベネフィット3"],
        "proof_points": ["証拠1", "証拠2"]
    }},
    "positioning_statement": "ポジショニングステートメント（1文）",
    "competitive_response_plan": {{
        "if_price_war": "価格競争時の対応",
        "if_feature_copy": "機能模倣時の対応",
        "if_new_entrant": "新規参入時の対応"
    }},
    "implementation_priorities": [
        {{
            "action": "アクション",
            "priority": "高/中/低",
            "timing": "即時/短期/中期"
        }}
    ],
    "summary": "差別化戦略の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            primary = result.get("primary_differentiation", {}).get("strategy", "不明")
            headline = result.get("value_proposition", {}).get("headline", "不明")
            print(f"  ✓ 主要差別化: {primary}")
            print(f"  ✓ バリュープロポジション: {headline[:30]}...")

        return result

    def _assess_competitive_threats(self, web_research_data: Dict, analysis_results: Dict) -> Dict:
        """競合脅威を評価"""
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")

        # 分析結果からの情報
        direct_competitors = analysis_results.get("direct_competitors", [])
        landscape = analysis_results.get("competitive_landscape", {})

        threat_context = f"""
【脅威評価用データ】
- 製品タイプ: {product_type}
- 競争強度: {landscape.get('competition_intensity', '不明')}
- 直接競合数: {len(direct_competitors)}件
- 市場構造: {landscape.get('market_structure', '不明')}
"""

        if direct_competitors:
            threat_context += "\n【主要競合の脅威レベル】\n"
            for c in direct_competitors[:5]:
                if isinstance(c, dict):
                    threat_context += f"- {c.get('name', '不明')}: {c.get('threat_level', '不明')}\n"

        result = self._analyze_with_gpt(
            system_prompt="""あなたはリスク分析のエキスパートです。
競合からの脅威を総合評価し、対策を提案してください。""",
            user_prompt=f"""以下の情報から競合脅威を評価してください。

{threat_context}

【出力形式】
```json
{{
    "overall_threat_level": "高/中/低",
    "threat_breakdown": {{
        "existing_competitors": {{
            "level": "高/中/低",
            "details": "詳細"
        }},
        "new_entrants": {{
            "level": "高/中/低",
            "details": "詳細"
        }},
        "substitute_products": {{
            "level": "高/中/低",
            "details": "詳細"
        }},
        "price_pressure": {{
            "level": "高/中/低",
            "details": "詳細"
        }}
    }},
    "critical_threats": [
        {{
            "threat": "脅威名",
            "probability": "高/中/低",
            "impact": "高/中/低",
            "mitigation": "緩和策"
        }}
    ],
    "monitoring_points": ["監視すべきポイント1", "ポイント2"],
    "early_warning_signs": ["警戒サイン1", "サイン2"],
    "summary": "脅威評価の要約"
}}
```"""
        )

        if isinstance(result, dict):
            overall = result.get("overall_threat_level", "不明")
            critical = result.get("critical_threats", [])
            print(f"  ✓ 総合脅威レベル: {overall}")
            print(f"  ✓ 重要脅威数: {len(critical)}件")

        return result


def test_competitor_analyzer():
    """テスト実行"""
    from dotenv import load_dotenv
    load_dotenv()

    # テスト用のWeb調査結果を読み込み
    try:
        with open("web_research_results.json", "r", encoding="utf-8") as f:
            web_research_data = json.load(f)
    except FileNotFoundError:
        print("web_research_results.jsonが見つかりません")
        return

    analyzer = CompetitorAnalyzer()
    results = analyzer.analyze(web_research_data)

    # 結果を保存
    with open("competitor_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n結果をcompetitor_analysis_results.jsonに保存しました")


if __name__ == "__main__":
    test_competitor_analyzer()
