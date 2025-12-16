#!/usr/bin/env python3
"""
業界分析モジュール

WebResearcherで取得したデータを基に業界分析を行う。
- 市場トレンド分析
- 日本市場での機会・リスク評価
- 参入障壁の分析
- 価格ポジショニング提案

※特定の業界にハードコードしない汎用設計
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional
from openai import OpenAI


class IndustryAnalyzer:
    """
    業界分析クラス

    WebResearcherの出力を入力として、
    製品が属する業界の詳細分析を行う
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ OpenAI APIキーが設定されていません")

    def analyze(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """
        業界分析を実行

        Args:
            web_research_data: WebResearcherの出力結果
            kickstarter_data: DataCollectorからのKickstarterデータ（補助）

        Returns:
            業界分析結果の辞書
        """
        if not self.client:
            return {"error": "OpenAI APIキーが設定されていません"}

        print("\n" + "=" * 60)
        print("📊 業界分析開始")
        print("=" * 60)

        results = {
            "meta": {
                "analyzed_at": datetime.now().isoformat()
            },
            "industry_overview": {},
            "japan_market_analysis": {},
            "entry_barriers": {},
            "opportunities": {},
            "risks": {},
            "pricing_strategy": {},
            "success_factors": {}
        }

        # 製品分析結果を取得
        product_analysis = web_research_data.get("product_analysis", {})
        category = product_analysis.get("category", "不明")
        product_type = product_analysis.get("product_type", "不明")

        print(f"  カテゴリ: {category}")
        print(f"  製品タイプ: {product_type}")

        # Step 1: 業界概要分析
        print("\n[Step 1] 業界概要を分析中...")
        results["industry_overview"] = self._analyze_industry_overview(
            web_research_data, kickstarter_data
        )

        # Step 2: 日本市場分析
        print("\n[Step 2] 日本市場を分析中...")
        results["japan_market_analysis"] = self._analyze_japan_market(
            web_research_data, kickstarter_data
        )

        # Step 3: 参入障壁分析
        print("\n[Step 3] 参入障壁を分析中...")
        results["entry_barriers"] = self._analyze_entry_barriers(
            web_research_data
        )

        # Step 4: 機会分析
        print("\n[Step 4] 市場機会を分析中...")
        results["opportunities"] = self._analyze_opportunities(
            web_research_data, kickstarter_data
        )

        # Step 5: リスク分析
        print("\n[Step 5] リスクを分析中...")
        results["risks"] = self._analyze_risks(
            web_research_data, kickstarter_data
        )

        # Step 6: 価格戦略分析
        print("\n[Step 6] 価格戦略を分析中...")
        results["pricing_strategy"] = self._analyze_pricing_strategy(
            web_research_data, kickstarter_data
        )

        # Step 7: 成功要因分析
        print("\n[Step 7] 成功要因を分析中...")
        results["success_factors"] = self._analyze_success_factors(
            web_research_data, kickstarter_data
        )

        print("\n" + "=" * 60)
        print("✅ 業界分析完了")
        print("=" * 60)

        return results

    def _build_context(self, web_research_data: Dict, kickstarter_data: Dict = None) -> str:
        """分析用のコンテキストを構築"""
        context = ""

        # 製品分析情報
        pa = web_research_data.get("product_analysis", {})
        if pa:
            context += f"""
【製品情報】
- ブランド名: {pa.get('brand_name', '不明')}
- 製品タイプ: {pa.get('product_type', '不明')}
- カテゴリ: {pa.get('category', '不明')}
- サブカテゴリ: {pa.get('subcategory', '不明')}
- 主な特徴: {', '.join(pa.get('key_features', []))}
- ターゲットユーザー: {', '.join(pa.get('target_users', []))}
- 電気製品: {'はい' if pa.get('has_electrical_components') else 'いいえ'}
- 無線機能: {'あり' if pa.get('has_wireless_features') else 'なし'}
- バッテリー: {'あり' if pa.get('has_battery') else 'なし'}
"""

        # Kickstarter情報
        kd = web_research_data.get("kickstarter_details", {})
        if kd:
            context += f"""
【Kickstarterキャンペーン情報】
- 調達額: ${kd.get('funding_amount_usd', '不明')}
- 目標額: ${kd.get('goal_amount_usd', '不明')}
- 達成率: {kd.get('percent_funded', '不明')}%
- バッカー数: {kd.get('backers_count', '不明')}人
- 平均Pledge: ${kd.get('average_pledge_usd', '不明')}
- ステータス: {kd.get('campaign_status', '不明')}
"""
            # 価格帯情報
            price_tiers = kd.get("price_tiers", [])
            if price_tiers:
                context += "- 価格帯:\n"
                for tier in price_tiers[:5]:
                    if isinstance(tier, dict):
                        context += f"  ・{tier.get('tier_name', '')}: ${tier.get('price_usd', 0)}\n"

        # Amazon Japan情報
        aj = web_research_data.get("amazon_japan", {})
        if aj:
            context += f"""
【Amazon.co.jp流通状況】
- ブランド存在: {'あり' if aj.get('brand_exists_in_japan') else 'なし'}
- 同一製品: {'あり' if aj.get('same_product_found') else 'なし'}
- 市場分析: {aj.get('market_analysis', '情報なし')}
"""
            products = aj.get("products_found", [])
            if products:
                context += "- 発見製品:\n"
                for p in products[:3]:
                    if isinstance(p, dict):
                        context += f"  ・{p.get('product_name', '')}: ¥{p.get('price_jpy', 'N/A')}\n"

        # 日本CF競合情報
        jcf = web_research_data.get("japan_cf_competitors", {})
        if jcf:
            competitors = jcf.get("competitors", [])
            context += f"""
【日本CF競合状況】
- Makuake同一製品: {'あり' if jcf.get('same_product_found', {}).get('makuake') else 'なし'}
- CAMPFIRE同一製品: {'あり' if jcf.get('same_product_found', {}).get('campfire') else 'なし'}
- 競合製品数: {len(competitors)}件
- カテゴリ分析: {jcf.get('category_analysis', '情報なし')}
"""
            if competitors:
                context += "- 競合製品:\n"
                for c in competitors[:3]:
                    if isinstance(c, dict):
                        context += f"  ・{c.get('product_name', '')}: ¥{c.get('funding_amount_jpy', 'N/A')}調達\n"

        # 規制情報
        reg = web_research_data.get("regulations", {})
        if reg:
            pse = reg.get("pse", {})
            telec = reg.get("telec", {})
            context += f"""
【規制情報】
- PSE: {pse.get('required', '要確認')} - {pse.get('reason', '')}
- 技適: {telec.get('required', '要確認')} - {telec.get('reason', '')}
- 推奨事項: {reg.get('recommendation', '情報なし')}
"""

        # 市場情報
        mi = web_research_data.get("market_info", {})
        if mi:
            fx = mi.get("exchange_rate", {})
            market = mi.get("market_info", {}) if isinstance(mi.get("market_info"), dict) else {}
            context += f"""
【市場情報】
- 為替レート: $1 = ¥{fx.get('usd_jpy', '不明')}
- 市場規模: {market.get('market_size_jpy', '情報なし')}
- 成長率: {market.get('growth_rate', '情報なし')}
"""

        # DataCollectorからの追加情報
        if kickstarter_data:
            context += f"""
【DataCollector情報】
- タイトル: {kickstarter_data.get('title', '不明')}
"""

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

    def _analyze_industry_overview(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """業界概要を分析"""
        context = self._build_context(web_research_data, kickstarter_data)
        pa = web_research_data.get("product_analysis", {})
        category = pa.get("category", "不明")
        product_type = pa.get("product_type", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたは市場調査のエキスパートです。
提供された情報を基に、製品が属する業界の概要を分析してください。
情報がない場合は推測せず「情報不足」と記載してください。""",
            user_prompt=f"""以下の情報を基に、「{category}」業界（製品: {product_type}）の概要を分析してください。

{context}

【出力形式】
```json
{{
    "industry_name": "業界名",
    "industry_name_en": "英語名",
    "global_market_size": "グローバル市場規模（推定）",
    "growth_stage": "成長段階（黎明期/成長期/成熟期/衰退期）",
    "key_players": ["主要プレイヤー1", "プレイヤー2"],
    "recent_trends": ["トレンド1", "トレンド2", "トレンド3"],
    "technology_drivers": ["技術トレンド1", "トレンド2"],
    "consumer_trends": ["消費者トレンド1", "トレンド2"],
    "typical_price_range": {{
        "low": "低価格帯",
        "mid": "中価格帯",
        "high": "高価格帯"
    }},
    "summary": "業界概要の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict) and "industry_name" in result:
            print(f"  ✓ 業界: {result.get('industry_name', '不明')}")
            print(f"  ✓ 成長段階: {result.get('growth_stage', '不明')}")

        return result

    def _analyze_japan_market(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """日本市場を分析"""
        context = self._build_context(web_research_data, kickstarter_data)
        pa = web_research_data.get("product_analysis", {})
        category = pa.get("category", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたは日本市場分析のエキスパートです。
提供された情報を基に、日本市場での製品カテゴリの状況を分析してください。
情報がない場合は推測せず「情報不足」と記載してください。""",
            user_prompt=f"""以下の情報を基に、日本市場での「{category}」カテゴリの状況を分析してください。

{context}

【出力形式】
```json
{{
    "market_size_jpy": "日本市場規模",
    "growth_rate": "成長率",
    "market_maturity": "市場成熟度（新興/成長/成熟/飽和）",
    "major_channels": ["主要販売チャネル1", "チャネル2"],
    "consumer_preferences": ["日本消費者の嗜好1", "嗜好2"],
    "price_sensitivity": "価格感度（高/中/低）",
    "quality_expectations": "品質期待度（高/中/低）",
    "import_product_acceptance": "輸入品受容度（高/中/低）",
    "crowdfunding_potential": {{
        "score": "1-10のスコア",
        "reasoning": "理由"
    }},
    "seasonal_factors": ["季節要因1", "要因2"],
    "summary": "日本市場分析の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            maturity = result.get("market_maturity", "不明")
            cf_score = result.get("crowdfunding_potential", {}).get("score", "不明")
            print(f"  ✓ 市場成熟度: {maturity}")
            print(f"  ✓ CF適性スコア: {cf_score}/10")

        return result

    def _analyze_entry_barriers(self, web_research_data: Dict) -> Dict:
        """参入障壁を分析"""
        context = self._build_context(web_research_data)
        pa = web_research_data.get("product_analysis", {})
        category = pa.get("category", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたは市場参入戦略のエキスパートです。
提供された情報を基に、日本市場への参入障壁を分析してください。
具体的な規制情報がある場合はそれを活用してください。""",
            user_prompt=f"""以下の情報を基に、「{category}」カテゴリの日本市場参入障壁を分析してください。

{context}

【出力形式】
```json
{{
    "regulatory_barriers": {{
        "level": "高/中/低",
        "details": ["規制障壁の詳細1", "詳細2"],
        "estimated_cost_jpy": "規制対応推定費用",
        "estimated_time": "規制対応推定期間"
    }},
    "competitive_barriers": {{
        "level": "高/中/低",
        "details": ["競合障壁の詳細1", "詳細2"]
    }},
    "distribution_barriers": {{
        "level": "高/中/低",
        "details": ["流通障壁の詳細1", "詳細2"]
    }},
    "brand_barriers": {{
        "level": "高/中/低",
        "details": ["ブランド障壁の詳細1", "詳細2"]
    }},
    "cultural_barriers": {{
        "level": "高/中/低",
        "details": ["文化的障壁の詳細1", "詳細2"]
    }},
    "overall_barrier_level": "総合評価（高/中/低）",
    "recommended_entry_strategy": "推奨参入戦略"
}}
```"""
        )

        if isinstance(result, dict):
            overall = result.get("overall_barrier_level", "不明")
            print(f"  ✓ 総合障壁レベル: {overall}")

        return result

    def _analyze_opportunities(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """市場機会を分析"""
        context = self._build_context(web_research_data, kickstarter_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたは市場機会分析のエキスパートです。
提供された情報を基に、この製品の日本市場での機会を分析してください。
楽観的すぎず、現実的な分析を行ってください。""",
            user_prompt=f"""以下の情報を基に、「{product_type}」の日本市場での機会を分析してください。

{context}

【出力形式】
```json
{{
    "market_opportunities": [
        {{
            "opportunity": "機会の名前",
            "description": "詳細説明",
            "potential_impact": "高/中/低",
            "time_to_capture": "短期/中期/長期"
        }}
    ],
    "competitive_advantages": [
        {{
            "advantage": "優位性の名前",
            "description": "詳細説明",
            "sustainability": "高/中/低"
        }}
    ],
    "target_segments": [
        {{
            "segment": "セグメント名",
            "size_estimate": "規模推定",
            "accessibility": "アクセスしやすさ（高/中/低）"
        }}
    ],
    "timing_assessment": {{
        "market_timing": "適切/やや早い/やや遅い/遅い",
        "reasoning": "理由"
    }},
    "opportunity_score": "1-10のスコア",
    "summary": "機会分析の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            score = result.get("opportunity_score", "不明")
            timing = result.get("timing_assessment", {}).get("market_timing", "不明")
            print(f"  ✓ 機会スコア: {score}/10")
            print(f"  ✓ 市場タイミング: {timing}")

        return result

    def _analyze_risks(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """リスクを分析"""
        context = self._build_context(web_research_data, kickstarter_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたはリスク分析のエキスパートです。
提供された情報を基に、この製品の日本市場でのリスクを分析してください。
重要なリスクを見落とさないよう、包括的に分析してください。""",
            user_prompt=f"""以下の情報を基に、「{product_type}」の日本市場でのリスクを分析してください。

{context}

【出力形式】
```json
{{
    "market_risks": [
        {{
            "risk": "リスク名",
            "description": "詳細説明",
            "probability": "高/中/低",
            "impact": "高/中/低",
            "mitigation": "緩和策"
        }}
    ],
    "regulatory_risks": [
        {{
            "risk": "リスク名",
            "description": "詳細説明",
            "probability": "高/中/低",
            "impact": "高/中/低",
            "mitigation": "緩和策"
        }}
    ],
    "competitive_risks": [
        {{
            "risk": "リスク名",
            "description": "詳細説明",
            "probability": "高/中/低",
            "impact": "高/中/低",
            "mitigation": "緩和策"
        }}
    ],
    "operational_risks": [
        {{
            "risk": "リスク名",
            "description": "詳細説明",
            "probability": "高/中/低",
            "impact": "高/中/低",
            "mitigation": "緩和策"
        }}
    ],
    "overall_risk_level": "総合リスクレベル（高/中/低）",
    "critical_risks": ["最重要リスク1", "リスク2"],
    "summary": "リスク分析の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            overall = result.get("overall_risk_level", "不明")
            critical = result.get("critical_risks", [])
            print(f"  ✓ 総合リスクレベル: {overall}")
            print(f"  ✓ 最重要リスク: {', '.join(critical[:2]) if critical else 'なし'}")

        return result

    def _analyze_pricing_strategy(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """価格戦略を分析"""
        context = self._build_context(web_research_data, kickstarter_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")

        # Kickstarter価格帯を取得
        kd = web_research_data.get("kickstarter_details", {})
        price_tiers = kd.get("price_tiers", [])
        avg_pledge = kd.get("average_pledge_usd")

        price_info = ""
        if price_tiers:
            prices = [t.get("price_usd", 0) for t in price_tiers if isinstance(t, dict) and t.get("price_usd")]
            if prices:
                price_info = f"Kickstarter価格帯: ${min(prices)} - ${max(prices)}, 平均Pledge: ${avg_pledge or 'N/A'}"

        result = self._analyze_with_gpt(
            system_prompt="""あなたは価格戦略のエキスパートです。
提供された情報を基に、日本市場での最適な価格戦略を提案してください。
Makuakeでのクラウドファンディングを前提として分析してください。""",
            user_prompt=f"""以下の情報を基に、「{product_type}」の日本市場価格戦略を分析してください。
{price_info}

{context}

【出力形式】
```json
{{
    "reference_prices": {{
        "kickstarter_range_usd": {{"low": 数値, "high": 数値}},
        "average_pledge_usd": 数値またはnull,
        "japan_competitor_range_jpy": {{"low": 数値, "high": 数値}},
        "amazon_jp_range_jpy": {{"low": 数値, "high": 数値}}
    }},
    "recommended_makuake_prices": {{
        "early_bird_jpy": 数値,
        "early_bird_discount_percent": 数値,
        "standard_jpy": 数値,
        "premium_bundle_jpy": 数値,
        "reasoning": "価格設定の理由"
    }},
    "price_positioning": "プレミアム/中価格帯/エントリー",
    "value_perception_drivers": ["価値訴求ポイント1", "ポイント2"],
    "price_sensitivity_assessment": "価格感度の評価",
    "margin_considerations": {{
        "estimated_fob_rate": "FOB率の推定（MSRP比）",
        "makuake_fee_percent": 22,
        "minimum_viable_margin": "最低限必要なマージン"
    }},
    "pricing_risks": ["価格関連リスク1", "リスク2"],
    "summary": "価格戦略の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            positioning = result.get("price_positioning", "不明")
            rec_prices = result.get("recommended_makuake_prices", {})
            early_bird = rec_prices.get("early_bird_jpy", "不明")
            print(f"  ✓ 価格ポジショニング: {positioning}")
            print(f"  ✓ 推奨早割価格: ¥{early_bird}")

        return result

    def _analyze_success_factors(self, web_research_data: Dict, kickstarter_data: Dict = None) -> Dict:
        """成功要因を分析"""
        context = self._build_context(web_research_data, kickstarter_data)
        pa = web_research_data.get("product_analysis", {})
        product_type = pa.get("product_type", "不明")
        category = pa.get("category", "不明")

        result = self._analyze_with_gpt(
            system_prompt="""あなたはクラウドファンディング成功要因分析のエキスパートです。
提供された情報を基に、Makuakeでの成功に必要な要因を分析してください。
現実的かつ実行可能な提案をしてください。""",
            user_prompt=f"""以下の情報を基に、「{product_type}」（{category}カテゴリ）のMakuake成功要因を分析してください。

{context}

【出力形式】
```json
{{
    "critical_success_factors": [
        {{
            "factor": "成功要因名",
            "importance": "高/中",
            "current_status": "満たしている/部分的/未確認/不足",
            "action_required": "必要なアクション"
        }}
    ],
    "product_strengths": ["強み1", "強み2", "強み3"],
    "product_weaknesses": ["弱み1", "弱み2"],
    "marketing_recommendations": [
        {{
            "channel": "マーケティングチャネル",
            "recommendation": "推奨内容",
            "priority": "高/中/低"
        }}
    ],
    "messaging_strategy": {{
        "primary_message": "メインメッセージ",
        "value_propositions": ["価値提案1", "価値提案2"],
        "target_keywords": ["キーワード1", "キーワード2"]
    }},
    "success_probability": {{
        "score": "1-10のスコア",
        "confidence": "高/中/低",
        "reasoning": "理由"
    }},
    "go_nogo_recommendation": {{
        "recommendation": "Go/Conditional Go/No Go",
        "conditions": ["条件1", "条件2"],
        "reasoning": "理由"
    }},
    "summary": "成功要因分析の要約（2-3文）"
}}
```"""
        )

        if isinstance(result, dict):
            success_score = result.get("success_probability", {}).get("score", "不明")
            go_nogo = result.get("go_nogo_recommendation", {}).get("recommendation", "不明")
            print(f"  ✓ 成功確率スコア: {success_score}/10")
            print(f"  ✓ Go/No-Go推奨: {go_nogo}")

        return result


def test_industry_analyzer():
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

    analyzer = IndustryAnalyzer()
    results = analyzer.analyze(web_research_data)

    # 結果を保存
    with open("industry_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n結果をindustry_analysis_results.jsonに保存しました")


if __name__ == "__main__":
    test_industry_analyzer()
