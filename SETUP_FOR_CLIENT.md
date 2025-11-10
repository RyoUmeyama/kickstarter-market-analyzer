# クライアント向けセットアップガイド

このドキュメントは、ITリテラシーがそこまで高くないWindowsユーザー向けに、Kickstarter Market Analyzerを使用するためのセットアップ手順を説明します。

## 🎯 システム概要

**クライアントの操作**:
1. Google Sheetsに分析したいKickstarter URLを入力
2. GitHubのボタンをクリック（または自動実行を待つ）
3. Google Sheetsに結果が自動的に書き込まれる

**裏側で動いていること**:
- GitHub Actions（クラウド上の自動実行環境）がPythonスクリプトを実行
- KickstarterからSeleniumでデータを取得
- ChatGPT APIで市場分析レポートを生成
- Google Sheetsに自動書き込み

**クライアント側に必要なもの**:
- ✓ Googleアカウント（Gmail）
- ✓ GitHubアカウント（無料）
- ✓ OpenAI APIキー（有料）
- ✗ ~~Pythonのインストール~~ **不要**
- ✗ ~~コマンドライン操作~~ **不要**

---

## 📋 初回セットアップ（コンサルタントが実施）

### ステップ1: GitHubリポジトリのセットアップ

1. **リポジトリの作成**（すでに完了）
   - https://github.com/RyoUmeyama/kickstarter-market-analyzer

2. **GitHub Secretsの設定**
   - リポジトリページ → Settings → Secrets and variables → Actions
   - 以下のSecretsを追加：

| Secret名 | 説明 | 取得方法 |
|---------|------|---------|
| `OPENAI_API_KEY` | OpenAI APIキー | [OpenAI Platform](https://platform.openai.com/api-keys)で作成 |
| `SPREADSHEET_ID` | Google SpreadsheetのID | スプレッドシートURLの`/d/`と`/edit`の間の文字列 |
| `SHEET_NAME` | シート名（例: kickstarter） | スプレッドシートのシート名 |
| `GOOGLE_CREDENTIALS_JSON` | Google認証情報 | 後述の手順で取得 |

### ステップ2: Google Sheets APIの設定

詳細は `SETUP_GOOGLE_SHEETS.md` を参照

**概要**:
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Google Sheets APIを有効化
3. サービスアカウントを作成
4. JSONキーをダウンロード
5. JSONキーの内容をGitHub Secretsの`GOOGLE_CREDENTIALS_JSON`に設定
6. スプレッドシートにサービスアカウントのメールアドレスを共有

### ステップ3: Google Sheetsの準備

スプレッドシートを以下の列構成で作成：

| A | B | C | D | E | F〜J | K | L |
|---|---|---|---|---|------|---|---|
| 番号 | Kickstarter URL | 商品名 | メーカー名 | クリエーター名 | （任意） | 日本語レポート | 英語レポート |
| 1 | https://www.kickstarter.com/projects/... | （任意） | 〇〇社 | John Doe | - | （自動生成） | （自動生成） |

**注意**:
- 1行目はヘッダー（列名）
- K列（日本語レポート）が空、または100文字未満の行が自動処理されます
- C列（商品名）は空でもOK（自動取得されます）
- F〜J列は任意項目（既存データがある場合に使用）

---

## 🚀 クライアントの使い方

### 方法1: 手動実行（即座に実行したい場合）

1. GitHubリポジトリにアクセス
   - https://github.com/RyoUmeyama/kickstarter-market-analyzer

2. **Actions**タブをクリック

3. 左サイドバーから**Kickstarter Market Analyzer**を選択

4. 右上の**Run workflow**ボタンをクリック

5. ブランチ（main）を確認して**Run workflow**をクリック

6. 30秒〜5分程度で処理完了
   - 緑のチェックマーク: 成功
   - 赤のXマーク: エラー（ログを確認）

7. Google Sheetsを確認
   - K列（日本語レポート）に結果が書き込まれています

### 方法2: 自動実行（毎日定時）

- **実行時刻**: 毎日9:00 JST（日本時間）※現在は無効化されています
- **処理内容**: K列が空、または100文字未満の行を自動的に処理
- **クライアント操作**: 不要（Google Sheetsに行を追加するだけ）

---

## 💰 コスト

### GitHub Actions
- **無料枠**: 月2000分（約33時間）
- **本プロジェクト**: 1回の実行で約2〜5分
- **月間コスト**: 無料（400回実行/月まで無料）

### OpenAI API
- **GPT-4o-mini**: ~$0.15 per 1M tokens (入力)
- **1レポート生成**: 約$0.01〜$0.05
- **月間コスト**: 利用量による（100レポート = $1〜$5程度）

### Google Sheets API
- **無料**（制限内）

**合計**: 月$1〜$5程度（主にOpenAI API）

---

## 🔧 トラブルシューティング

### エラー1: GitHub Actionsが失敗する（赤のXマーク）

**確認事項**:
1. GitHub Secretsが正しく設定されているか
   - Settings → Secrets and variables → Actions
2. スプレッドシートにサービスアカウントが共有されているか
3. OpenAI APIキーが有効か（残高があるか）

**ログの確認方法**:
- Actions → 失敗したワークフロー → Run analyzer → ログを展開

### エラー2: Google Sheetsに書き込まれない

**確認事項**:
1. K列（日本語レポート）が空、または100文字未満か
2. B列（Kickstarter URL）が正しいURL形式か
3. スプレッドシートIDが正しいか（GitHub Secrets）

### エラー3: OpenAI APIエラー

**確認事項**:
1. APIキーが正しいか
2. OpenAIアカウントに残高があるか
3. 利用制限（Rate Limit）を超えていないか

---

## 📞 サポート

セットアップでお困りの場合は、コンサルタント（梅山）までご連絡ください。

---

## 📝 補足: なぜこの方法を選んだのか

### 他の選択肢との比較

| 方法 | クライアント操作 | コスト | 難易度 |
|------|----------------|--------|--------|
| **GitHub Actions**（採用） | Google Sheets入力のみ | $1〜5/月 | ⭐ 低 |
| Windows PC実行 | Python、ChromeDriver等のインストール | $1〜5/月 | ⭐⭐⭐⭐⭐ 高 |
| VPS（サーバー） | なし | $10〜20/月 | ⭐⭐⭐ 中 |
| Apps Script + 有料API | Google Sheets内 | $50〜/月 | ⭐⭐ 低〜中 |

**結論**: ITリテラシーがそこまで高くないWindowsユーザーには、GitHub Actionsが最適です。
