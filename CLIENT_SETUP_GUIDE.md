# Kickstarter Market Analyzer - クライアント様向けセットアップガイド

このドキュメントでは、Kickstarter Market Analyzerを初めて使用するクライアント様向けに、完全なセットアップ手順を説明します。

## 📋 目次

1. [準備するもの](#準備するもの)
2. [Google スプレッドシートのセットアップ](#google-スプレッドシートのセットアップ)
3. [Google Cloud サービスアカウントの作成](#google-cloud-サービスアカウントの作成)
4. [OpenAI APIキーの取得](#openai-apiキーの取得)
5. [GitHub Secretsの設定](#github-secretsの設定)
6. [使い方](#使い方)
7. [トラブルシューティング](#トラブルシューティング)

---

## 準備するもの

セットアップには以下が必要です：

- ✅ **Googleアカウント**（Google SheetsとGoogle Cloud用）
- ✅ **OpenAIアカウント**（APIキー取得用、クレジットカード登録が必要）
- ✅ **GitHubアカウント**（リポジトリアクセス用）
- ⏱️ **所要時間**: 約30-45分

---

## Google スプレッドシートのセットアップ

### ステップ1: スプレッドシートをコピー

提供されたテンプレートスプレッドシートを自分のGoogleドライブにコピーします。

1. 提供されたスプレッドシートのURLを開く
2. 「ファイル」→「コピーを作成」をクリック
3. 新しいスプレッドシート名を入力（例: `Kickstarter 管理シート`）
4. 「コピーを作成」をクリック

### ステップ2: スプレッドシートIDをメモ

コピーしたスプレッドシートのURLから、IDをコピーしてメモ帳などに保存します。

**URL例**:
```
https://docs.google.com/spreadsheets/d/1C1NvFExNAAeUIxXAzsvnq69B50NcIbu8HfVOoRIOAH8/edit
```

**スプレッドシートID**（`/d/`と`/edit`の間の部分）:
```
1C1NvFExNAAeUIxXAzsvnq69B50NcIbu8HfVOoRIOAH8
```

### ステップ3: シート構造の確認

以下のシートが含まれていることを確認してください：

- ✅ `kickstarter` シート（メインデータ管理）
- ✅ `①1回目送信文` シート（テンプレート）
- ✅ `②無返信用2回目送信` シート（テンプレート）
- ✅ `③無返信3回目` シート（テンプレート）
- ✅ `④自動返信用　2回目送信` シート（テンプレート）
- ✅ `⑤好返信用　詳細レポート送信` シート（テンプレート）

---

## Google Cloud サービスアカウントの作成

GitHub Actionsからスプレッドシートにアクセスするために、サービスアカウントを作成します。

### ステップ1: Google Cloud Console にアクセス

1. ブラウザで以下のURLを開く:
   ```
   https://console.cloud.google.com/
   ```

2. Googleアカウントでログイン

### ステップ2: プロジェクトを作成

1. 画面上部の「プロジェクトを選択」をクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を入力（例: `kickstarter-analyzer`）
4. 「作成」をクリック
5. プロジェクトが作成されたら、そのプロジェクトを選択

### ステップ3: Google Sheets APIを有効化

1. 以下のURLを開く:
   ```
   https://console.cloud.google.com/apis/library/sheets.googleapis.com
   ```

2. 「有効にする」ボタンをクリック

### ステップ4: サービスアカウントを作成

1. 左メニュー → 「IAMと管理」 → 「サービスアカウント」をクリック
2. 「サービスアカウントを作成」をクリック
3. 以下を入力：
   - **サービスアカウント名**: `kickstarter-analyzer`
   - **説明**: `Kickstarter市場分析用サービスアカウント`
4. 「作成して続行」をクリック
5. **ロール**: 何も選択せず「続行」をクリック
6. 「完了」をクリック

### ステップ5: サービスアカウントキー（JSON）をダウンロード

1. 作成したサービスアカウント（`kickstarter-analyzer@...iam.gserviceaccount.com`）をクリック
2. 「キー」タブをクリック
3. 「鍵を追加」 → 「新しい鍵を作成」をクリック
4. **キーのタイプ**: `JSON` を選択
5. 「作成」をクリック
6. **JSONファイルがダウンロードされます**

⚠️ **重要**: このJSONファイルは安全な場所に保管してください。他人に共有しないでください。

### ステップ6: スプレッドシートをサービスアカウントと共有

1. ダウンロードしたJSONファイルをテキストエディタで開く
2. `client_email` の値をコピー（例: `kickstarter-analyzer@...iam.gserviceaccount.com`）
3. Google Sheetsでスプレッドシートを開く
4. 右上の「共有」ボタンをクリック
5. コピーしたメールアドレスを貼り付け
6. 権限を「**編集者**」に設定
7. 「送信」をクリック（通知メールは不要）

---

## OpenAI APIキーの取得

AIによるレポート生成機能を使用するために、OpenAI APIキーを取得します。

### ステップ1: OpenAIアカウントを作成

1. 以下のURLを開く:
   ```
   https://platform.openai.com/signup
   ```

2. アカウントを作成（既にアカウントをお持ちの場合はログイン）

### ステップ2: クレジットカードを登録

1. ログイン後、「Billing」（請求）ページにアクセス
2. クレジットカード情報を登録
3. 初回クレジットを追加（$5-10程度で十分です）

### ステップ3: APIキーを作成

1. 以下のURLを開く:
   ```
   https://platform.openai.com/api-keys
   ```

2. 「Create new secret key」をクリック
3. 名前を入力（例: `Kickstarter Analyzer`）
4. 「Create secret key」をクリック
5. **表示されたAPIキーをコピーしてメモ帳に保存**（`sk-proj-...` で始まる長い文字列）

⚠️ **重要**: APIキーは一度しか表示されません。必ずコピーして安全な場所に保管してください。

### 料金の目安

- **使用モデル**: gpt-4o-mini
- **1回の処理**: 約$0.01-0.03（1-3円）
- **月間100件処理**: 約$1-3（100-300円）

---

## GitHub Secretsの設定

GitHub Actionsで自動実行するために、必要な情報をGitHub Secretsに登録します。

### ステップ1: GitHubリポジトリにアクセス

提供されたリポジトリURLにアクセスします。
（例: `https://github.com/[username]/kickstarter-market-analyzer`）

### ステップ2: Secretsページを開く

1. リポジトリの「Settings」タブをクリック
2. 左メニューの「Secrets and variables」 → 「Actions」をクリック

### ステップ3: 以下の3つのSecretsを追加

#### ① GOOGLE_CREDENTIALS_JSON

1. 「New repository secret」をクリック
2. **Name**: `GOOGLE_CREDENTIALS_JSON`
3. **Secret**:
   - ダウンロードしたJSONファイルをテキストエディタで開く
   - **全体を選択**（Ctrl+A または Cmd+A）
   - コピー（Ctrl+C または Cmd+C）
   - GitHub Secretsの入力欄にペースト（Ctrl+V または Cmd+V）
4. 「Add secret」をクリック

⚠️ **重要**: JSONファイルの最初の `{` から最後の `}` まで**全て**コピーしてください。

#### ② SPREADSHEET_ID

1. 「New repository secret」をクリック
2. **Name**: `SPREADSHEET_ID`
3. **Secret**: ステップ2でメモしたスプレッドシートID
   - 例: `1C1NvFExNAAeUIxXAzsvnq69B50NcIbu8HfVOoRIOAH8`
4. 「Add secret」をクリック

#### ③ OPENAI_API_KEY

1. 「New repository secret」をクリック
2. **Name**: `OPENAI_API_KEY`
3. **Secret**: OpenAIでコピーしたAPIキー
   - 例: `sk-proj-...`
4. 「Add secret」をクリック

### ステップ4: Secretsの確認

以下の3つのSecretsが登録されていることを確認してください：
- ✅ GOOGLE_CREDENTIALS_JSON
- ✅ SPREADSHEET_ID
- ✅ OPENAI_API_KEY

---

## 使い方

### 日常的な使い方

#### 1. データを入力

1. Google Sheetsで `kickstarter` シートを開く
2. 新しい行に以下を入力：
   - **A列（NO）**: 1, 2, 3...（連番）
   - **B列（product_url）**: Kickstarter URL
   - **C列（template）**: ドロップダウンからテンプレートを選択
   - **D列（name）**: メーカー名（例: WashWow）
   - **E列（to_email）**: 送信先メールアドレス

#### 2. GitHub Actionsで実行

1. GitHubリポジトリの「Actions」タブを開く
2. 左側から「**Kickstarter Market Analyzer - Manual Update**」を選択
3. 「**Run workflow**」ボタンをクリック
4. もう一度「**Run workflow**」をクリック
5. 処理が開始されます（通常1-3分で完了）

#### 3. 結果を確認

1. Google Sheetsに戻る
2. 以下の列に結果が自動入力されます：
   - **F列**: 日本語件名
   - **G列**: 英語件名
   - **H列**: 日本語本文（プレーンテキスト）
   - **I列**: 英語本文（プレーンテキスト）
   - **J列**: 日本語本文（HTML形式）
   - **K列**: 英語本文（HTML形式）

#### 4. メール送信（Thunderbird Mail Merge）

1. **CSV出力**
   - Google Sheets → ファイル → ダウンロード → カンマ区切り形式（.csv）

2. **Thunderbirdで読み込み**
   - Thunderbird のメールマージアドオンで読み込み

3. **メール設定**
   - 送信先: `{{to_email}}`
   - 件名: `{{jp_subject}}` または `{{en_subject}}`
   - 本文:
     - HTMLメール: `{{jp_body_html}}` または `{{en_body_html}}`
     - プレーンテキスト: `{{jp_body}}` または `{{en_body}}`

### テンプレートのカスタマイズ

各テンプレートシートの内容は自由に編集できます：

- **A1**: 英語件名
- **B1**: 日本語件名（GOOGLETRANSLATE関数）
- **A2**: 英語本文
- **B2**: 日本語本文（GOOGLETRANSLATE関数）
- **A3**: OpenAIプロンプト（任意、日本語）

**プレースホルダー**:
- `{{URL}}`: Kickstarter URLに自動置換
- `{{name}}`: メーカー名に自動置換
- `{{レポート}}`: OpenAI生成レポートに自動置換（A3にプロンプトがある場合）

---

## トラブルシューティング

### エラー: 403 Forbidden

**原因**: サービスアカウントがスプレッドシートにアクセスできない

**解決策**:
1. スプレッドシートの「共有」設定を確認
2. サービスアカウントのメールアドレス（`...@iam.gserviceaccount.com`）が**編集者**権限で追加されているか確認
3. メールアドレスに間違いがないか確認

### エラー: invalid_grant

**原因**: `GOOGLE_CREDENTIALS_JSON` の内容が正しくない

**解決策**:
1. JSONファイル全体（`{` から `}` まで）がコピーされているか確認
2. GitHub Secretsの `GOOGLE_CREDENTIALS_JSON` を削除して再度追加

### 処理が実行されない

**原因**: 未処理の行がない

**確認**:
1. B列（product_url）にURLが入力されているか
2. H列（jp_body）が空、または100文字未満か
3. 既に処理済みの行は再処理されません

**解決策**: 新しい行を追加するか、既存行のH列を空にしてください

### OpenAI APIエラー

**原因**: APIキーが無効、またはクレジットが不足

**解決策**:
1. OpenAI アカウントでクレジット残高を確認
2. APIキーが正しく設定されているか確認
3. 必要に応じてクレジットを追加

### ワークフローが見つからない

**原因**: リポジトリへのアクセス権限がない

**解決策**:
1. リポジトリのCollaboratorとして招待されているか確認
2. GitHubアカウントでログインしているか確認

---

## サポート

問題が解決しない場合は、以下の情報を添えてお問い合わせください：

1. **エラーメッセージ**（GitHub Actionsのログから）
2. **実行日時**
3. **スクリーンショット**（該当箇所）

---

## 付録: セットアップチェックリスト

セットアップが完了したら、以下をチェックしてください：

- [ ] Google スプレッドシートをコピーした
- [ ] スプレッドシートIDをメモした
- [ ] Google Cloud サービスアカウントを作成した
- [ ] サービスアカウントのJSONキーをダウンロードした
- [ ] Google Sheets APIを有効化した
- [ ] スプレッドシートをサービスアカウントと共有した（編集者権限）
- [ ] OpenAI APIキーを取得した
- [ ] GitHub Secretsを3つ設定した
  - [ ] GOOGLE_CREDENTIALS_JSON
  - [ ] SPREADSHEET_ID
  - [ ] OPENAI_API_KEY
- [ ] GitHub Actionsで手動実行テストを行った
- [ ] スプレッドシートに結果が書き込まれることを確認した

全てチェックできたら、セットアップ完了です！🎉
