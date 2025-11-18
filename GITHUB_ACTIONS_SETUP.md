# GitHub Actions 自動実行セットアップ手順

このドキュメントでは、GitHub Actionsで自動的にスプレッドシートを更新する設定方法を説明します。

## 📋 前提条件

- GitHubリポジトリが作成されていること
- Google Cloud Projectが作成されていること
- Google Sheets APIが有効になっていること

## 🔧 セットアップ手順

### 1. Google Cloud サービスアカウントの作成

1. **Google Cloud Consoleにアクセス**
   - https://console.cloud.google.com/

2. **プロジェクトを選択**
   - 既存のプロジェクトを選択、または新規作成

3. **サービスアカウントを作成**
   - 左メニュー → 「IAMと管理」 → 「サービスアカウント」
   - 「サービスアカウントを作成」をクリック
   - サービスアカウント名: `kickstarter-analyzer`（任意）
   - 説明: `GitHub Actions用のサービスアカウント`
   - 「作成して続行」をクリック
   - ロール: 不要（スキップ）
   - 「完了」をクリック

4. **サービスアカウントキーを作成**
   - 作成したサービスアカウントをクリック
   - 「キー」タブ → 「鍵を追加」 → 「新しい鍵を作成」
   - キーのタイプ: JSON
   - 「作成」をクリック
   - **JSONファイルがダウンロードされます（重要: 安全に保管してください）**

### 2. Google Sheetsの共有設定

1. **サービスアカウントのメールアドレスをコピー**
   - ダウンロードしたJSONファイルを開く
   - `client_email`の値をコピー（例: `kickstarter-analyzer@project-id.iam.gserviceaccount.com`）

2. **スプレッドシートを共有**
   - Google Sheetsを開く
   - 右上の「共有」ボタンをクリック
   - サービスアカウントのメールアドレスを貼り付け
   - 権限: **編集者**
   - 「送信」をクリック（通知は不要）

### 3. GitHub Secretsの設定

1. **GitHubリポジトリのSettings → Secrets and variables → Actionsにアクセス**

2. **以下のSecretsを追加**:

   #### GOOGLE_CREDENTIALS_JSON
   - 「New repository secret」をクリック
   - Name: `GOOGLE_CREDENTIALS_JSON`
   - Secret: ダウンロードしたJSONファイルの**全内容**をコピー＆ペースト
   ```json
   {
     "type": "service_account",
     "project_id": "your-project-id",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "kickstarter-analyzer@your-project-id.iam.gserviceaccount.com",
     "client_id": "...",
     ...
   }
   ```

   #### SPREADSHEET_ID
   - Name: `SPREADSHEET_ID`
   - Secret: スプレッドシートのID
   - 例: スプレッドシートのURL `https://docs.google.com/spreadsheets/d/1C1NvFExNAAeUIxXAzsvnq69B50NcIbu8HfVOoRIOAH8/edit`
   - → `1C1NvFExNAAeUIxXAzsvnq69B50NcIbu8HfVOoRIOAH8`

   #### OPENAI_API_KEY（任意）
   - Name: `OPENAI_API_KEY`
   - Secret: OpenAIのAPIキー
   - プロンプト機能を使わない場合は不要（`your-openai-api-key-here`のままでOK）

### 4. リポジトリにプッシュ

```bash
# 変更をコミット
git add .
git commit -m "Add GitHub Actions workflow for auto-updating spreadsheet

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# GitHubにプッシュ
git push origin main
```

### 5. 動作確認

#### 手動実行でテスト

1. GitHubリポジトリの「Actions」タブを開く
2. 左側のワークフロー一覧から「Kickstarter Market Analyzer - Auto Update」を選択
3. 「Run workflow」ボタンをクリック
4. 「Run workflow」を再度クリック
5. 実行状況を確認
6. 成功したら、Google Sheetsを確認

#### 自動実行スケジュール

- **実行時刻**: 毎日 9:00 JST（00:00 UTC）
- **実行内容**: 未処理の行を自動的に処理してスプレッドシートに書き込み

## 📊 実行時刻の変更

`.github/workflows/update_reports.yml`のcron設定を変更してください：

```yaml
on:
  schedule:
    # 毎日 9:00 JST (00:00 UTC) に実行
    - cron: '0 0 * * *'

    # 例: 毎日 18:00 JST (09:00 UTC) に実行
    # - cron: '0 9 * * *'

    # 例: 毎日 9:00 と 18:00 JST に実行
    # - cron: '0 0,9 * * *'
```

**注意**: cronはUTC時刻で指定します（JST - 9時間）

## 🔍 トラブルシューティング

### Error: 403 Forbidden

**原因**: サービスアカウントにスプレッドシートの編集権限がない

**解決策**:
1. スプレッドシートの「共有」設定を確認
2. サービスアカウントのメールアドレスが**編集者**権限で追加されているか確認

### Error: invalid_grant

**原因**: `GOOGLE_CREDENTIALS_JSON`の内容が正しくない

**解決策**:
1. JSONファイル全体がコピーされているか確認
2. 改行やスペースが正しく保持されているか確認（特に`private_key`）
3. Secretを削除して再度追加

### ワークフローが実行されない

**原因**: `.github/workflows/`ディレクトリがmainブランチにプッシュされていない

**解決策**:
```bash
git add .github/workflows/
git commit -m "Add GitHub Actions workflow"
git push origin main
```

## 📝 メンテナンス

### 新しい行の追加

1. Google Sheetsの`kickstarter`シートに新しい行を追加
2. B列（product_url）にKickstarter URLを入力
3. C列（template）からテンプレートを選択
4. D列（name）にメーカー名を入力（任意）
5. E列（to_email）にメールアドレスを入力
6. 次回の自動実行時、または手動実行で処理される

### ログの確認

1. GitHubリポジトリの「Actions」タブを開く
2. 最新の実行をクリック
3. 「update-reports」ジョブをクリック
4. 各ステップのログを確認

## 🎯 次のステップ

- [x] GitHub Actionsワークフロー作成
- [x] サービスアカウント認証設定
- [ ] 初回実行テスト
- [ ] メール通知機能の追加（オプション）
