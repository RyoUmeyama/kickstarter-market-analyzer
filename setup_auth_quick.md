# Google Sheets API 認証設定 - クイックガイド

## 最も簡単な方法: OAuth 2.0認証（5分で完了）

### 手順

1. **Google Cloud Consoleにアクセス**
   https://console.cloud.google.com/

2. **プロジェクトを作成（まだない場合）**
   - 左上のプロジェクト選択 → 「新しいプロジェクト」
   - プロジェクト名: `kickstarter-analyzer`
   - 「作成」をクリック

3. **Google Sheets APIを有効化**
   - 左メニュー「APIとサービス」→ 「ライブラリ」
   - 検索ボックスに「Google Sheets API」と入力
   - 「Google Sheets API」をクリック
   - 「有効にする」をクリック

4. **OAuth同意画面を設定**
   - 左メニュー「APIとサービス」→ 「OAuth同意画面」
   - User Type: **外部**を選択 → 「作成」
   - アプリ名: `Kickstarter Analyzer`
   - ユーザーサポートメール: あなたのGmailアドレス
   - デベロッパーの連絡先: あなたのGmailアドレス
   - 「保存して次へ」を3回クリック（スコープ、テストユーザーはスキップ）

5. **OAuth 2.0クライアントIDを作成**
   - 左メニュー「APIとサービス」→ 「認証情報」
   - 「認証情報を作成」→ 「OAuthクライアントID」
   - アプリケーションの種類: **デスクトップアプリ**
   - 名前: `kickstarter-desktop`
   - 「作成」をクリック

6. **JSONをダウンロード**
   - 「認証情報」ページで、作成したクライアントIDの右側のダウンロードアイコン（↓）をクリック
   - ダウンロードされたJSONファイルを確認

7. **credentials.jsonとして保存**
   - ダウンロードしたファイル名は `client_secret_XXXXX.json` のような名前
   - このファイルを `credentials.json` にリネームして、プロジェクトディレクトリに配置

完了！次のステップに進んでください。
