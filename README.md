# Kickstarter Market Analyzer

Kickstarter製品の日本市場参入提案メールを自動生成するシステムです。

## 🎯 主な機能

1. **テンプレートベースのメール生成**
   - Google Sheetsでテンプレートを管理
   - ドロップダウンリストで簡単選択
   - クライアント様が自由にテンプレートシートを追加可能

2. **OpenAI API統合（任意）**
   - テンプレートにプロンプト（A3セル）を設定すれば、OpenAI APIで専門的な市場分析レポートを生成
   - プロンプトがなければ、テンプレート本文をそのまま使用
   - 具体的なデータ、実URL、競合分析を含む詳細レポート

3. **自動翻訳対応**
   - Google SheetsのGOOGLETRANSLATE関数により英語→日本語を自動翻訳
   - テンプレートは英語で作成、日本語は自動生成

4. **メールマージ対応**
   - Google SheetsをCSV出力してThunderbirdのメールマージで一括送信可能
   - HTML形式メール対応（改行を`<br>`に自動変換）

5. **GitHub Actions自動実行**
   - 手動トリガーで簡単実行
   - サービスアカウント認証で安全

## 📊 システム構成

### kickstarterシート（一覧管理）

| 列 | 列名 | 説明 | メールマージで使用 |
|----|------|------|--------------------|
| A | NO | 番号 | ❌ |
| B | product_url | Kickstarter URL | ❌ |
| C | template | テンプレート名 | ❌ |
| D | name | 担当者名/メーカー名 | ✅ `{{name}}` |
| E | to_email | 送信先メールアドレス | ✅ `{{to_email}}` |
| F | jp_subject | 日本語件名（自動生成） | ✅ `{{jp_subject}}` |
| G | en_subject | 英語件名（自動生成） | ✅ `{{en_subject}}` |
| H | jp_body | 日本語本文（自動生成） | ✅ `{{jp_body}}` |
| I | en_body | 英語本文（自動生成） | ✅ `{{en_body}}` |
| J | jp_body_html | 日本語本文HTML版 | ✅ `{{jp_body_html}}` |
| K | en_body_html | 英語本文HTML版 | ✅ `{{en_body_html}}` |

### テンプレートシート

クライアント様が自由にシートを追加できます。以下のルールに従ってください：

| 行 | A列 | B列 |
|----|-----|-----|
| 1 | 英語件名 | 日本語件名（`=GOOGLETRANSLATE(A1, "en", "ja")`） |
| 2 | 英語本文 | 日本語本文（`=GOOGLETRANSLATE(A2, "en", "ja")`） |
| 3 | プロンプト（日本語、任意） | （空） |

**重要な仕様:**
- **B1とB2はGOOGLETRANSLATE関数**でA1とA2を自動翻訳
- **A3のプロンプトは日本語で記載**（任意）
- プロンプトがある場合、A2の本文テンプレート + A3のプロンプトをOpenAI APIに送信し、**完全な英語メール本文**を生成
- 生成された英語本文は、kickstarterシートのH列でGOOGLETRANSLATE関数により日本語に自動翻訳

**プレースホルダー:**
- `{{URL}}`: Kickstarter URLに置換
- `{{name}}`: メーカー名に置換
- `{{レポート}}`: OpenAI生成レポートに置換（A3プロンプトがある場合）

**OpenAI API使用条件:**
- **A3が空の場合**: A2/B2の本文をそのまま使用
- **A3にプロンプトがある場合**: OpenAI APIで英語メール本文全体を生成 → Google Sheetsで日本語に自動翻訳

## 🚀 クライアント様向けセットアップ

詳細な手順は **[CLIENT_SETUP_GUIDE.md](CLIENT_SETUP_GUIDE.md)** をご覧ください。

### 必要なもの
- Googleアカウント（Google Sheets、Google Cloud用）
- OpenAIアカウント（APIキー取得用）
- GitHubアカウント（リポジトリアクセス用）
- 所要時間: 約30-45分

### セットアップ概要
1. Google Sheetsテンプレートをコピー
2. Google Cloud サービスアカウントを作成
3. OpenAI APIキーを取得
4. GitHub Secretsを設定（3つ）
5. GitHub Actionsで手動実行

## 📁 プロジェクト構成

```
kickstarter-market-analyzer/
├── .github/
│   └── workflows/
│       └── update_reports.yml       # GitHub Actionsワークフロー
├── .env                             # ローカル設定（Git除外）
├── .env.example                     # 設定テンプレート
├── .gitignore                       # Git除外設定
├── main.py                          # メインスクリプト
├── sheets_client.py                 # Google Sheets連携
├── report_generator.py              # レポート生成（OpenAI API）
├── requirements.txt                 # 依存関係
├── README.md                        # 本ドキュメント
└── CLIENT_SETUP_GUIDE.md            # クライアント向けガイド
```

## 🔧 日常的な使い方

### 1. データ入力

Google Sheetsの`kickstarter`シートに新しい行を追加：

| A | B | C | D | E |
|---|---|---|---|---|
| 1 | https://www.kickstarter.com/projects/... | ①1回目送信文 | WashWow | contact@washwow.com |

### 2. GitHub Actionsで実行

1. GitHubリポジトリの「Actions」タブを開く
2. 「Kickstarter Market Analyzer - Manual Update」を選択
3. 「Run workflow」ボタンをクリック
4. 処理完了を待つ（1-3分）

### 3. 結果確認

Google Sheetsに以下が自動入力されます：
- F列: 日本語件名
- G列: 英語件名
- H列: 日本語本文（プレーンテキスト）
- I列: 英語本文（プレーンテキスト）
- J列: 日本語本文（HTML）
- K列: 英語本文（HTML）

### 4. メール送信（Thunderbird）

1. **CSV出力**: ファイル → ダウンロード → カンマ区切り形式（.csv）
2. **Thunderbirdメールマージ**:
   - 送信先: `{{to_email}}`
   - 件名: `{{jp_subject}}` または `{{en_subject}}`
   - 本文（HTML）: `{{jp_body_html}}` または `{{en_body_html}}`

## 🆕 新しいテンプレートの追加

クライアント様が自由にテンプレートを追加できます：

1. **新しいシートを作成**（例: `⑥新規顧客向け`）
2. **以下の構造でテンプレートを記述**:
   ```
   A1: Subject: Market Entry Proposal for {{name}}'s Product
   B1: =GOOGLETRANSLATE(A1, "en", "ja")

   A2: Dear {{name}} team,

       We are interested in your product: {{URL}}
       ...
   B2: =GOOGLETRANSLATE(A2, "en", "ja")

   A3: （プロンプトを入れる場合のみ、日本語で記載）
   ```
3. **kickstarterシートのC列ドロップダウン**から新しいテンプレートを選択

## ⚙️ OpenAI API使用について

### プロンプトなし（シンプルモード）
A3セルを空欄にすると、A2/B2の本文をそのまま使用します。OpenAI APIは呼び出されません。

### プロンプトあり（AI分析モード）
A3セルに日本語でプロンプトを記述すると、OpenAI APIで専門的な市場分析レポートを生成します。

**プロンプト例:**
```
{{URL}}のKickstarter製品について、日本市場参入の詳細な提案レポートを作成してください。

以下の内容を含めてください：
1. 日本市場におけるクラウドファンディングの成功可能性（具体的な数字で）
2. 競合製品の分析（実際の製品名とMakuakeやGREEN FUNDINGのURLを含む）
3. 推奨販売チャネル（Makuake、Amazon Japanなど）
4. 予想収益予測（類似製品の実績データに基づく）
5. リスク分析

全て英語で、具体的な情報源のURLを含めて詳細に記述してください。
```

**処理の流れ:**
1. A2の本文テンプレート + A3のプロンプトをOpenAI APIに送信
2. OpenAI APIが**英語で完全なメール本文**を生成（{{レポート}}部分を含む）
3. 英語メール本文をkickstarterシートのI列に書き込み
4. H列に`=GOOGLETRANSLATE(I2, "en", "ja")`関数を自動設定
5. Google SheetsがリアルタイムでH列を日本語に翻訳

## 🎓 トラブルシューティング

詳細は **[CLIENT_SETUP_GUIDE.md](CLIENT_SETUP_GUIDE.md)** の「トラブルシューティング」セクションをご覧ください。

### よくある問題

**Error 403: Forbidden**
- サービスアカウントがスプレッドシートにアクセスできない
- 解決策: スプレッドシートの共有設定を確認（編集者権限）

**未処理行が検出されない**
- B列（product_url）にURLが入力されているか確認
- H列（jp_body）が空、または100文字未満か確認

**OpenAI APIエラー**
- APIキーが正しく設定されているか確認
- クレジット残高を確認

## 📈 技術仕様

### 使用技術
- **Python 3.11+**
- **Google Sheets API** (service account認証)
- **OpenAI API** (gpt-4o-mini)
- **GitHub Actions** (手動トリガー)

### 依存関係
```
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
openai
python-dotenv
```

### コスト目安
- **OpenAI API**: 1回の処理で約$0.01-0.03（1-3円）
- **月間100件処理**: 約$1-3（100-300円）

## 📝 ライセンス

このプロジェクトは内部使用のためのものです。
