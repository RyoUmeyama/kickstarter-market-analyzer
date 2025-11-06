# Google Sheets API セットアップガイド

このドキュメントでは、Google Sheets APIを使用するための設定手順を説明します。

## 🎯 認証方法の選択

本プロジェクトは2種類の認証方法をサポートしています：

| 認証方法 | 用途 | 推奨 |
|---------|------|------|
| **サービスアカウント** | GitHub Actions、サーバー実行 | ⭐ 推奨 |
| OAuth 2.0 | ローカルPC実行（対話的認証） | ローカルのみ |

**GitHub Actionsで使用する場合は、必ずサービスアカウントを使用してください。**

---

## 📋 方法1: サービスアカウント認証（GitHub Actions用）⭐

### ステップ1: Google Cloud Consoleでプロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 右上の「プロジェクトを選択」→「新しいプロジェクト」
3. プロジェクト名を入力（例: \`kickstarter-analyzer\`）
4. 「作成」をクリック

### ステップ2: Google Sheets APIを有効化

1. 左メニュー → 「APIとサービス」→「ライブラリ」
2. 検索バーで「Google Sheets API」を検索
3. 「Google Sheets API」をクリック
4. 「有効にする」をクリック

### ステップ3: サービスアカウントを作成

1. 左メニュー → 「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「サービスアカウント」を選択
3. サービスアカウント名を入力（例: \`kickstarter-sheets-bot\`）
4. サービスアカウントID（例: \`kickstarter-sheets-bot@your-project.iam.gserviceaccount.com\`）が自動生成される
   - **このメールアドレスをメモしておく**
5. 「作成して続行」をクリック
6. ロールは「なし」でOK（スプレッドシート側で権限を付与するため）
7. 「完了」をクリック

### ステップ4: サービスアカウントキーをダウンロード

1. 作成したサービスアカウントをクリック
2. 「キー」タブをクリック
3. 「鍵を追加」→「新しい鍵を作成」
4. キーのタイプ: **JSON**を選択
5. 「作成」をクリック
6. JSONファイルがダウンロードされる
   - **このファイルは厳重に管理してください（公開しない）**

### ステップ5: スプレッドシートに共有設定

1. 分析対象のGoogle Sheetsを開く
2. 右上の「共有」ボタンをクリック
3. サービスアカウントのメールアドレスを入力
   - 例: \`kickstarter-sheets-bot@your-project.iam.gserviceaccount.com\`
4. 権限を「編集者」に設定
5. 「送信」をクリック

### ステップ6: GitHub Secretsに設定

1. GitHubリポジトリ → Settings → Secrets and variables → Actions
2. 「New repository secret」をクリック
3. **Name**: \`GOOGLE_CREDENTIALS_JSON\`
4. **Value**: ダウンロードしたJSONファイルの内容をそのまま貼り付け
5. 「Add secret」をクリック

### ステップ7: その他のSecretsを設定

同様の手順で以下も設定：

| Secret名 | 説明 | 例 |
|---------|------|-----|
| \`OPENAI_API_KEY\` | OpenAI APIキー | \`sk-proj-...\` |
| \`SPREADSHEET_ID\` | SpreadsheetのID | \`1AbC...XyZ\`（URLの\`/d/\`と\`/edit\`の間） |
| \`SHEET_NAME\` | シート名 | \`kickstarter\` |

---

## 📋 方法2: OAuth 2.0認証（ローカル実行用）

ローカルPCで実行する場合のみ使用してください。

### ステップ1〜2: （方法1と同じ）

プロジェクト作成とGoogle Sheets API有効化は同じ手順です。

### ステップ3: OAuth 2.0クライアントIDを作成

1. 左メニュー → 「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「OAuth クライアント ID」を選択
3. アプリケーションの種類: **デスクトップアプリ**を選択
4. 名前を入力（例: \`Kickstarter Analyzer Local\`）
5. 「作成」をクリック

### ステップ4: credentials.jsonをダウンロード

1. 作成したOAuth 2.0クライアントの右側にある「ダウンロード」アイコンをクリック
2. JSONファイルがダウンロードされる
3. ファイル名を\`credentials.json\`にリネーム
4. プロジェクトルートに配置

### ステップ5: 初回認証

1. プロジェクトルートで実行：
   \`\`\`bash
   python check_kickstarter.py
   \`\`\`

2. ブラウザが自動的に開き、Google認証画面が表示される

3. Googleアカウントでログイン

4. 「このアプリは確認されていません」という警告が表示される場合：
   - 「詳細」→「（アプリ名）に移動」をクリック

5. 権限のリクエストを「許可」

6. \`token.json\`が自動生成される
   - 次回以降はこのトークンを使用（再認証不要）

---

## 🔧 トラブルシューティング

### エラー: \`credentials.json が見つかりません\`

- OAuth 2.0認証の場合: credentials.jsonをダウンロードしてプロジェクトルートに配置
- サービスアカウント認証の場合: \`GOOGLE_CREDENTIALS_JSON\`環境変数を設定

### エラー: \`HttpError 403: The caller does not have permission\`

- スプレッドシートがサービスアカウントに共有されているか確認
- サービスアカウントのメールアドレスが正しいか確認
- 権限が「編集者」になっているか確認

### エラー: \`invalid_grant\` (OAuth 2.0)

- \`token.json\`を削除して再認証
  \`\`\`bash
  rm token.json
  python check_kickstarter.py
  \`\`\`

### GitHub Actionsで\`credentials.json\`エラー

- \`GOOGLE_CREDENTIALS_JSON\`がGitHub Secretsに正しく設定されているか確認
- JSONの形式が正しいか確認（\`{\`で始まり\`}\`で終わる）

---

## 📝 セキュリティ注意事項

### 絶対に公開してはいけないファイル

- ✗ \`credentials.json\`（OAuth 2.0クライアント秘密鍵）
- ✗ \`token.json\`（アクセストークン）
- ✗ サービスアカウントのJSONキー

これらは\`.gitignore\`に含まれています。

### GitHub Secretsの安全性

- GitHub Secretsは暗号化されて保存されます
- ワークフローログには\`***\`でマスクされます
- リポジトリの管理者のみアクセス可能

---

## 🔗 参考リンク

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Google Cloud Console](https://console.cloud.google.com/)
- [サービスアカウント認証について](https://cloud.google.com/iam/docs/service-accounts)
