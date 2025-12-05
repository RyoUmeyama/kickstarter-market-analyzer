#!/usr/bin/env python3
"""
設定シートのプロンプトを更新するスクリプト
"""

import os
from dotenv import load_dotenv
from sheets_client import GoogleSheetsClient

load_dotenv()

# 改善したシステム設定（G2）
NEW_SYSTEM_SETTINGS = """=== システム設定（変更しないでください） ===

■ プロのマーケッターとしての分析基準（最重要）
あなたは日本市場に精通したプロのマーケッターです。以下の基準で分析を行ってください：

【データがある場合】
・具体的な数値とソースURLを必ずセットで記載
・例: 「CAMPFIREで"Tiny Ten"が1,017,500円を調達（https://camp-fire.jp/projects/609963/view）」
・金額の根拠がないデータは絶対に記載しない

【データがない場合 - 「No data available」は禁止】
・「現在、データはありません」「No data available」という記載は禁止
・代わりに以下の分析を必ず行うこと：

1. 業界データからの推論（必ず出典を明記）
   例: 「日本のクラウドファンディング市場は2024年に432億円規模（PR TIMES 2024）であり...」

2. 類似製品カテゴリからの推定
   例: 「同価格帯（$80-120）のアウトドア製品は、日本のクラウドファンディングで平均150-300万円の調達実績があり...」

3. 具体的な小売店名・EC名を挙げた戦略
   例: 「ヨドバシカメラ、ビックカメラ、東急ハンズなどの大手量販店では...」

■ レポート構成ルール（重要）

【テンプレートの分析項目に厳密に従う】
・テンプレートに記載された分析項目（①〜④など）のみを記述すること
・テンプレートにない追加セクション（PSE認証、独占販売契約など）は生成しない
・例: テンプレートが①②③④の4項目なら、レポートも1〜4のセクションのみ

【PSE認証について】
・電子機器・電気製品のみ言及すること
・カミソリ、映画、衣類、食品などにはPSE認証は不要なので言及しない

【文字数制限】
・日本語本文は全体で1500〜2000文字程度に収める
・各セクションは3〜5文程度で簡潔に記述
・冗長な説明は避け、要点を明確に

■ データ正確性（絶対厳守）
【自社製品データ】
・Kickstarterの調達額・バッカー数は提供データをそのまま使用
・ドルはドルのまま記載（円換算しない）

【日本クラファンデータ - 必須使用】
・market_research_dataにMakuake/CAMPFIREデータがある場合、必ずレポートに含める
・製品名、調達額、URLをセットで記載

【業界データの使用】
・業界データセクションから引用する場合は必ず出典を明記
・例: 「日本のクラウドファンディング市場は432億円（PR TIMES 2024）」

■ 禁止事項
・[insert URL]や[URL]などのプレースホルダー
・ソースURLなしの具体的金額
・「No data available」「現在、データはありません」という記載
・テンプレートにない追加セクションの生成
・電子機器以外へのPSE認証の言及

■ 出力形式
・URLはプレーンテキスト形式
・Markdown記法は使用禁止
・セクションタイトルの後に改行を入れる"""

# 改善した共通プロンプト（A2）
NEW_COMMON_PROMPT = """=== レポートの質と内容（この設定は編集可能です） ===

■ 文章量の目安
・各セクションは3-5文で簡潔に記述
・日本語本文の合計は1500〜2000文字程度
・データがある場合は詳細に、データがない場合は推論を記載
・無理に文章を膨らませない

■ 類似製品の分析
・提供された市場調査データに含まれる製品のみ記載
・各製品のURLを必ず含める
・調達額はデータにある場合のみ記載

■ データの取り扱い（重要）
・提供されたKickstarterデータ（調達額・バッカー数）をそのまま使用
・ドルはドルのまま記載（円換算しない）
・EC売上・小売売上のデータがない場合は業界データから推論
・数字を推測・捏造しない
・業界データを引用する場合は必ず出典を明記

■ 戦略の具体性
・具体的な施策を含める（SNS活用、インフルエンサー起用等）
・数値目標は提供データがある場合のみ記載

■ 文体とトーン
・ビジネスパートナーへの提案として説得力のある内容
・専門的かつ分かりやすい表現
・「AIによると」などの表現は避ける

■ フォーマット
・テンプレートで指定されたセクション数のみ記述
・追加セクションは生成しない
・セクションは番号付き（1. 2. 3.）
・セクションタイトルの後に改行"""


def main():
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    if not spreadsheet_id:
        print("❌ エラー: SPREADSHEET_IDが.envファイルに設定されていません")
        return

    print("=" * 60)
    print("設定シート更新スクリプト")
    print("=" * 60)

    # Google Sheetsクライアントを初期化
    print("\nGoogle Sheets認証中...")
    client = GoogleSheetsClient(spreadsheet_id, 'kickstarter')
    print("✓ 認証成功！\n")

    try:
        # G2（システム設定）を更新
        print("G2（システム設定）を更新中...")
        result = client.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="'設定'!G2",
            valueInputOption='RAW',
            body={'values': [[NEW_SYSTEM_SETTINGS]]}
        ).execute()
        print(f"✓ G2を更新しました（{result.get('updatedCells', 0)}セル）")

        # A2（共通プロンプト）を更新
        print("A2（共通プロンプト）を更新中...")
        result = client.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="'設定'!A2",
            valueInputOption='RAW',
            body={'values': [[NEW_COMMON_PROMPT]]}
        ).execute()
        print(f"✓ A2を更新しました（{result.get('updatedCells', 0)}セル）")

        print("\n" + "=" * 60)
        print("✅ 設定シートの更新が完了しました！")
        print("=" * 60)

        # 確認のため更新内容を表示
        print("\n【更新内容の概要】")
        print("■ G2（システム設定）:")
        print("  - テンプレートの分析項目に厳密に従うルールを追加")
        print("  - PSE認証は電子機器のみに言及するルールを追加")
        print("  - 文字数制限（1500〜2000文字）を追加")
        print("\n■ A2（共通プロンプト）:")
        print("  - 文章量の目安を明確化")
        print("  - 追加セクション生成禁止ルールを追加")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
