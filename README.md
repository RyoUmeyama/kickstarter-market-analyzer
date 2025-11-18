# Kickstarter Market Analyzer

Kickstarter製品の日本市場参入提案メールを自動生成するシステムです。

## 🎯 主な機能

1. **テンプレート選択機能**
   - 5種類のメールテンプレートから選択
   - ドロップダウンリストで簡単選択

2. **OpenAI API統合（任意）**
   - テンプレートにプロンプトを設定すれば、OpenAI APIで動的にレポート生成
   - プロンプトがなければ、テンプレート本文をそのまま使用

3. **件名・本文の自動生成**
   - テンプレートから日本語・英語の件名と本文を自動取得
   - `{{URL}}`と`{{name}}`のプレースホルダーを自動置換

4. **メールマージ対応**
   - Google SheetsをCSV出力してThunderbirdのメールマージで一括送信可能

## 📊 システム構成

### kickstarterシート（一覧管理）

| 列 | 列名 | 説明 | メールマージで使用 |
|----|------|------|--------------------|
| A | NO | 番号 | ❌ |
| B | product_url | Kickstarter URL | ❌ |
| C | template | テンプレート名 | ❌ |
| D | name | 担当者名/メーカー名 | ✅ |
| E | to_email | 送信先メールアドレス | ✅ |
| F | jp_subject | 日本語件名（自動生成） | ✅ |
| G | en_subject | 英語件名（自動生成） | ✅ |
| H | status | 処理ステータス | ❌ |
| I | jp_body | 日本語本文（自動生成） | ✅ |
| J | en_body | 英語本文（自動生成） | ✅ |

### テンプレートシート

各テンプレートは独立したシートとして存在：

| 行 | A列 | B列 |
|----|-----|-----|
| 1 | 英語件名 | 日本語件名（`=GOOGLETRANSLATE(A1, "en", "ja")`） |
| 2 | 英語本文 | 日本語本文（`=GOOGLETRANSLATE(A2, "en", "ja")`） |
| 3 | プロンプト（日本語、任意） | （空） |

**重要な仕様:**
- B1とB2はGOOGLETRANSLATE関数でA1とA2を自動翻訳
- A3のプロンプトは**日本語**で記載
- プロンプトがある場合、OpenAI APIに投げて**英語**でレポートを生成
- 生成された英語レポートは、kickstarterシートのI列でGOOGLETRANSLATE関数により日本語に自動翻訳

**プレースホルダー:**
- `{{URL}}`: Kickstarter URLに置換
- `{{name}}`: メーカー名に置換

**OpenAI API使用条件:**
- A3が**空の場合**: A2/B2の本文をそのまま使用
- A3に**プロンプトがある場合**: OpenAI APIで英語レポートを生成 → Google Sheetsで日本語に自動翻訳

## 🚀 使用方法

### 初回セットアップ

1. **Google Sheets API認証設定**
   ```bash
   # setup_auth_quick.mdの手順に従ってcredentials.jsonを取得
   # OAuth同意画面にテストユーザーを追加
   ```

2. **.envファイルを設定**
   ```bash
   SPREADSHEET_ID=your_spreadsheet_id
   SHEET_NAME=kickstarter
   OPENAI_API_KEY=your_api_key_here  # 任意
   MODEL=gpt-4o-mini
   ```

3. **必要な依存関係をインストール**
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client openai python-dotenv
   ```

### データ入力

1. **kickstarterシートにデータを追加**
   - A列（NO）: 1, 2, 3...
   - B列（product_url）: Kickstarter URL
   - C列（template）: ドロップダウンからテンプレートを選択
   - D列（name）: メーカー名（任意）
   - E列（to_email）: 送信先メールアドレス

2. **main.pyを実行**
   ```bash
   python3 main.py
   ```

3. **結果を確認**
   - F列（jp_subject）: 日本語件名
   - G列（en_subject）: 英語件名
   - H列（status）: ステータス（完了）
   - I列（jp_body）: 日本語本文
   - J列（en_body）: 英語本文

### メールマージで送信

1. **Google SheetsをCSV出力**
   - ファイル → ダウンロード → カンマ区切り形式（.csv）

2. **Thunderbirdのメールマージで送信**
   - Thunderbirdでメールマージアドオンを使用
   - CSVファイルを読み込み
   - 送信先: `{{to_email}}`
   - 件名: `{{jp_subject}}` または `{{en_subject}}`
   - 本文: `{{jp_body}}` または `{{en_body}}`

## 📁 ファイル構成

```
kickstarter-market-analyzer/
├── .env                                # 環境変数
├── credentials.json                    # OAuth 2.0認証情報
├── token.json                          # 認証トークン（自動生成）
├── main.py                             # メイン処理
├── sheets_client.py                    # Google Sheets連携
├── report_generator.py                 # レポート生成（OpenAI API対応）
├── openai_client_improved.py           # 旧OpenAIクライアント（参考用）
├── setup_template_dropdown.py          # ドロップダウンリスト設定
├── update_kickstarter_sheet_structure.py # シート構造更新
├── test_template_reading.py            # テンプレート読み込みテスト
├── inspect_template_sheet.py           # テンプレート構造確認
├── inspect_spreadsheet.py              # 全シート確認
└── test_sheets_access.py               # Sheets接続テスト
```

## 🔧 メンテナンス

### 新しいテンプレートの追加

1. スプレッドシートに新しいシートを作成
2. 以下の構造でテンプレートを記述：
   ```
   A1: 英語件名        B1: 日本語件名
   A2: 英語本文        B2: 日本語本文
   A3: 英語プロンプト  B3: 日本語プロンプト（任意）
   ```

3. `setup_template_dropdown.py`を編集してテンプレート名を追加:
   ```python
   template_names = [
       "①1回目送信文",
       "②無返信用2回目送信",
       "➂無返信3回目",
       "④自動返信用　2回目送信",
       "⑤好返信用　詳細レポート送信",
       "⑥新しいテンプレート"  # 追加
   ]
   ```

4. `setup_template_dropdown.py`を実行してドロップダウンリストを更新:
   ```bash
   python3 setup_template_dropdown.py
   ```

### テンプレートの検証

```bash
# 全シート確認
python3 inspect_spreadsheet.py

# テンプレート構造確認
python3 inspect_template_sheet.py

# テンプレート読み込みテスト
python3 test_template_reading.py
```

## ⚙️ OpenAI API使用について

### プロンプトなし（デフォルト）
テンプレートシートの3行目を空欄にすると、2行目の本文をそのまま使用します。
OpenAI APIは呼び出されません。

### プロンプトあり
テンプレートシートのA3にプロンプト（日本語）を記述すると、OpenAI APIで英語レポートを生成します。

**例:**
```
A3（プロンプト、日本語）:
{{URL}}のKickstarter製品について、日本市場参入の詳細な提案を英語で作成してください。

製品URL: {{URL}}
メーカー名: {{name}}

以下の内容を含めてください：
1. 日本市場におけるクラウドファンディングの成功可能性
2. 競合製品の分析（具体的な製品名とURLを含む）
3. 推奨販売チャネル（Makuake、Amazon Japanなど）
4. 予想収益予測
5. リスク分析

全て英語で詳細に記述してください。

B3: （空のまま）
```

**処理の流れ:**
1. A3のプロンプトをOpenAI APIに送信（日本語プロンプト）
2. OpenAI APIが**英語**でレポートを生成
3. 英語レポートをkickstarterシートのJ列に書き込み
4. I列に`=GOOGLETRANSLATE(J2, "en", "ja")`関数を自動設定
5. Google SheetsがリアルタイムでI列を日本語に翻訳

## 🎓 トラブルシューティング

### Error 403: access_denied
- OAuth同意画面にテストユーザーを追加
- Google Cloud Console → OAuth同意画面 → テストユーザー

### テンプレートが読み込めない
```bash
python3 inspect_template_sheet.py
```
でテンプレート構造を確認してください。

### 未処理行が検出されない
- B列（product_url）にURLが入力されているか確認
- I列（jp_body）が空白、または100文字未満か確認

### OpenAI APIエラー
- `.env`ファイルの`OPENAI_API_KEY`が正しく設定されているか確認
- APIキーの有効期限とクレジットを確認

## 🤖 GitHub Actions 自動実行

このシステムはGitHub Actionsで自動実行できます。

### セットアップ

詳細は [`GITHUB_ACTIONS_SETUP.md`](GITHUB_ACTIONS_SETUP.md) を参照してください。

**概要**:
1. Google Cloud サービスアカウントを作成
2. スプレッドシートをサービスアカウントと共有（編集者権限）
3. GitHub Secretsに以下を設定:
   - `GOOGLE_CREDENTIALS_JSON`: サービスアカウントのJSONキー
   - `SPREADSHEET_ID`: スプレッドシートID
   - `OPENAI_API_KEY`: OpenAI APIキー（任意）
4. リポジトリにプッシュ

### 実行スケジュール

- **自動実行**: 毎日 9:00 JST（00:00 UTC）
- **手動実行**: GitHubの「Actions」タブから「Run workflow」

### ワークフローファイル

`.github/workflows/update_reports.yml`

## 📈 今後の拡張予定

- [x] OpenAI APIによる動的レポート生成機能
- [x] 件名の自動生成
- [x] メールマージ対応
- [x] GitHub Actionsによる自動実行
- [ ] 自動メール送信機能の統合
- [ ] 送信履歴管理
- [ ] レスポンス追跡機能

## 📝 ライセンス

このプロジェクトは内部使用のためのものです。
