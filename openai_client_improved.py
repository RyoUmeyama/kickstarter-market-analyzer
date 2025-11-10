#!/usr/bin/env python3
"""
OpenAI API連携モジュール（改善版）
より事業者目線の詳細な市場分析レポートを生成
"""

import os
from openai import OpenAI


class ImprovedMarketReportGenerator:
    """改善版：市場分析レポート生成クラス"""

    def __init__(self, api_key=None, model='gpt-4o-mini'):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def generate_japanese_report(self, kickstarter_data, maker_name, creator_name, business_context=''):
        """事業者目線の詳細な日本語レポートを生成"""
        prompt = self._create_improved_japanese_prompt(kickstarter_data, maker_name, creator_name, business_context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """あなたは日本のクラウドファンディング市場に精通した事業コンサルタントです。
海外製品の日本市場参入を支援する専門家として、データに基づいた具体的で実践的な分析を行います。
推測ではなく、可能な限り具体的な数値、製品名、URL、実績データを含めてください。
事業者が意思決定できるレベルの詳細な分析を提供してください。"""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error generating Japanese report: {e}")
            return f"エラー: レポート生成に失敗しました ({str(e)})"

    def _create_improved_japanese_prompt(self, data, maker_name, creator_name, business_context=''):
        """改善版：事業者目線の詳細なプロンプト"""
        product_name = data.get('product_name', '不明')
        url = data.get('url', '')
        pledge_amounts = data.get('pledge_amounts', '不明')
        funding_total = data.get('funding_total_usd', 0)
        funding_jpy = data.get('funding_total_jpy', 0)
        backers = data.get('backers', 0)
        category = data.get('category', '不明')
        description = data.get('description', '')

        prompt = f"""
以下のKickstarterプロジェクトについて、事業者が意思決定できるレベルの詳細な市場分析レポートを作成してください。

---
【製品情報】
製品名: {product_name}
メーカー名: {maker_name}
クリエーター名: {creator_name}
製品URL: {url}

【Kickstarterデータ】
プレッジ金額: {pledge_amounts}
総支援額: ${funding_total:,.2f} (約{funding_jpy:,}円)
支援者数: {backers:,}人
平均支援額: ${funding_total/max(backers, 1):.2f}
カテゴリ: {category}
製品説明: {description}

{f'''
【事業者からの追加情報】
{business_context}
''' if business_context else ''}
---

以下の形式で、**事業者目線で具体的かつ詳細な**ビジネスレポートを作成してください：

{maker_name} Sales Team

お世話になっております。
先日ご提案に関して、以下の貴社製品の日本市場における販売拡大可能性を調査いたしました。

{url}

フェーズ1：クラウドファンディング
フェーズ2：アマゾン等のECサイト販売
フェーズ3：日本国内主要量販店へ卸販売

【詳細な市場分析】

①日本における、クラファン及びECサイトにおける販売実績の有無

**要求事項**:
- 具体的な調査結果を記載（「現時点で確認できません」等の曖昧な表現ではなく）
- 類似製品がある場合、製品名とURLを列挙（最低3件）
- 各製品の販売実績（金額・件数）を記載
- 日本のクラウドファンディングサイト（Makuake、CAMPFIRE、GREEN FUNDING等）での実績を調査
- Amazon.co.jp、楽天市場での販売状況と価格帯
- 販売チャネルごとの市場規模感

②日本におけるクラファンにおける類似商品の販売実績額

**要求事項**:
- 最低5件の類似製品を列挙（製品名、URL、実績額、実施時期）
- 各製品の特徴と本製品との差異
- 成功事例と失敗事例の両方を含める
- 実績額の分布（最高額、最低額、中央値）
- トレンド分析（直近1年の動向）
- 市場の飽和度・競合状況の評価

例:
- 製品A「[製品名]」(Makuake): ¥XX,XXX,XXX（202X年X月）
  特徴: [...]
  本製品との差異: [...]

- 製品B「[製品名]」(CAMPFIRE): ¥XX,XXX,XXX（202X年X月）
  ...

③クラファンにおける想定販売価格帯と収益性分析

**要求事項**:
- 早割価格、通常価格、リテール価格の3段階を提案
- 各価格帯における想定支援者数
- 競合製品の価格分析（最低3件の具体例）
- 価格感度分析（高価格・中価格・低価格戦略の比較）
- 粗利率の推定（Kickstarterの$XX → 日本市場¥XX,XXX）
- 送料・関税・手数料を含めた実質利益率
- ブレークイーブンポイント（損益分岐点）

例:
- 早割（限定100名）: ¥XX,XXX（競合より15%安）
- 通常価格: ¥XX,XXX（市場平均価格）
- リテール価格: ¥XX,XXX（Amazon販売時の想定）

④日本のクラウドファンディング実施における販売予測と成功可能性

**要求事項**:
- 具体的な目標金額の提案（根拠を明示）
- 保守的/標準的/楽観的の3シナリオ予測
- 各シナリオの成功確率（%）
- 達成に必要な施策（広告費、PR戦略等）
- リスク要因の列挙（最低5項目、各項目の影響度を評価）
- タイミング戦略（実施推奨月、避けるべき時期）
- KPI設定（初日目標、1週間目標、最終目標）

例:
【保守的シナリオ】
- 目標金額: ¥XX,XXX,XXX
- 想定支援者数: XXX名
- 成功確率: XX%
- 前提条件: [...]

【標準的シナリオ】
- 目標金額: ¥XX,XXX,XXX
- ...

⑤競合優位性分析と差別化戦略

**要求事項**:
- 本製品の3つの強み（競合との明確な差別化ポイント）
- 本製品の2つの弱み（改善可能な課題）
- ターゲット顧客の明確化（年齢層、性別、ライフスタイル）
- 競合製品に勝つための具体的な戦略
- USP（独自の販売提案）の明確化

⑥フェーズ2・3への展開戦略

**要求事項**:
- Amazon・楽天での販売開始時期の提案
- 想定売上（月間・年間）
- 必要な在庫数・物流戦略
- 量販店（ヨドバシ、ビックカメラ等）への卸条件
- 長期的な市場展開ロードマップ

---

これらの結果から、貴社製品には日本市場で大きな可能性があると感じております。
また、日本のクラウドファンディングで成功を収めるためには、
いくつかの特殊事情を考慮し、以下の事項を徹底することで成功に導くことができます。
・クラウドファンディング開始前から用意周到に見込み客を獲得する。
・商品の特性を踏まえた広告を最大限行う。

私共は、日本のクラウドファンディングで成功を収めるべく
国内有数のチーム「OMP」に所属しており、これまで数多くの実績を収めております。
以下に、その取り組みや実績も照会させて頂いております。
長い動画もあり、大変恐縮に存じますが、
ご興味がございましたら、ご確認を頂ければ幸いです。

■公式ウェブサイトでも当社業務についてご確認を頂けます。
https://lifeupjp.com

■Japan's Crowdfunding Achievements
https://drive.google.com/file/d/1jUMMmlFATSFfxlxrbhrNdmIsnAtQZQ9T/view?usp=sharing

■Amazon Japan Results
https://drive.google.com/file/d/1zXLVoLLy3DEBAHgDQ0nHCtu_0xicDRMr/view?usp=sharing

■Pre-Launch Customer Acquisition Group Seminar
https://drive.google.com/file/d/1uwW_WVQxVCHVxXxDXI5YvFF5Usg-ZZFe/view?usp=sharing

■Pre-Launch Audience Acquisition & Advertising Group Seminar
https://drive.google.com/file/d/1lQ3IgFPgha6CU2nB5OCb-5ZzbjiUjDRg/view?usp=sharing

もしご希望がございましたら、より詳細な市場レポートをお送りすることもできますので、
ご用命を頂ければ幸いです。
またズームで、より詳しく説明をさせて頂きたいと存じます。
ご連絡をお待ちしております。

敬具
Koki Oshima
CEO
株式会社ライフサポート
西池袋3-11-12 池袋ガーデンコート4階〒171-0021 東京都豊島区
電話番号：090-4606-2523
メール：contact@lifeupjp.com
ウェブサイト：https://lifeupjp.com

---

【重要な指示】
1. 各分析項目について、**具体的な数値・製品名・URL**を必ず含めてください
2. 「可能性があります」「期待できます」等の曖昧な表現は避け、**定量的な根拠**を示してください
3. 競合製品は実在する製品を調査し、**最低3-5件の具体例**を挙げてください
4. 推測ではなく、**あなたの知識に基づく実在のデータ**を提供してください
5. 事業者が**すぐに意思決定できる**レベルの具体性を保ってください
6. 各価格、金額には必ず**通貨記号と桁区切り**（¥XX,XXX,XXX）を使用してください
7. 成功確率やリスク評価には**パーセンテージ**を明示してください
8. 文字数は2000-2500文字程度で、**詳細かつ簡潔に**まとめてください
"""

        return prompt

    def generate_english_report(self, kickstarter_data, maker_name, creator_name):
        """
        英語の市場分析レポートを生成

        Args:
            kickstarter_data (dict): Kickstarterから取得したデータ
            maker_name (str): メーカー名
            creator_name (str): クリエーター名

        Returns:
            str: 生成されたレポート
        """
        prompt = self._create_english_prompt(kickstarter_data, maker_name, creator_name)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )

            report = response.choices[0].message.content.strip()
            return report

        except Exception as e:
            print(f"Error generating English report: {e}")
            return f"Error: Failed to generate report ({str(e)})"

    def _create_english_prompt(self, data, maker_name, creator_name):
        """英語プロンプトを作成"""
        product_name = data.get('product_name', 'Unknown')
        url = data.get('url', '')
        pledge_amounts = data.get('pledge_amounts', 'Unknown')
        funding_total = data.get('funding_total_usd', 0)
        funding_jpy = data.get('funding_total_jpy', 0)
        backers = data.get('backers', 0)
        category = data.get('category', 'Unknown')
        description = data.get('description', '')

        prompt = f"""
Create an English version of a market analysis report for the following Kickstarter project.
The report should be professional, business-formal, and sent to the manufacturer.

---
【Product Information】
Product Name: {product_name}
Maker: {maker_name}
Creator: {creator_name}
Product URL: {url}

【Kickstarter Data】
Pledge Amounts: {pledge_amounts}
Total Funding: ${funding_total:,.2f} (approx. ¥{funding_jpy:,})
Backers: {backers:,}
Category: {category}
Description: {description}

---

Please create a report in the following format:

Dear {maker_name} Sales Team,

We hope this message finds you well.

Following up on our previous proposal, we have conducted market research on your product's potential for expansion in the Japanese market through the following phases:

{url}

Phase 1: Crowdfunding
Phase 2: E-commerce Sales (Amazon Japan, Rakuten, etc.)
Phase 3: Distribution to Major Japanese Retailers

【Market Analysis】

① Current Sales Status in Japan
(Report findings on existing crowdfunding and e-commerce presence)

② Similar Products on Japanese Crowdfunding Platforms
(Provide specific examples with funding amounts)

③ Recommended Pricing Strategy for Japanese Crowdfunding
(Suggest appropriate pricing based on Kickstarter data and Japanese market)

④ Sales Forecast and Success Potential
(Provide specific projections, success rate, and key considerations)

---

Based on these findings, we believe your product has significant potential in the Japanese market.

To ensure success on Japanese crowdfunding platforms, we recommend:
• Building a customer base before the campaign launch
• Implementing targeted advertising based on product characteristics

Our team is part of "OMP," one of Japan's leading crowdfunding agencies, with numerous successful campaigns.
Please find our achievements and case studies below:

■Official Website
https://lifeupjp.com

■Japan's Crowdfunding Achievements
https://drive.google.com/file/d/1jUMMmlFATSFfxlxrbhrNdmIsnAtQZQ9T/view?usp=sharing

■Amazon Japan Results
https://drive.google.com/file/d/1zXLVoLLy3DEBAHgDQ0nHCtu_0xicDRMr/view?usp=sharing

We would be happy to provide a more detailed market report and discuss this opportunity via Zoom at your convenience.

Looking forward to hearing from you.

Best regards,
Koki Oshima
CEO
Life Support Co., Ltd.
4F Garden Court Ikebukuro, 3-11-12 Nishi-Ikebukuro, Toshima-ku, Tokyo 〒171-0021 Japan
Phone: +81-90-4606-2523
Email: contact@lifeupjp.com
Website: https://lifeupjp.com

---

※Please fill in the 【Market Analysis】 section (①-④) with specific, detailed information.
※Use bullet points for clarity.
※Include concrete numbers and examples where possible.
"""

        return prompt


def test_improved_openai():
    """改善版OpenAI APIのテスト"""
    from dotenv import load_dotenv
    load_dotenv()

    test_data = {
        'product_name': 'Smart Coffee Mug',
        'url': 'https://www.kickstarter.com/projects/example/smart-coffee-mug',
        'pledge_amounts': '$49 (約7,350円), $79 (約11,850円), $129 (約19,350円)',
        'funding_total_usd': 456789.50,
        'funding_total_jpy': 68518425,
        'backers': 5234,
        'category': 'Product Design',
        'description': 'A temperature-controlled smart mug that keeps your beverage at the perfect temperature...'
    }

    generator = ImprovedMarketReportGenerator()

    print("=" * 80)
    print("改善版 OpenAI API Test")
    print("=" * 80)
    print("事業者目線の詳細レポートを生成中...\n")

    report_ja = generator.generate_japanese_report(
        test_data,
        maker_name='Ember Technologies',
        creator_name='Ember Team'
    )

    print(report_ja)
    print("\n" + "=" * 80)

    # トークン数の推定
    estimated_input_tokens = len(report_ja.split()) * 2  # 日本語は約2トークン/単語
    print(f"\n推定出力トークン数: 約{estimated_input_tokens}トークン")


if __name__ == '__main__':
    test_improved_openai()
