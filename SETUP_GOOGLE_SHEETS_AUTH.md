# Google Sheets API 認証設定ガイド

## 方法1: サービスアカウント認証（推奨）

### 手順

1. **Google Cloud Consoleにアクセス**
   - https://console.cloud.google.com/

2. **プロジェクトを作成（まだない場合）**
   - 左上のプロジェクト名 → 「新しいプロジェクト」
   - プロジェクト名: `kickstarter-analyzer`

3. **Google Sheets APIを有効化**
   - 「APIとサービス」→ 「ライブラリ」
   - 「Google Sheets API」を検索
   - 「有効にする」をクリック

4. **サービスアカウントを作成**
   - 「APIとサービス」→ 「認証情報」
   - 「認証情報を作成」→ 「サービスアカウント」
   - 名前: `kickstarter-sheets-access`
   - 「作成して続行」

5. **キーをダウンロード**
   - 作成したサービスアカウントをクリック
   - 「キー」タブ → 「鍵を追加」→ 「新しい鍵を作成」
   - 形式: **JSON**
   - ダウンロードされたファイルを `credentials.json` にリネーム

6. **スプレッドシートに共有**
   - `credentials.json`を開く
   - `"client_email": "xxxxx@xxxxx.iam.gserviceaccount.com"` の部分をコピー
   - Google Spreadsheetsの「共有」ボタンをクリック
   - このメールアドレスを**編集者**として追加

7. **credentials.jsonを配置**
   ```bash
   cp /path/to/downloaded/credentials.json /Users/r.umeyama/work/kickstarter-market-analyzer/
   ```

8. **テスト実行**
   ```bash
   cd /Users/r.umeyama/work/kickstarter-market-analyzer
   python3 inspect_spreadsheet.py
   ```

---

## 方法2: OAuth 2.0認証（対話的）

### 手順

1-3は方法1と同じ

4. **OAuth 2.0クライアントIDを作成**
   - 「APIとサービス」→ 「認証情報」
   - 「認証情報を作成」→ 「OAuthクライアントID」
   - アプリケーションの種類: **デスクトップアプリ**
   - 名前: `kickstarter-analyzer-desktop`

5. **JSONをダウンロード**
   - 作成したクライアントIDの右側の「ダウンロード」アイコンをクリック
   - ダウンロードしたファイルを `credentials.json` にリネーム

6. **credentials.jsonを配置**
   ```bash
   cp /path/to/downloaded/credentials.json /Users/r.umeyama/work/kickstarter-market-analyzer/
   ```

7. **初回実行（ブラウザで認証）**
   ```bash
   cd /Users/r.umeyama/work/kickstarter-market-analyzer
   python3 inspect_spreadsheet.py
   ```
   - ブラウザが開いてGoogleアカウントでログイン
   - 「許可」をクリック
   - `token.json`が自動生成され、次回以降は認証不要

---

## 所要時間

- **方法1（サービスアカウント）**: 約5分
- **方法2（OAuth）**: 約5分

---

## セキュリティ

- `credentials.json`と`token.json`は**絶対にGitにコミットしない**
- `.gitignore`に既に追加されているので安全
