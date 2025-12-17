#!/usr/bin/env python3
"""
レポート生成モジュール V2（Phase 3）
収集データと計算結果を基に、15項目の評価レポートを生成

出力形式:
- プレーンテキスト（マークダウン記法なし）
- 全データに出典URL付き
- 表形式はプレーンテキストで表現
- サンプルレポートをお手本として高品質な出力を生成
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from openai import OpenAI


def filter_quality_urls(urls: list) -> list:
    """
    URLリストから検索URLを除外し、具体的なページURLのみを返す

    除外パターン:
    - 検索結果URL (amazon.co.jp/s?, google.com/search?, etc.)
    - 一般的なトップページURL (ドメインのみ)

    優先パターン:
    - 製品ページURL (/dp/, /product/, /projects/, etc.)
    - 記事ページURL (/article/, /news/, etc.)
    """
    if not urls or not isinstance(urls, list):
        return []

    quality_urls = []
    search_patterns = [
        r'/s\?',  # Amazon search
        r'/search\?',  # General search
        r'\?q=',  # Search query
        r'\?k=',  # Amazon search
        r'/search/',  # Search path
    ]

    page_patterns = [
        r'/dp/',  # Amazon product
        r'/product/',  # Product page
        r'/products/',  # Product page
        r'/projects/',  # Kickstarter/Makuake project
        r'/project/',  # CF project
        r'/article/',  # Article
        r'/news/',  # News
        r'/blog/',  # Blog
    ]

    for url in urls:
        if not url or not isinstance(url, str):
            continue

        # 検索URLは除外
        is_search = any(re.search(pattern, url) for pattern in search_patterns)
        if is_search:
            continue

        # 具体的なページURLを優先
        is_page = any(re.search(pattern, url) for pattern in page_patterns)
        if is_page:
            quality_urls.insert(0, url)  # 優先度高いものを先頭に
        else:
            quality_urls.append(url)

    # 重複除去しつつ順序維持
    seen = set()
    result = []
    for url in quality_urls:
        if url not in seen:
            seen.add(url)
            result.append(url)

    return result[:5]  # 最大5件


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

        # サンプルレポートを読み込み
        self.sample_report = self._load_sample_report()

    def _safe_num(self, value, default=0):
        """Noneや無効な値を安全に数値に変換"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            cleaned = ''.join(c for c in value if c.isdigit() or c == '.' or c == '-')
            if cleaned:
                try:
                    return float(cleaned) if '.' in cleaned else int(cleaned)
                except ValueError:
                    return default
        return default

    def _load_sample_report(self):
        """サンプルレポートをファイルから読み込む"""
        sample_path = Path(__file__).parent / "templates" / "sample_report_v2.md"
        try:
            if sample_path.exists():
                with open(sample_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                print(f"⚠️ サンプルレポートが見つかりません: {sample_path}")
                return None
        except Exception as e:
            print(f"⚠️ サンプルレポート読み込みエラー: {e}")
            return None

    def generate_report(self, collected_data, calculation_results, use_split_mode=True):
        """
        15項目評価レポートを生成

        Args:
            collected_data: DataCollectorで収集したデータ
            calculation_results: CalculationEngineで計算した結果
            use_split_mode: True=分割生成モード（高品質）、False=一括生成モード

        Returns:
            str: 生成されたレポート（プレーンテキスト）
        """
        if not self.client:
            return "エラー: OpenAI APIキーが設定されていません"

        print("\n" + "=" * 60)
        print("📝 レポート生成開始")
        print("=" * 60)

        if use_split_mode:
            return self._generate_report_split(collected_data, calculation_results)
        else:
            return self._generate_report_single(collected_data, calculation_results)

    def _generate_report_single(self, collected_data, calculation_results):
        """一括生成モード（従来方式）"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(collected_data, calculation_results)

        print(f"  プロンプト長: {len(system_prompt) + len(user_prompt):,}文字")

        try:
            print("  🤖 OpenAI API呼び出し中...")
            print("  📊 一括生成モード")

            enhanced_user_prompt = user_prompt + """

========================================
【最終確認 - 絶対遵守】
========================================
あなたの出力は【必ず8,000文字以上】でなければなりません。
サンプルレポートの各セクションの詳細度・分析の深さ・文章量を忠実に再現してください。
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_user_prompt}
                ],
                max_tokens=16000,
                temperature=0.5,
            )

            report = response.choices[0].message.content.strip()
            print(f"  ✓ レポート生成完了 ({len(report):,}文字)")

            return self._post_process(report)

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return f"レポート生成エラー: {str(e)}"

    def _generate_report_split(self, collected_data, calculation_results):
        """分割生成モード（高品質）- セクションごとに生成"""
        print("  📊 分割生成モード（高品質）")

        user_prompt = self._build_user_prompt(collected_data, calculation_results)

        # セクショングループ定義
        section_groups = [
            {
                "name": "Part 1: エグゼクティブサマリー・製品評価・価格・実績",
                "sections": ["エグゼクティブサマリー", "①", "②", "③"],
                "prompt": """
以下のセクションを詳細に出力してください。サンプルレポートと同等の品質・詳細度で。

【出力時の注意】
・セクションタイトルは「① 製品特徴・日本市場での通用度評価」のように、丸数字と項目名のみ
・「最低XXX文字」などの指示は出力に含めない

【出典記載の厳格ルール - 最重要】
・URLは「その情報が実際に記載されていたURL」のみを記載すること
・提供データに含まれる情報のみ、そのデータの出典URLを記載
・【絶対禁止】AIの推測・知識に基づく競合他社名の記載
  → 「direct_competitor_brands」「direct_competitor_products」データは使用禁止
  → 競合情報は実際の検索結果で見つかったもののみ記載可
・例:
  ○ 調達額は$1,110,820（https://www.kickstarter.com/projects/xxx）← 事実
  × 競合としてはCamRangerがある ← AI推定は禁止
  × 業界の主要プレイヤーとしては〇〇がある ← AI推定は禁止

【エグゼクティブサマリー】（レポート冒頭に必ず記載）
以下の形式で5行程度の要約を最初に出力：
---
【エグゼクティブサマリー】
・Kickstarter実績: $XX,XXX調達（バッカーXX人）
・日本市場成功確度: 高/中/低
・推奨価格帯: ¥XX,XXX〜¥XX,XXX
・利益100万円達成ライン: XX台以上
・主要リスク: （1〜2点を簡潔に）
---

① 製品特徴・日本市場での通用度評価
   【製品仕様を具体的に記載すること - 汎用的な表現は禁止】
   ・「要点（スペック/訴求）」として製品の特徴を3点以上、各点を詳細に説明
     - 必ず具体的な数値を含める（例: BLE 100ft通信、12時間バッテリー、36g軽量）
     - technical_specsデータがある場合は必ず引用
   ・「日本での通用性」として新規性/革新性/訴求力を各々200文字以上で評価
     - 第三者レビュー（DPReview、WIRED等）の評価があれば引用し、URLを記載
   ・日本市場での受容性分析
     - 【注意】AI推定の競合他社名は記載禁止
     - 実際の検索結果（Amazon、Makuake等）で見つかった競合のみ記載可
   ・キャンペーン時期の評価（campaign_yearデータがあれば技術の陳腐化リスクを評価）
   ・総括

② Kickstarter販売価格【日本展開用参考データ】
   【注意】出品者はご自身の価格設定を把握しています。長い説明は不要です。
   以下の形式で簡潔に記載:
   ・平均Pledge: $XX（約XX円）
   ・想定リテール価格: $XX（約XX円）
   ※日本市場での価格設定検討用の参考値として記載

③ 調達実績【日本展開検討の背景】
   【注意】出品者はご自身の実績を把握しています。長い説明や解説は不要です。
   以下の形式で簡潔に記載:
   ・調達額: $XX（約XX円）/ バッカー: XX人 / 達成率: XX%
   ※この実績を踏まえ、以下で日本市場での展開可能性を分析

【文字数目安】① 800字以上、②③ 各50〜100字程度（簡潔に）
"""
            },
            {
                "name": "Part 2: 日本市場調査・ターゲット分析",
                "sections": ["④", "⑤", "⑥", "⑦"],
                "prompt": """
以下のセクションを詳細に出力してください。サンプルレポートと同等の品質・詳細度で。

【出力時の注意】
・セクションタイトルは「④ 日本CFでの既出可否」のように、丸数字と項目名のみ
・「最低XXX文字」などの指示は出力に含めない

【出典記載の厳格ルール - 最重要】
・URLは「その情報が実際に記載されていたURL」のみを記載すること
・【絶対禁止】AI推定・業界知識に基づく競合他社名の記載
  → 「direct_competitor_brands」「direct_competitor_products」データは使用禁止
  → 競合情報は実際の検索結果で見つかったもののみ記載可
・実際の検索結果（amazon_jp, makuake, campfire等）から見つかった製品のみ記載可

④ 日本CFでの既出可否
   ・Makuake検索結果と分析（提供データのmakuake.source_urlを使用）
   ・CAMPFIRE検索結果と分析（提供データのcampfire.source_urlを使用）
   ・【必須】各事実の直後に実際の検索URLを記載

⑤ 日本EC（Amazon等）での既出可否
   ・同一ブランド/製品の有無を詳述（提供データのamazon_jp情報を使用）
   ・既に流通している場合はその影響と課題を分析
   ・今後の展開への示唆
   ・【必須】検索結果URLを各事実の直後にインライン記載

⑥ 日本CFにおける主要競合比較
   【最重要】実際の検索結果で見つかった競合のみ記載すること！

   ■ 直接競合の定義と判定:
   ・直接競合 = 同じ製品タイプ・同じ機能・同じターゲット層を持つ製品
   ・製品タイプが異なるものは「間接競合」として区別

   ■ 出典ルール（厳守）:
   ・【絶対禁止】「direct_competitor_brands」「direct_competitor_products」データの使用
   ・【絶対禁止】AI推定・業界知識に基づく競合他社名の記載
   ・Makuake/CAMPFIRE/Amazonで実際に見つかった競合のみ記載可
   ・検索で競合が見つからなかった場合は「直接競合は確認されなかった」と記載

   ■ 出力形式（必須）:
   1. まず「直接競合: あり/なし」を冒頭で明記
   2. 実際の検索で見つかった直接競合がある場合:
      | 製品名 | ブランド | 価格 | プラットフォーム | URL |
   3. 直接競合がない場合:
      「日本のCFプラットフォーム（Makuake/CAMPFIRE）では直接競合は確認されなかった」
   4. 「参考: カテゴリ内の他製品」として間接競合を別途記載（実際の検索結果のみ）

   ■ 禁止事項:
   ・【絶対禁止】AI推定の競合他社名の記載（CamRanger、Tether Tools等）
   ・無関係な製品（パソコン、ぬいぐるみ等）は記載しない
   ・製品カテゴリに合致しない検索結果は無視する

⑦ ターゲット顧客・マーケティング方向性
   ・想定ターゲット層（年齢層、性別、趣味嗜好、購買行動）
   ・日本市場での訴求ポイント（製品特徴から導出）
   ・推奨プロモーションチャネル（SNS、インフルエンサー、メディア等）
   ・競合との差別化メッセージ案

【文字数目安】④ 200字以上、⑤ 300字以上、⑥ 700字以上、⑦ 400字以上
"""
            },
            {
                "name": "Part 3: 独占契約・規制・FOB",
                "sections": ["⑧", "⑨", "⑩"],
                "prompt": """
以下のセクションを詳細に出力してください。サンプルレポートと同等の品質・詳細度で。

【出力時の注意】
・セクションタイトルは「⑧ 日本での独占販売契約の可能性」のように、丸数字と項目名のみ
・「最低XXX文字」などの指示は出力に含めない
・規制情報には根拠となる法令・公式情報源を記載すること

⑧ 日本での独占販売契約の可能性
   ・難易度を「高/中/低」で評価
   ・既存流通との関係を詳細に分析
   ・交渉可能な条件を具体的に提案
   ・リスクと対策

⑨ 規制（PSE/技適）
   ・PSE要否とその理由を詳述
   ・技適要否とその理由を詳述
   ・製品仕様の確認ポイントを記載
   ・費用感と期間を明記
   ・【重要】不確実性への言及
     - 製品仕様の詳細が不明な場合は「要確認」と明記
     - 例: 「電源仕様が不明のため、PSE要否は製品仕様確認後に最終判断が必要」
     - 例: 「Bluetooth機能の有無が確認できないため、技適要否はメーカー確認後に判断」
   ・注意事項

⑩ 想定仕入単価（FOB）
   ・MSRP推定根拠を明記
   ・FOB楽観/標準/悲観の3パターンを金額で記載
   ・ディストリ向け一般的な比率の説明
   ・注記として確定前の仮置きである旨を記載

【文字数目安】⑧ 400字以上、⑨ 500字以上、⑩ 300字以上
"""
            },
            {
                "name": "Part 4: 収支シミュレーション",
                "sections": ["⑪"],
                "prompt": """
以下のセクションを非常に詳細に出力してください。サンプルレポートと同等の品質・詳細度で。

【出力時の注意】
・セクションタイトルは「⑪ 収支シミュレーション（Makuake）」のように、丸数字と項目名のみ
・「最低XXX文字」「非常に重要」などの指示は出力に含めない

⑪ 収支シミュレーション（Makuake）

前提条件を明記：
・Makuake手数料: 22%（税込）
・国内配送料: 1,200円/台
・輸入諸掛: 1,500円/台
・PSE/技適: 製品による（0〜2,000円/台案分）
・為替レート

価格帯案を3パターン提示（例: 55,800円、64,800円、69,800円）

【ケース表：1台あたり粗利（円）】を表形式で出力
| 販売価格 | Makuake手数料 | 仕入$XXX(¥XX,XXX) | 仕入$XXX(¥XX,XXX) | 仕入$XXX(¥XX,XXX) | 物流他 | 技適/PSE案分 | 粗利レンジ |

【販売台数×利益（例）】の表を追加
| 価格 | 仕入 | 技適/PSE案分 | 150台 | 220台 | 300台 |

目安コメントを追加（例：「税込64,800円以上 × 200台前後で30%利益水準に近い実効」）

【文字数目安】⑪ 1000字以上
"""
            },
            {
                "name": "Part 5: 販路可能性・利益目標",
                "sections": ["⑫", "⑬", "⑭"],
                "prompt": """
以下のセクションを詳細に出力してください。サンプルレポートと同等の品質・詳細度で。

【出力時の注意】
・セクションタイトルは「⑫ 日本EC（Amazon等）での成功可能性・課題」のように、丸数字と項目名のみ
・「最低XXX文字」などの指示は出力に含めない

⑫ 日本EC（Amazon等）での成功可能性・課題
   ・可能性を詳述
   ・課題を詳述
   ・結論を「高/中/低」で明記

⑬ 量販（ドン・キホーテ等）への卸の可能性・課題
   ・可能性を詳述
   ・課題を詳述
   ・結論を「高/中/低」で明記

⑭ Makuakeで利益100万円超の可否
   ・評価を「高/中/低」で明記
   ・到達条件を3パターン以上で具体的に記載（パターンA、B、Cなど）
   ・課題を列挙

【文字数目安】⑫ 300字以上、⑬ 300字以上、⑭ 400字以上
"""
            },
            {
                "name": "Part 6: リスク分析・最終判定・まとめ",
                "sections": ["⑮", "⑯", "補足", "情報源", "まとめ"],
                "prompt": """
以下のセクションを非常に詳細に出力してください。サンプルレポートと同等の品質・詳細度で。

【出力時の注意】
・セクションタイトルは「⑮ リスク分析と対応策」のように、丸数字と項目名のみ
・「最低XXX文字」「非常に重要」などの指示は出力に含めない
・このレポートは日本市場への出品を前提とした提案書です。「見送り」という結論はありません。
・製品をどのように成功させるかを提案してください。

⑮ リスク分析と対応策
   ・市場リスク（競合参入、価格競争、需要変動）
   ・オペレーションリスク（納期遅延、品質問題、為替変動）
   ・規制リスク（認証取得の遅延、規制変更）
   ・各リスクへの具体的対応策

⑯ 最終判定（出品提案・成功戦略）
   ・Makuake成功確度:「高/中/低」で明記
   ・【成功のための必須条件】を箇条書きで4点以上
     例：「FOBを$XXX以下に交渉する」「販売価格¥XX,XXX以上を設定する」
   ・【リスク管理と対策】を箇条書きで3点以上
     例：「FOBが高い場合→セット販売で単価向上」「競合が多い場合→独自特典で差別化」
   ・成功に向けた戦略を詳述

補足：規制・手数料の根拠リンク
   ・Makuake手数料の根拠
   ・技適の根拠
   ・PSEの根拠

情報源URL一覧
   ・カテゴリ別に整理して記載

まとめ（出品に向けたアクションプラン）
   ・結論: 「出品を推奨」と明記
   ・推奨アクションを5点以上の箇条書きで記載
     【必須項目】
     1. FOB交渉目標: 「$XXX以下での交渉を目指す（利益率XX%確保のため）」
     2. 価格戦略: 「¥XX,XXX〜¥XX,XXXの価格帯で展開」
     3. 規制対応: 「PSE/技適の要否確認と対応計画」
     4. 差別化戦略: 「XXXをアピールポイントとして訴求」
     5. 販売目標: 「利益100万円達成には最低XX台（価格¥XX,XXX × XX台）」
   ・成功のポイント（条件をクリアすれば十分な利益が見込める旨を記載）

【文字数目安】⑮ 400字以上、⑯ 600字以上、補足 150字以上、まとめ 500字以上
"""
            },
        ]

        # 各セクションを生成
        all_sections = []
        total_chars = 0

        for i, group in enumerate(section_groups):
            print(f"  [{i+1}/{len(section_groups)}] {group['name']} を生成中...")

            section_system_prompt = f"""あなたは日本市場参入コンサルタントです。
Kickstarter製品の日本クラウドファンディング（主にMakuake）での展開可否を、事業者目線で厳しく評価するレポートを作成します。

【レポートの前提 - 最重要】
・このレポートの提出先は「Kickstarter出品者本人」です
・出品者は自分のKickstarterキャンペーン結果（調達額、バッカー数、達成率、価格設定など）を当然把握しています
・Kickstarter実績の詳細な説明や解説は不要です
・レポートの価値は「日本市場での展開可能性分析」にあります
・②③セクションは日本展開検討に必要な参考情報として簡潔に記載し、出品者が既知の情報を長々と説明しないこと

【重要ルール】
・データ捏造の絶対禁止 - 提供されたデータ以外の数値を絶対に使用しない
・各セクションは十分な詳細度で出力すること（目安は各プロンプト末尾を参照）
・簡潔にまとめすぎない - 詳細な分析と洞察を含めること
・プレーンテキスト形式で出力（マークダウン記法は使用しない）
・見出しは「①」「②」のように丸数字と項目名のみ（文字数指示は含めない）
・箇条書きは「・」を使用
・表は「|」で区切ったテキスト形式
・重要な情報は【】で囲んで強調

【出典記載の厳格ルール - 最重要】
・URLは「その情報が実際に記載されていたURL」のみを記載すること
・【絶対禁止】情報の出典ではないURLを記載すること（虚偽の出典）
・【絶対禁止】AI推定・業界知識に基づく競合他社名の記載
  → 「direct_competitor_brands」「direct_competitor_products」データは使用禁止
  → 競合情報は実際の検索結果（Amazon、Makuake、CAMPFIRE等）で見つかったもののみ記載可
  → 検索で見つからなかった場合は「競合は確認されなかった」と記載
・例:
  ○「調達額は$1,110,820（https://kickstarter.com/...）」← KSページに記載あり
  ○「直接競合は確認されなかった」← 検索結果になかった場合
  ×「競合としてはCamRangerがある」← AI推定は禁止
  ×「業界の主要プレイヤーとしては〇〇がある」← AI推定は禁止
"""

            section_user_prompt = f"""
{user_prompt}

========================================
【このパートで出力するセクション】
========================================
{group['prompt']}

上記セクションのみを出力してください。他のセクションは出力しないでください。
各セクションは詳細に分析し、全ての事実・数値に出典URLをインラインで付けてください。
"""

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": section_system_prompt},
                        {"role": "user", "content": section_user_prompt}
                    ],
                    max_tokens=4000,
                    temperature=0.5,
                )

                section_content = response.choices[0].message.content.strip()
                section_content = self._post_process(section_content)
                all_sections.append(section_content)
                total_chars += len(section_content)
                print(f"    ✓ 完了 ({len(section_content):,}文字)")

            except Exception as e:
                print(f"    ❌ エラー: {e}")
                all_sections.append(f"【{group['name']}の生成に失敗】")

        # 全セクションを結合
        report = "\n\n".join(all_sections)

        print(f"\n  ✓ 全セクション生成完了")
        print(f"  📊 合計文字数: {len(report):,}文字")

        return report

    def _build_system_prompt(self):
        """システムプロンプトを構築（サンプルレポートを含む）"""
        base_prompt = """あなたは日本市場参入コンサルタントです。
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

■ 類似製品・競合製品について（非常に重要）
  - 提供データの「similar_products」「category_competitors」「direct_competitor_brands」「direct_competitor_products」を参照
  - 自分の知識で類似製品を追加しない
  - 【重要】同一製品・類似製品が見つからない場合は正直に「検索結果なし」と記載
  - 【重要】CAMPFIRE/Makuakeの検索結果が製品カテゴリと無関係な場合（例: フィットネス製品を探しているのにパソコンやぬいぐるみが出てきた場合）は「関連製品なし」と記載し、無関係な製品を競合として記載しない
  - 【重要】「category_competitors」は単なるカテゴリ検索結果であり、直接競合ではない
    ・製品タイプが異なるものは直接競合ではない
    ・「⑥日本CFにおける主要競合比較」では、直接競合がない場合は「直接競合: なし」と明記し、カテゴリ内の他製品は「参考: カテゴリ内の他製品」として区別して記載すること
  - 【重要】「direct_competitor_brands」「direct_competitor_products」に記載されたブランド・製品が直接競合
    ・直接競合 = 同じ製品タイプ・同じ機能・同じターゲット層を持つ製品

■ 製品仕様の具体的記載（非常に重要）
  - 「technical_specs」データから具体的な仕様を必ず記載すること
    ・通信方式（Bluetooth LE、WiFi等）
    ・通信距離（100ft/30m等）
    ・バッテリー持続時間（12時間等）
    ・重量（36g等）
    ・対応機器（Canon/Nikon DSLR等）
  - これらの仕様は製品評価の根拠として使用する
  - 仕様が不明な場合は「仕様不明」と記載し、推測しない

■ 第三者レビュー情報の活用（非常に重要）
  - 「third_party_reviews」データがある場合、必ずレポートに引用すること
  - DPReview、WIRED、Fstoppers、The Verge等の評価を信頼性の根拠として使用
  - レビュー出典URLを必ずインライン記載
  - 例: 「DPReviewでは『初心者にも使いやすい』と評価されている（https://www.dpreview.com/...）」

■ キャンペーン時期の考慮（重要）
  - 「campaign_year」データがある場合、製品の市場投入時期を考慮した評価を行う
  - 古いキャンペーン（2015-2016年等）の場合、技術の陳腐化リスクを評価に含める

■ キャンペーンステータスについて
  - 提供データの「campaign_status」をそのまま使用する
  - 「active」「successful」「failed」「ended」以外のステータスを推測しない
  - 達成率が0%の場合、目標額が取得できていない可能性がある旨を記載

=========================================
【出力形式 - プレーンテキスト】
=========================================

1. 出力形式（プレーンテキスト）
   - マークダウン記法は使用禁止（#, **, *, - など）
   - 見出しは「① 製品特徴」のように丸数字のみを使用
   - 箇条書きは「・」を使用
   - 表は「|」で区切ったテキスト形式
   - 各セクションは空行で区切る
   - 【最重要】URLはインラインで記載 - 全ての事実に出典URLを必須で付ける
     ・調達額、バッカー数、達成率 → Kickstarter/BackerKit/KicktraqのURL
     ・Makuake検索結果 → Makuake検索URL
     ・CAMPFIRE検索結果 → CAMPFIRE検索URL
     ・Amazon検索結果 → Amazon検索URL
     ・為替レート → 出典（ExchangeRate-API等）
     例: 調達額は$143,110（https://www.kickstarter.com/projects/xxx）
     例: Makuakeで「MAXPRO」を検索したが同一製品は見つからなかった（https://www.makuake.com/discover/projects/?keyword=MAXPRO）
     例: 平均Pledge金額は$368.84（https://www.backerkit.com/projects/xxx）
   - URLなしで事実を記載することは禁止
   - レポート末尾の情報源URL一覧も残す（重複OK）

2. 評価基準
   - 「高」「中」「低」の3段階評価を使用
   - 評価には必ず根拠を添えること
   - 厳しめの評価を心がけること（楽観的な予測は禁止）

3. 金額表記
   - 為替レートを冒頭で明記（例: 1 USD ≒ 152円）
   - USDと日本円を併記（例: $143,110（約2,176万円））
   - 重要な金額は【】で囲んで強調

4. 文体
   - 敬体は使わない（である調）
   - 冗長な表現を避け、簡潔に
   - 事実と分析を明確に分ける

5. 詳細度（非常に重要）
   - 各項目は詳細な分析を含めること（サンプル参照）
   - 単なるデータの羅列ではなく、事業者目線での洞察を加える
   - 競合比較では表形式で具体的に比較
   - 収支シミュレーションは複数パターンの表を作成
   - 最終判定では「成功のための必須条件」「リスク管理と対策」を明確に記載

6. レポート構成（15項目）
   ① 製品特徴・日本市場での通用度評価
   ② Kickstarter販売価格（支援時価格）
   ③ 調達総額（実績）
   ④ 日本CFでの既出可否
   ⑤ 日本EC（Amazon等）での既出可否
   ⑥ 日本CFにおける主要競合比較
   ⑧ 日本での独占販売契約の可能性
   ⑨ 規制（PSE/技適）
   ⑩ 想定仕入単価（FOB）
   ⑪ 収支シミュレーション（Makuake）
   ⑫ 日本EC（Amazon等）での成功可能性
   ⑬ 量販（ドンキ等）への卸の可能性
   ⑭ Makuakeで利益100万円超の可否
   ⑮ 最終判定"""

        # サンプルレポートを追加（存在する場合）
        if self.sample_report:
            return base_prompt + """

=========================================
【お手本サンプルレポート - 必ず同等の品質で出力】
=========================================

【最重要指示】
以下のサンプルレポートは約12,000文字です。あなたの出力もサンプルと同等の
【品質・詳細度・分析の深さ・文章量】を必ず再現してください。
簡潔にまとめすぎないこと。各セクションを十分に詳しく書くこと。

【出力形式の変換ルール】
サンプルはマークダウン形式ですが、出力は必ずプレーンテキストに変換すること。
- # 見出し → 「① 見出し」（丸数字と項目名のみ、文字数指示は含めない）
- **太字** → 【太字】（隅付き括弧）
- * 箇条書き → ・箇条書き
- | 表 | → | 表 |（そのまま維持）
- [リンク](URL) → (URL)
- > 引用 → そのまま「> 」で記載

【重要】セクションタイトルには「最低XXX文字」「非常に重要」などの指示を含めないこと。
例: ○「① 製品特徴・日本市場での通用度評価」 ×「① 製品特徴（最低500文字）」

【各セクションの必須要件】

① 製品特徴・日本市場での通用度評価
   ・「要点（スペック/訴求）」として製品の特徴を3点以上詳述
   ・「日本での通用性」として新規性/革新性/訴求力を各々詳細に評価
   ・総括として評価を明記

② Kickstarter販売価格
   ・平均Pledge金額を明記（出典URLをインライン記載）
   ・想定リテール価格を推定
   ・価格帯の根拠を説明

③ 調達総額
   ・金額、人数、達成率を明記
   ・【重要】出典URLをインライン記載（例: 達成率957%（https://...））

④ 日本CFでの既出可否
   ・Makuake/CAMPFIRE両方の検索結果を記載
   ・【重要】各検索結果URLをインラインで記載

⑤ 日本EC（Amazon等）での既出可否
   ・同一ブランド/製品の有無を詳述
   ・既に流通している場合はその影響を分析
   ・【重要】Amazon検索URLをインラインで記載

⑥ 日本CFにおける主要競合比較
   ・【最重要】まず「直接競合: あり/なし」を明記
   ・直接競合がない場合は「同一タイプの製品は確認されなかった」と記載
   ・カテゴリ検索結果は「参考: カテゴリ内の他製品」として記載
   ・表には必ずURLを含める（製品名/調達額/達成率/URL）
   ・無関係な製品は記載しない

⑧ 日本での独占販売契約の可能性
   ・難易度を評価
   ・既存流通との関係を分析
   ・交渉可能な条件を提案

⑨ 規制（PSE/技適）
   ・PSE要否とその理由を詳述
   ・技適要否とその理由を詳述
   ・製品仕様の確認ポイントを記載
   ・費用感を明記
   ・【重要】製品仕様が不明な場合は「要確認」と明記し、不確実性を言及すること

⑩ 想定仕入単価（FOB）
   ・MSRP推定根拠を明記
   ・FOB楽観/標準/悲観の3パターンを金額で記載
   ・注記として確定前の仮置きである旨を記載

⑪ 収支シミュレーション（Makuake）
   ・前提条件を明記（手数料、送料、為替、仕入レンジ）
   ・価格帯案を3パターン提示
   ・【ケース表：1台あたり粗利】を表形式で出力
   ・【販売台数×利益】の表を追加（150台/220台/300台など）
   ・目安コメントを追加

⑫ 日本EC（Amazon等）での成功可能性・課題
   ・可能性と課題を分けて記載
   ・結論を明記

⑬ 量販（ドン・キホーテ等）への卸の可能性・課題
   ・可能性と課題を分けて記載
   ・結論を明記

⑭ Makuakeで利益100万円超の可否
   ・評価を明記
   ・到達条件を3パターン以上で具体的に記載
   ・課題を列挙

⑮ 最終判定（出品提案・成功戦略）
   ※このレポートは出品を前提とした提案書。「見送り」結論は不可。
   ・Makuake成功確度を明記
   ・【成功のための必須条件】を箇条書きで4点以上（具体的な数値条件を含む）
     例: 「FOBを$XXX以下に交渉」「税込¥XX,XXX以上で販売」「XX台以上を販売」
   ・【リスク管理と対策】を箇条書きで3点以上
     例: 「FOBが高い場合→セット販売で単価向上」「競合多い場合→限定特典で差別化」
   ・成功に向けた戦略を詳述

補足：規制・手数料の根拠リンク
   ・Makuake手数料の根拠
   ・技適の根拠
   ・PSEの根拠

情報源URL一覧
   ・カテゴリ別に整理して記載

まとめ（出品に向けたアクションプラン）
   ・レコメンドを明記
   ・推奨アクションを5点以上の箇条書きで記載（収集データに基づく製品固有のアクション）
     必須: FOB交渉目標、価格戦略、規制対応、競合対策、販売目標の各具体的数値
   ・最終コメント（Go/NG判断の具体的条件を含む）

【出典URL記載の徹底】
・全ての事実・数値の直後に出典URLをインライン記載すること
・例: 「調達額は$1,110,820、達成率2222%（https://www.kickstarter.com/projects/xxx）」
・例: 「Amazon.co.jpで¥14,800で販売中（https://www.amazon.co.jp/dp/xxx）」

<sample_report>
""" + self.sample_report + """
</sample_report>

【再確認】
上記サンプルと同等の【品質・詳細度・文章量】で出力すること。
サンプルの数値やURLは使用せず、提供データのみを使用すること。
出力はプレーンテキスト形式とすること。
セクションタイトルに文字数指示を含めないこと。"""
        else:
            return base_prompt

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
        cat_comp = collected_data.get("category_competitors", {})  # カテゴリ競合

        calc = calculation_results
        ks_stats = calc.get("kickstarter_stats", {})
        fob_est = calc.get("fob_estimate", {})
        prices = calc.get("price_recommendations", [])
        sims = calc.get("simulations", [])
        profit_analysis = calc.get("profit_target_analysis", {})
        regulations = calc.get("regulation_assessment", {})  # 規制判定結果

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
調達額: ${self._safe_num(ks_stats.get("funding_amount_usd")):,}（約{self._safe_num(ks_stats.get("funding_amount_jpy")):,}円）
目標額: {f"${self._safe_num(ks_stats.get('goal_amount_usd')):,}（約{self._safe_num(ks_stats.get('goal_amount_jpy')):,}円）" if ks_stats.get("goal_amount_usd") else "データ未取得"}
達成率: {f"{self._safe_num(ks_stats.get('percent_funded'))}%" if ks_stats.get("goal_amount_usd") and ks_stats.get("percent_funded") else "目標額未取得のため算出不可（調達額とバッカー数のみ参照）"}
バッカー数: {self._safe_num(ks_stats.get("backers_count")):,}人
平均Pledge: ${self._safe_num(ks_stats.get("average_pledge_usd")):.2f}（約{self._safe_num(ks_stats.get("average_pledge_jpy")):,}円）
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

        # カテゴリ別競合製品（より広い検索結果）
        if cat_comp:
            prompt += f"""
【6-2. カテゴリ別競合製品（日本CF）】
検索キーワード: {cat_comp.get("search_keywords", [])}
"""
            mk_cat_products = cat_comp.get("makuake", [])
            cf_cat_products = cat_comp.get("campfire", [])

            if mk_cat_products:
                prompt += "\nMakuake（カテゴリ検索）:\n"
                for p in mk_cat_products[:5]:
                    prompt += f"  ・{p.get('title', '')[:50]} / 調達額:{self._safe_num(p.get('funding_amount_jpy')):,}円 / {self._safe_num(p.get('percent_funded'))}%達成\n"
                    prompt += f"    キーワード: {p.get('search_keyword', '')} / URL: {p.get('url', '')}\n"
            else:
                prompt += "\nMakuake（カテゴリ検索）: なし\n"

            if cf_cat_products:
                prompt += "\nCAMPFIRE（カテゴリ検索）:\n"
                for p in cf_cat_products[:5]:
                    prompt += f"  ・{p.get('title', '')[:50]} / 調達額:{self._safe_num(p.get('funding_amount_jpy')):,}円 / {self._safe_num(p.get('percent_funded'))}%達成\n"
                    prompt += f"    キーワード: {p.get('search_keyword', '')} / URL: {p.get('url', '')}\n"
            else:
                prompt += "\nCAMPFIRE（カテゴリ検索）: なし\n"

        # Kickstarter価格帯（rewards）
        rewards = ks_data.get("rewards", [])
        if rewards:
            prompt += "\n【Kickstarter価格帯（rewards）】\n"
            for r in rewards[:5]:
                prompt += f"  ・${r.get('price_usd', 0)}: {r.get('title', '')[:50]}... (バッカー: {r.get('backers', 0)}人)\n"
        else:
            prompt += "\n【Kickstarter価格帯】\nリワード詳細データなし（価格はKickstarterページでご確認ください）\n"

        # Web調査結果（OpenAI APIによる詳細調査）
        web_research = collected_data.get("web_research", {})
        if web_research and "error" not in web_research:
            prompt += self._format_web_research_data(web_research)

        # FOB推定
        if fob_est and "error" not in fob_est:
            prompt += f"""
【7. FOB（仕入単価）推定】
MSRP（推定）: ${self._safe_num(fob_est.get("msrp_usd")):.2f}（約{self._safe_num(fob_est.get("msrp_jpy")):,}円）
MSRP根拠: {fob_est.get("msrp_source", "")}
FOB楽観（40%）: ${self._safe_num(fob_est.get("fob_low", {}).get("usd")):.2f}（約{self._safe_num(fob_est.get("fob_low", {}).get("jpy")):,}円）
FOB標準（47.5%）: ${self._safe_num(fob_est.get("fob_mid", {}).get("usd")):.2f}（約{self._safe_num(fob_est.get("fob_mid", {}).get("jpy")):,}円）
FOB悲観（55%）: ${self._safe_num(fob_est.get("fob_high", {}).get("usd")):.2f}（約{self._safe_num(fob_est.get("fob_high", {}).get("jpy")):,}円）
"""
        else:
            prompt += "\n【7. FOB推定】\nデータ不足のため推定不可\n"

        # 推奨価格
        if prices:
            prompt += "\n【8. 推奨販売価格（税込）】\n"
            for p in prices:
                prompt += f"  {p.get('label', '')}: ¥{self._safe_num(p.get('price_jpy')):,}\n"

        # 収支シミュレーション
        if sims:
            prompt += "\n【9. 収支シミュレーション（1台あたり）】\n"
            prompt += "| 価格タイプ | 仕入タイプ | 販売価格 | 仕入原価 | 粗利 | 利益率 |\n"
            for sim in sims:
                prompt += f"| {sim.get('price_label', '')} | {sim.get('fob_label', '')} | ¥{self._safe_num(sim.get('price_jpy')):,} | ¥{self._safe_num(sim.get('fob_jpy')):,} | ¥{self._safe_num(sim.get('gross_profit')):,} | {self._safe_num(sim.get('profit_margin'))}% |\n"

        # 利益目標分析
        if profit_analysis.get("best_case"):
            best = profit_analysis["best_case"]
            prompt += f"""
【10. 利益100万円達成分析】
ベストケース: {best.get('price_label', '')} × {best.get('fob_label', '')}
1台あたり粗利: ¥{self._safe_num(best.get('gross_profit_per_unit')):,}
必要台数: {self._safe_num(best.get('units_needed'))}台
必要調達額: 約{best.get('total_revenue_formatted', '')}
"""

        # 規制情報
        if regulations:
            pse = regulations.get("pse", {})
            telec = regulations.get("telec", {})
            prompt += f"""
【11. 規制判定結果（自動推定）】
製品カテゴリ: {regulations.get("product_category", "不明")}

PSE（電気用品安全法）:
  要否: {pse.get("required", "不明")}
  理由: {pse.get("reason", "")}
  種別: {pse.get("type", "")}
  推定費用: {self._safe_num(pse.get("estimated_cost_jpy")):,}円
  備考: {pse.get("notes", "")}

技適（技術基準適合証明）:
  要否: {telec.get("required", "不明")}
  理由: {telec.get("reason", "")}
  推定費用: {self._safe_num(telec.get("estimated_cost_jpy")):,}円
  備考: {telec.get("notes", "")}

総合推奨: {regulations.get("recommendation", "")}
"""

        # 固定コスト情報
        prompt += """
【固定情報】
・Makuake手数料: 22%（税込）
・国内配送料: 約1,200円/台
・輸入諸掛: 約1,500円/台（国際送料・通関等）
・PSE/技適: 製品による（0〜2,000円/台相当を案分、別途認証費用は初期コスト）

==================================================
【出力指示 - 必ず守ること】
==================================================

以下の16項目（①〜⑯）で評価レポートを作成してください。冒頭にエグゼクティブサマリーを必ず記載。

■ 必須ルール（違反厳禁）
1. 各項目には必ず【評価: 高/中/低】を入れてください
2. 推測で数値を作らない（「〜と思われる」で数字を作ることも禁止）
3. URLは提供されたもののみを記載
4. 各項目は3行以上の分析を含めること
5. 類似製品は提供されたリストのもののみを使用
6. ツール・システムの都合によるエラーメッセージは絶対に出力しない
7. 冒頭に必ず【エグゼクティブサマリー】を記載すること（下記参照）

■ 【エグゼクティブサマリー】の必須項目（レポート冒頭に必ず記載）
以下の形式で5行程度の要約を冒頭に記載：
---
【エグゼクティブサマリー】
・Kickstarter実績: $XX,XXX調達（バッカーXX人）
・日本市場成功確度: 高/中/低
・推奨価格帯: ¥XX,XXX〜¥XX,XXX
・利益100万円達成ライン: XX台以上
・主要リスク: （1〜2点を簡潔に）
---

■ 特に注意すべき点
- 「Kickstarter販売価格」: rewardsデータがない場合は「価格詳細: Kickstarterページでご確認ください」と記載
- 「調達総額」: 達成率が不明な場合は調達額とバッカー数のみ記載し、達成率には言及しない
- 「類似製品比較」: 提供リストが空の場合は「検索で直接競合は確認されなかった」と記載
- 「Amazon検索結果」: productsが空の場合は「同一ブランドの商品は検出されなかった」と記載

① 製品特徴・日本市場での通用度評価
   - 製品スペック・訴求ポイント（タイトルと説明文から抽出）
   - 新規性・革新性・訴求力（各:高/中/低）
   - 日本市場での受容性分析（市場需要、価格帯の妥当性等）
   - 総合評価

② Kickstarter販売価格（支援時価格）
   - 平均Pledge金額（提供データのみ使用）
   - 推定MSRP（定価）= 平均Pledge × 1.35の計算根拠を明記
   - リワード価格詳細がデータにない場合は「Kickstarterページでご確認ください」と記載

③ 調達総額（実績）
   - 調達額、バッカー数、達成率（提供データそのまま）
   - キャンペーン状態（active/successful等）
   - 【重要】出典URLをインライン記載（例: 達成率957%（https://...））
   - 達成率が0%または不明の場合は達成率に言及せず、調達額とバッカー数のみ記載

④ 日本CFでの既出可否（同一メーカー/同一製品）
   - Makuake検索結果: 同一製品の有無を明記
   - CAMPFIRE検索結果: 同一製品の有無を明記
   - 【重要】各検索結果URLを事実の直後にインライン記載

⑤ 日本EC（Amazon等）での既出可否
   - Amazon.co.jp検索結果（提供データのproductsリストを使用）
   - 同一ブランド/製品の有無
   - 【重要】検索URLをインライン記載

⑥ 日本CFにおける主要競合比較
   【最重要】直接競合とカテゴリ内製品を明確に区別すること！

   ■ 直接競合の判定:
   - 直接競合 = 同じ製品タイプ・同じ機能・同じターゲット層
   - 直接競合 = 同じ製品タイプ・同じ機能・同じターゲット層を持つ製品のみ
   - 製品タイプが異なるものは「間接競合」または「カテゴリ内の他製品」

   ■ 出力形式:
   - まず「直接競合: あり/なし」を明記
   - 直接競合がない場合: 「同一タイプの製品はMakuake/CAMPFIREで確認されなかった」と記載
   - カテゴリ検索で見つかった製品は「参考: 同カテゴリの他製品」として別途記載
   - 表には必ずURLを含める（製品名、調達額、達成率、URL）

   ■ 注意:
   - CAMPFIRE検索結果が製品と無関係な場合（パソコン、ぬいぐるみ等）は記載しない
   - 「競合」という言葉を使う場合は、本当に競合かどうか確認すること

⑦ ターゲット顧客・マーケティング方向性
   - 想定ターゲット層（年齢層、性別、趣味嗜好、購買行動）
   - 日本市場での訴求ポイント（製品特徴から導出）
   - 推奨プロモーションチャネル（SNS、インフルエンサー、メディア等）
   - 競合との差別化メッセージ案

⑧ 日本での独占販売契約の可能性
   - 既存流通状況からの分析
   - Amazon/日本CFでの取扱状況を根拠に評価
   - 交渉難易度

⑨ 規制（PSE/技適）
   - 製品カテゴリに基づく規制要件の推定
   - 電気製品の場合: PSE要否
   - 無線機能ありの場合: 技適要否
   - 必要な認証と費用感
   - 【重要】製品仕様が不明確な場合は「要確認」と明記
     例: 「電源仕様が未確認のため、PSE要否は製品仕様確認後に判断」

⑩ 想定仕入単価（FOB）
   - MSRP推定根拠を明記
   - FOB楽観/標準/悲観の3パターン（提供データ使用）

⑪ 収支シミュレーション（Makuake）
   【重要】提供されたシミュレーションデータを必ず表形式で出力すること！
   - 以下の形式で9パターン全てを記載:
     | 価格タイプ | 仕入タイプ | 販売価格 | 仕入原価 | 粗利 | 利益率 |
     | 競争力重視 | 楽観 | ¥XX,XXX | ¥XX,XXX | ¥X,XXX | XX.X% |
     ...
   - コスト内訳（Makuake手数料22%、国内配送1,200円、輸入諸掛1,500円）
   - 推奨価格帯とその理由（利益率と市場性のバランス）

⑫ 日本EC（Amazon等）での成功可能性・課題
   - 市場性評価
   - 具体的な課題（競合、価格、認知度等）

⑬ 量販（ドン・キホーテ等）への卸の可能性・課題
   - 卸価格帯の検討
   - 量販店向けの課題

⑭ Makuakeで利益100万円超の可否
   - 達成条件（価格×台数）を具体的に記載
   - 達成難易度の評価

⑮ リスク分析と対応策
   - 市場リスク（競合参入、価格競争、需要変動）
   - オペレーションリスク（納期遅延、品質問題、為替変動）
   - 規制リスク（認証取得の遅延、規制変更）
   - 各リスクへの具体的対応策

⑯ 最終判定（出品提案・成功戦略）【このレポートは出品を前提とした提案書です】
   ※「見送り」という結論は不可。製品を日本市場で成功させるための戦略を提案すること。
   - Makuake成功確度: 高/中/低（低でも出品を推奨。成功への道筋を示す）
   - 成功のための必須条件（【具体的な数値条件を必ず含めること】）
     ・FOB交渉目標: 利益率15%以上を確保できるFOB価格（シミュレーション結果から算出）
     ・推奨販売価格: 損益分岐点を超える価格（例: ¥XX,XXX以上）
     ・目標販売台数: 利益100万円達成に必要な台数（例: XX台以上）
     ・競合差別化: 具体的な差別化ポイント（価格差、機能差など）
   - リスク管理と対策（【リスクを認識した上での対応策を必ず含めること】）
     ・FOBリスク: FOBが$XXX超の場合の対応策（交渉戦略、仕様変更など）
     ・競合リスク: 競合価格が¥XX,XXX以下の場合の差別化戦略
     ・規制リスク: 認証費用が高額な場合のコスト分散策
   - 推奨アクション（収集したデータに基づく【製品固有の】具体的なステップ）
     ・Amazon競合対策: 「Amazonで¥XX,XXXで販売されているため、限定特典や早期割引で差別化」
     ・規制対応計画: 「PSE/技適認証のため、XXヶ月の準備期間を確保」
     ・FOB交渉戦略: 「利益確保のため、$XXX以下でのFOB交渉を優先」
     ・販売促進策: 具体的なプロモーション施策

最後に「情報源URL一覧」として、提供されたURLのみをリストアップしてください。
"""
        return prompt

    def _format_web_research_data(self, web_research):
        """Web調査結果をプロンプト用にフォーマット"""
        prompt = """

==================================================
【Web調査結果（OpenAI APIによる詳細調査）】
==================================================
"""
        # 製品分析結果（カテゴリ・競合ブランド情報）
        product_analysis = web_research.get("product_analysis", {})
        if product_analysis:
            prompt += "\n【製品分析結果】\n"
            prompt += f"ブランド名: {product_analysis.get('brand_name', '不明')}\n"
            prompt += f"製品タイプ: {product_analysis.get('product_type', '不明')}\n"
            prompt += f"カテゴリ: {product_analysis.get('category', '不明')}\n"
            prompt += f"サブカテゴリ: {product_analysis.get('subcategory', '不明')}\n"
            if product_analysis.get("campaign_year"):
                prompt += f"キャンペーン年: {product_analysis['campaign_year']}\n"

            # 技術仕様（非常に重要）
            tech_specs = product_analysis.get("technical_specs", {})
            if tech_specs:
                prompt += "\n【技術仕様（具体的数値）】\n"
                if tech_specs.get("connectivity"):
                    prompt += f"  ・通信方式: {tech_specs['connectivity']}\n"
                if tech_specs.get("range"):
                    prompt += f"  ・通信距離: {tech_specs['range']}\n"
                if tech_specs.get("battery_life"):
                    prompt += f"  ・バッテリー: {tech_specs['battery_life']}\n"
                if tech_specs.get("weight"):
                    prompt += f"  ・重量: {tech_specs['weight']}\n"
                if tech_specs.get("compatibility"):
                    prompt += f"  ・互換性: {tech_specs['compatibility']}\n"
                if tech_specs.get("other_specs"):
                    for spec in tech_specs["other_specs"][:5]:
                        prompt += f"  ・{spec}\n"

            # 直接競合ブランド・製品（非常に重要）
            direct_brands = product_analysis.get("direct_competitor_brands", [])
            direct_products = product_analysis.get("direct_competitor_products", [])
            if direct_brands or direct_products:
                prompt += "\n【直接競合情報（重要）】\n"
                if direct_brands:
                    prompt += f"直接競合ブランド: {', '.join(direct_brands)}\n"
                if direct_products:
                    prompt += f"直接競合製品: {', '.join(direct_products)}\n"

            # キーワード
            if product_analysis.get("search_keywords"):
                prompt += f"検索キーワード: {', '.join(product_analysis['search_keywords'][:5])}\n"

        # Kickstarter詳細情報
        ks_details = web_research.get("kickstarter_details", {})
        if ks_details and "raw_text" not in ks_details:
            prompt += "\n【Kickstarter詳細情報（Web調査）】\n"
            if ks_details.get("product_specs"):
                specs = ks_details["product_specs"]
                prompt += f"製品仕様:\n"
                prompt += f"  ・重量: {specs.get('weight', '不明')}\n"
                prompt += f"  ・最大抵抗: {specs.get('max_resistance', '不明')}\n"
                if specs.get("features"):
                    prompt += f"  ・特徴: {', '.join(specs['features'][:5])}\n"
            if ks_details.get("price_tiers"):
                prompt += "価格帯:\n"
                for tier in ks_details["price_tiers"][:5]:
                    if isinstance(tier, dict):
                        prompt += f"  ・{tier.get('tier_name', '')}: ${tier.get('price_usd', 0)}\n"
                    elif isinstance(tier, str):
                        prompt += f"  ・{tier}\n"
            if ks_details.get("sources"):
                filtered_sources = filter_quality_urls(ks_details['sources'])
                if filtered_sources:
                    prompt += f"情報源: {', '.join(filtered_sources[:3])}\n"

        # 公式サイト・SNS情報
        official_info = web_research.get("official_info", {})
        if official_info and "raw_text" not in official_info:
            prompt += "\n【公式サイト・SNS情報】\n"
            if official_info.get("official_website"):
                website = official_info["official_website"]
                prompt += f"公式サイト: {website.get('url', '不明')}\n"
                if website.get("msrp_usd"):
                    prompt += f"  ・公式MSRP: ${website['msrp_usd']}\n"
                if website.get("app_connectivity"):
                    prompt += f"  ・アプリ連携: {website['app_connectivity']}\n"
                if website.get("bluetooth"):
                    prompt += f"  ・Bluetooth: {website['bluetooth']}\n"
            if official_info.get("social_media"):
                social = official_info["social_media"]
                if social.get("instagram", {}).get("followers"):
                    prompt += f"Instagram: フォロワー{self._safe_num(social['instagram']['followers']):,}人\n"
                if social.get("youtube", {}).get("url"):
                    prompt += f"YouTube: {social['youtube']['url']}\n"
            if official_info.get("brand_info"):
                brand = official_info["brand_info"]
                prompt += f"ブランド情報: {brand.get('company_name', '不明')} ({brand.get('country', '不明')})\n"

            # 技術スペック（公式サイトから取得）
            tech_specs = official_info.get("tech_specs", {})
            if tech_specs:
                prompt += "\n【製品技術スペック（公式情報）】\n"
                spec_items = [
                    ("connectivity", "通信方式"),
                    ("wireless_range", "通信距離"),
                    ("battery_life", "バッテリー持続時間"),
                    ("battery_type", "バッテリー種別"),
                    ("weight", "重量"),
                    ("dimensions", "寸法"),
                    ("compatibility", "対応機種"),
                    ("water_resistance", "防水性能"),
                ]
                for key, label in spec_items:
                    if tech_specs.get(key) and tech_specs[key] not in ["不明", "null", None, ""]:
                        prompt += f"  ・{label}: {tech_specs[key]}\n"
                if tech_specs.get("app_features"):
                    features = tech_specs["app_features"]
                    if isinstance(features, list) and features:
                        prompt += f"  ・アプリ機能: {', '.join(features[:5])}\n"
                if tech_specs.get("other_specs"):
                    other = tech_specs["other_specs"]
                    if isinstance(other, dict):
                        for k, v in list(other.items())[:3]:
                            if v and v not in ["不明", "null", None, ""]:
                                prompt += f"  ・{k}: {v}\n"

            # 第三者レビュー（非常に重要）
            third_party_reviews = official_info.get("third_party_reviews", [])
            if third_party_reviews:
                prompt += "\n【第三者レビュー（引用推奨）】\n"
                for review in third_party_reviews[:5]:
                    prompt += f"  ・{review.get('source', '不明')}: {review.get('title', '')[:60]}\n"
                    prompt += f"    URL: {review.get('url', '')}\n"
                    if review.get("rating"):
                        prompt += f"    評価: {review['rating']}\n"
                    if review.get("price_mentioned"):
                        prompt += f"    記載価格: {review['price_mentioned']}\n"
                    if review.get("key_points"):
                        prompt += f"    要点: {', '.join(review['key_points'][:3])}\n"

            # Kickstarter価格情報
            ks_pricing = official_info.get("kickstarter_pricing", {})
            if ks_pricing:
                prompt += "\n【Kickstarter価格情報】\n"
                if ks_pricing.get("early_bird_price_usd"):
                    prompt += f"  ・Early Bird: ${ks_pricing['early_bird_price_usd']}\n"
                if ks_pricing.get("retail_price_usd"):
                    prompt += f"  ・Retail: ${ks_pricing['retail_price_usd']}\n"
                if ks_pricing.get("price_source_url"):
                    prompt += f"  ・出典: {ks_pricing['price_source_url']}\n"

            if official_info.get("sources"):
                filtered_sources = filter_quality_urls(official_info['sources'])
                if filtered_sources:
                    prompt += f"情報源: {', '.join(filtered_sources[:3])}\n"

        # Amazon.co.jp流通状況（Web調査）
        amazon_web = web_research.get("amazon_japan", {})
        if amazon_web and "raw_text" not in amazon_web:
            prompt += "\n【Amazon.co.jp流通状況（Web調査）】\n"
            prompt += f"ブランド日本流通: {'あり' if amazon_web.get('brand_exists_in_japan') else 'なし'}\n"
            prompt += f"同一製品発見: {'あり' if amazon_web.get('same_product_found') else 'なし'}\n"
            if amazon_web.get("products_found"):
                prompt += "発見製品:\n"
                for p in amazon_web["products_found"][:5]:
                    prompt += f"  ・{p.get('product_name', '')[:40]} / ¥{self._safe_num(p.get('price_jpy')):,} / "
                    prompt += f"評価{self._safe_num(p.get('rating'))} / レビュー{self._safe_num(p.get('review_count'))}件\n"
                    prompt += f"    販売元: {p.get('seller_type', '不明')} / URL: {p.get('url', '')}\n"
            if amazon_web.get("market_analysis"):
                prompt += f"市場分析: {amazon_web['market_analysis']}\n"

        # 日本CF競合製品（Web調査）
        cf_competitors = web_research.get("japan_cf_competitors", {})
        if cf_competitors and "raw_text" not in cf_competitors:
            prompt += "\n【日本CF競合製品（Web調査）】\n"
            if cf_competitors.get("same_product_found"):
                sp = cf_competitors["same_product_found"]
                prompt += f"同一製品: Makuake{'あり' if sp.get('makuake') else 'なし'} / CAMPFIRE{'あり' if sp.get('campfire') else 'なし'}\n"
                if sp.get("details"):
                    prompt += f"  詳細: {sp['details']}\n"
            if cf_competitors.get("competitors"):
                prompt += "競合製品:\n"
                for c in cf_competitors["competitors"][:8]:
                    # 文字列の場合は数値に変換（「不明」等の非数値文字列にも対応）
                    funding = self._safe_num(c.get('funding_amount_jpy'))
                    price = self._safe_num(c.get('price_jpy'))
                    prompt += f"  ・{c.get('product_name', '')[:40]} ({c.get('platform', '')})\n"
                    prompt += f"    調達額: ¥{funding:,} / 達成率: {self._safe_num(c.get('percent_funded'))}%\n"
                    prompt += f"    価格: ¥{price:,} / 特徴: {c.get('features', '')[:50]}\n"
                    prompt += f"    URL: {c.get('url', '')}\n"
            if cf_competitors.get("category_analysis"):
                prompt += f"カテゴリ分析: {cf_competitors['category_analysis']}\n"
            if cf_competitors.get("differentiation_points"):
                prompt += f"差別化ポイント: {', '.join(cf_competitors['differentiation_points'][:5])}\n"

        # Amazon.co.jpカテゴリ競合製品（Web調査）
        amazon_competitors = web_research.get("amazon_category_competitors", {})
        if amazon_competitors:
            prompt += "\n【Amazon.co.jp競合製品（カテゴリ検索）】\n"
            amazon_comps = amazon_competitors.get("amazon_competitors", [])
            if amazon_comps:
                prompt += "競合製品一覧:\n"
                for c in amazon_comps[:8]:
                    price = self._safe_num(c.get('price_jpy'))
                    prompt += f"  ・{c.get('product_name', '')[:50]}\n"
                    prompt += f"    ブランド: {c.get('brand', '不明')} / 価格: ¥{price:,}\n"
                    if c.get('price_range'):
                        prompt += f"    価格帯: {c.get('price_range')}\n"
                    if c.get('key_features'):
                        features = c.get('key_features', [])
                        if isinstance(features, list) and features:
                            prompt += f"    特徴: {', '.join(features[:3])}\n"
                    prompt += f"    関連度: {c.get('relevance', '不明')} / URL: {c.get('url', '')}\n"
            if amazon_competitors.get("market_price_range"):
                mpr = amazon_competitors["market_price_range"]
                prompt += f"市場価格帯: ¥{self._safe_num(mpr.get('low')):,}〜¥{self._safe_num(mpr.get('high')):,}（平均: ¥{self._safe_num(mpr.get('average')):,}）\n"
            if amazon_competitors.get("market_analysis"):
                prompt += f"競合分析: {amazon_competitors['market_analysis']}\n"

        # 規制情報（Web調査）
        regulations = web_research.get("regulations", {})
        if regulations and "raw_text" not in regulations:
            prompt += "\n【規制情報（Web調査）】\n"
            if regulations.get("pse"):
                pse = regulations["pse"]
                prompt += f"PSE: {pse.get('required', '不明')}\n"
                prompt += f"  理由: {pse.get('reason', '')}\n"
                prompt += f"  種別: {pse.get('type', '')}\n"
                prompt += f"  費用: {pse.get('estimated_cost_jpy', '')}\n"
            if regulations.get("telec"):
                telec = regulations["telec"]
                prompt += f"技適: {telec.get('required', '不明')}\n"
                prompt += f"  理由: {telec.get('reason', '')}\n"
                prompt += f"  費用: {telec.get('estimated_cost_usd', '')}\n"
                prompt += f"  認証モジュール: {telec.get('certified_module_option', '')}\n"
            if regulations.get("recommendation"):
                prompt += f"推奨事項: {regulations['recommendation']}\n"

        # 為替・市場情報（Web調査）
        market_info = web_research.get("market_info", {})
        if market_info and "raw_text" not in market_info:
            prompt += "\n【市場情報（Web調査）】\n"
            if market_info.get("exchange_rate"):
                fx = market_info["exchange_rate"]
                prompt += f"為替レート: $1 = ¥{fx.get('usd_jpy', 150)} (as of {fx.get('as_of', '不明')})\n"
            if market_info.get("japan_market"):
                jm = market_info["japan_market"]
                prompt += f"日本市場情報:\n"
                prompt += f"  ・市場規模: {jm.get('market_size_jpy', '不明')}\n"
                prompt += f"  ・成長率: {jm.get('growth_rate', '不明')}\n"
                if jm.get("trends"):
                    prompt += f"  ・トレンド: {', '.join(jm['trends'][:3])}\n"
            if market_info.get("makuake_fees"):
                fees = market_info["makuake_fees"]
                prompt += f"Makuake手数料: {fees.get('total_fee_percent', 22)}%（税込）\n"

        return prompt

    def _post_process(self, report):
        """レポートの後処理（マークダウンをプレーンテキストに変換）"""
        # **太字** → 【太字】
        report = re.sub(r'\*\*([^*]+)\*\*', r'【\1】', report)
        # *斜体* → そのまま
        report = re.sub(r'\*([^*]+)\*', r'\1', report)
        # # 見出し → 見出し（丸数字は残す）
        report = re.sub(r'^#{1,6}\s+', '', report, flags=re.MULTILINE)
        # - 箇条書き → ・箇条書き
        report = re.sub(r'^-\s+', '・', report, flags=re.MULTILINE)
        report = re.sub(r'^\*\s+', '・', report, flags=re.MULTILINE)
        # [リンクテキスト](URL) → リンクテキスト (URL)
        report = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', report)
        # --- 区切り線を削除
        report = re.sub(r'^---+\s*$', '', report, flags=re.MULTILINE)

        # 連続する空行を整理（3行以上を2行に）
        report = re.sub(r'\n{3,}', '\n\n', report)

        # 不要なコードブロックマーカーを削除（もしあれば）
        report = re.sub(r'^```[a-z]*\s*\n', '', report)
        report = re.sub(r'\n```\s*$', '', report)

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
