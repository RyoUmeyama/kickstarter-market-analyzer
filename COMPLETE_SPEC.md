# Kickstarter Market Analyzer - 完全仕様書

## 📋 最終確定仕様

### テンプレートシート構造

```
【行1: 件名】
A1: 英語件名
B1: =GOOGLETRANSLATE(A1, "en", "ja")  ← 日本語件名に自動翻訳

【行2: 本文】
A2: 英語本文
B2: =GOOGLETRANSLATE(A2, "en", "ja")  ← 日本語本文に自動翻訳

【行3: プロンプト（任意）】
A3: プロンプト（日本語で記載）
B3: （空）
```

### kickstarterシート構造（メールマージ対応）

| 列 | 列名 | 内容 | メールマージ変数名 |
|----|------|------|--------------------|
| A | NO | 番号 | - |
| B | product_url | Kickstarter URL | - |
| C | template | テンプレート名 | - |
| D | name | メーカー名 | `{{name}}` |
| E | to_email | 送信先メールアドレス | `{{to_email}}` |
| F | jp_subject | 日本語件名 | `{{jp_subject}}` |
| G | en_subject | 英語件名 | `{{en_subject}}` |
| H | status | ステータス | - |
| I | jp_body | 日本語本文 | `{{jp_body}}` |
| J | en_body | 英語本文 | `{{en_body}}` |

## 🔄 処理フロー詳細

### パターン1: プロンプトなし（固定文テンプレート）

```
1. テンプレートシートから読み取り
   ├─ A1（英語件名）
   ├─ B1（日本語件名、GOOGLETRANSLATE関数の結果）
   ├─ A2（英語本文）
   └─ B2（日本語本文、GOOGLETRANSLATE関数の結果）

2. プレースホルダー置換
   ├─ {{URL}} → Kickstarter URL
   └─ {{name}} → メーカー名

3. kickstarterシートに書き込み
   ├─ F列（jp_subject）: B1の置換結果
   ├─ G列（en_subject）: A1の置換結果
   ├─ I列（jp_body）: B2の置換結果
   └─ J列（en_body）: A2の置換結果
```

### パターン2: プロンプトあり（AI生成テンプレート）

```
1. テンプレートシートから読み取り
   ├─ A1（英語件名）
   ├─ B1（日本語件名、GOOGLETRANSLATE関数の結果）
   └─ A3（プロンプト、日本語）

2. 件名のプレースホルダー置換
   ├─ {{URL}} → Kickstarter URL
   └─ {{name}} → メーカー名

3. プロンプトのプレースホルダー置換
   ├─ {{URL}} → Kickstarter URL
   └─ {{name}} → メーカー名

4. OpenAI API呼び出し
   ├─ システム: "You are a professional business consultant.
   │             The user will provide a prompt in Japanese.
   │             Please respond in English with a detailed business report."
   ├─ ユーザー: A3のプロンプト（日本語、プレースホルダー置換済み）
   └─ レスポンス: 英語レポート

5. kickstarterシートに書き込み
   ├─ F列（jp_subject）: B1の置換結果
   ├─ G列（en_subject）: A1の置換結果
   ├─ I列（jp_body）: =IF(J2="", "", GOOGLETRANSLATE(J2, "en", "ja"))  ← 自動設定
   └─ J列（en_body）: OpenAI APIの英語レポート

6. Google SheetsがI列を自動翻訳
   └─ GOOGLETRANSLATE関数がJ列（英語）を日本語に翻訳
```

## 📧 メールマージでの使用方法

### ステップ1: Google SheetsをCSV出力

1. Google Sheetsを開く
2. ファイル → ダウンロード → カンマ区切り形式（.csv）
3. ファイルを保存

### ステップ2: Thunderbirdで読み込み

1. Thunderbirdを起動
2. Mail Mergeアドオンを選択
3. CSVファイルを読み込み

### ステップ3: メール設定

**日本語メールの場合:**
```
送信先: {{to_email}}
件名: {{jp_subject}}
本文: {{jp_body}}
```

**英語メールの場合:**
```
送信先: {{to_email}}
件名: {{en_subject}}
本文: {{en_body}}
```

### ステップ4: 送信

- プレビューで内容を確認
- 一括送信または個別送信を選択
- 送信実行

## 🎯 使用例

### 例1: 固定文テンプレート（①1回目送信文）

**テンプレートシート:**
```
A1: Proposal for Japan Market Collaboration
B1: =GOOGLETRANSLATE(A1, "en", "ja")  → 「日本市場における協業の提案」

A2: Dear {{name}} Sales Team,

I hope this message finds you well.
My name is Koki Oshima, CEO of Life Support Co., Ltd.,
headquartered in Tokyo, Japan.

I was very impressed by your innovative product below:
{{URL}}
...

B2: =GOOGLETRANSLATE(A2, "en", "ja")  → 「{{name}} 営業チーム様、...」

A3: （空）
```

**kickstarterシート（入力）:**
```
B2: https://www.kickstarter.com/projects/washwow/...
C2: ①1回目送信文
D2: WashWow
E2: sales@washwow.com
```

**kickstarterシート（出力）:**
```
F2: 日本市場における協業の提案
G2: Proposal for Japan Market Collaboration
H2: 完了
I2: WashWow 営業チーム様、...（プレースホルダー置換済み）
J2: Dear WashWow Sales Team, ...（プレースホルダー置換済み）
```

### 例2: AI生成テンプレート（新規作成例）

**テンプレートシート「⑥AI市場分析レポート」:**
```
A1: Japan Market Analysis Report for {{name}}
B1: =GOOGLETRANSLATE(A1, "en", "ja")  → 「{{name}}の日本市場分析レポート」

A2: （使用しない、空でOK）
B2: =GOOGLETRANSLATE(A2, "en", "ja")

A3: 以下のKickstarter製品について、日本市場参入の詳細な分析レポートを英語で作成してください。

製品URL: {{URL}}
メーカー名: {{name}}

以下の内容を含めてください：
1. 日本市場におけるクラウドファンディングの成功可能性
   - Makuakeでの予想支援額
   - 類似製品の実績データ（具体的なURLを含む）
2. 競合製品の分析
   - Amazon Japanでの競合製品リスト
   - 価格帯比較
3. 推奨販売チャネル
   - Makuake → Amazon Japan → 小売店の展開案
4. 予想収益予測（1年目、2年目、3年目）
5. リスク分析と対策

全て英語で詳細に記述してください。
```

**kickstarterシート（入力）:**
```
B2: https://www.kickstarter.com/projects/washwow/...
C2: ⑥AI市場分析レポート
D2: WashWow
E2: sales@washwow.com
```

**kickstarterシート（出力）:**
```
F2: WashWowの日本市場分析レポート
G2: Japan Market Analysis Report for WashWow
H2: 完了
I2: =IF(J2="", "", GOOGLETRANSLATE(J2, "en", "ja"))  → J2を自動翻訳
J2: Based on the Kickstarter product at https://www.kickstarter.com/...,
    here is a detailed market entry analysis for Japan:

    1. Crowdfunding Success Potential in Japan
    - Estimated Makuake funding: ¥15,000,000 - ¥25,000,000
    - Similar product case study: [Product Name] raised ¥18,500,000
      URL: https://www.makuake.com/project/...

    2. Competitive Analysis
    - Amazon Japan competitors:
      * Product A: ¥8,900 (URL: https://amazon.co.jp/...)
      * Product B: ¥12,800 (URL: https://amazon.co.jp/...)
    ...
```

## 🔧 主要ファイル

### 実行ファイル

1. **main.py** - メイン処理
2. **sheets_client.py** - Google Sheets連携
3. **report_generator.py** - レポート生成（OpenAI API対応）

### セットアップファイル

4. **setup_template_dropdown.py** - ドロップダウンリスト設定
5. **update_column_names.py** - 列名更新（jp_body, en_body）
6. **update_kickstarter_sheet_structure.py** - シート構造更新

### テストファイル

7. **test_updated_template.py** - テンプレート読み込みテスト
8. **inspect_template_sheet.py** - テンプレート構造確認
9. **inspect_spreadsheet.py** - 全シート確認

## ⚙️ 設定ファイル

- **.env** - 環境変数（SPREADSHEET_ID, OPENAI_API_KEY）
- **credentials.json** - OAuth 2.0認証情報
- **token.json** - 認証トークン（自動生成）

## 📚 ドキュメント

- **README.md** - 使用方法
- **COMPLETE_SPEC.md** - このファイル（完全仕様書）
- **UPDATED_SYSTEM_SPEC.md** - 詳細仕様
- **FINAL_SUMMARY.md** - 実装サマリー

## ✅ 完了チェックリスト

- [x] テンプレートシート構造確定（A1-B2, A3）
- [x] GOOGLETRANSLATE関数の自動設定実装
- [x] OpenAI API統合（日本語プロンプト → 英語レポート）
- [x] kickstarterシートの列名変更（jp_body, en_body）
- [x] メールマージ対応
- [x] ドキュメント完備

## 🎓 重要ポイント

1. **B1とB2はGOOGLETRANSLATE関数**
   - 手動で設定済み
   - A1とA2を自動翻訳

2. **A3のプロンプトは日本語**
   - OpenAI APIに投げて英語で結果を取得
   - スクリプトがI列にGOOGLETRANSLATE関数を自動設定

3. **列名はメールマージ用**
   - jp_body, en_body（reportではない）
   - そのままThunderbirdで使用可能

4. **プレースホルダーは2種類**
   - `{{URL}}`: Kickstarter URL
   - `{{name}}`: メーカー名
