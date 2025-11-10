#!/usr/bin/env python3
"""
OpenAI API連携モジュール
Kickstarterデータをもとに市場分析レポートを生成
"""

import os
from openai import OpenAI


class MarketReportGenerator:
    """市場分析レポート生成クラス"""

    def __init__(self, api_key=None, model='gpt-4o-mini'):
        """
        Args:
            api_key (str): OpenAI APIキー（Noneの場合は環境変数から取得）
            model (str): 使用するモデル
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def generate_japanese_report(self, kickstarter_data, maker_name, creator_name):
        """
        日本語の市場分析レポートを生成

        Args:
            kickstarter_data (dict): Kickstarterから取得したデータ
            maker_name (str): メーカー名
            creator_name (str): クリエーター名

        Returns:
            str: 生成されたレポート
        """
        prompt = self._create_japanese_prompt(kickstarter_data, maker_name, creator_name)

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
            print(f"Error generating Japanese report: {e}")
            return f"エラー: レポート生成に失敗しました ({str(e)})"

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

    def _create_japanese_prompt(self, data, maker_name, creator_name):
        """日本語プロンプトを作成"""
        product_name = data.get('product_name', '不明')
        url = data.get('url', '')
        pledge_amounts = data.get('pledge_amounts', '不明')
        funding_total = data.get('funding_total_usd', 0)
        funding_jpy = data.get('funding_total_jpy', 0)
        backers = data.get('backers', 0)
        category = data.get('category', '不明')
        description = data.get('description', '')

        prompt = f"""
以下のKickstarterプロジェクトについて、日本語でメーカーに送るあいさつ文と詳細な市場分析レポートを作成してください。

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
カテゴリ: {category}
製品説明: {description}

---

以下の形式で、丁寧なビジネス文体でレポートを作成してください：

{maker_name} Sales Team

お世話になっております。
先日ご提案に関して、以下の貴社製品の日本市場における販売拡大可能性を調査いたしました。

{url}

フェーズ1：クラウドファンディング
フェーズ2：アマゾン等のECサイト販売
フェーズ3：日本国内主要量販店へ卸販売

【分析内容】

①日本における、クラファン及びECサイトにおける販売実績の有無
（現時点での調査結果を記載）

②日本によるクラファンにおける類似商品の販売実績額
（具体的な金額と製品例を記載）

③クラファンにおける想定販売価格帯
（Kickstarterの価格を参考に、日本市場での適正価格を提案）

④日本のクラウドファンディング実施における販売予測と、その後のフェーズを含む成功の可能性と評価
（具体的な予測金額と成功率、注意点を記載）

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

※上記のフォーマットに沿って、【分析内容】の①〜④を具体的に記述してください。
※可能な限り具体的な数値や事例を含めてください。

【書式に関する重要な指示】
※このレポートはメール本文として直接使用されます
※Markdown形式（**太字**、###見出し、-箇条書き等）は使用しないでください
※プレーンテキスト形式で、改行と段落のみで読みやすく整形してください
※強調したい箇所は【】または「」で囲んでください
"""

        return prompt

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


def test_openai():
    """OpenAI APIのテスト"""
    from dotenv import load_dotenv
    load_dotenv()

    # テストデータ
    test_data = {
        'product_name': 'Gulliver',
        'url': 'https://www.kickstarter.com/projects/beehivebooks/gulliver',
        'pledge_amounts': '$25 (約3,750円), $50 (約7,500円)',
        'funding_total_usd': 123456.78,
        'funding_total_jpy': 18518517,
        'backers': 1234,
        'category': 'Publishing',
        'description': 'A beautiful reimagining of Jonathan Swift\'s classic tale...'
    }

    generator = MarketReportGenerator()

    print("=" * 60)
    print("OpenAI API Test")
    print("=" * 60)
    print("Generating Japanese report...\n")

    report_ja = generator.generate_japanese_report(
        test_data,
        maker_name='Beehive Books',
        creator_name='Beehive Books Team'
    )

    print(report_ja)
    print("\n" + "=" * 60)


if __name__ == '__main__':
    test_openai()
