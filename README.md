# Kickstarter Market Analyzer

KickstarterプロジェクトのデータをスクレイピングしてChatGPT APIで市場分析レポートを生成し、Google Sheetsに自動書き込みするツールです。

## 🎯 機能

- **Kickstarterスクレイピング**: プロジェクトURLから製品情報を自動取得
  - 製品名、価格、支援総額、支援者数、説明文など
  - **Selenium使用**: Bot検出を回避して確実にデータ取得
- **ChatGPT API連携**: 取得したデータをもとに日本市場向けレポートを自動生成
- **Google Sheets統合**: レポートを自動的にスプレッドシートに書き込み
- **GitHub Actions対応**: クライアント側の技術的ハードルを最小化

## 💻 実行環境の選択

### 推奨: GitHub Actions（クライアント向け）⭐

**こんな方におすすめ**:
- ITリテラシーに自信がない方
- Windowsユーザー
- Python環境のセットアップが難しい方

**メリット**:
- ✓ **技術的ハードルがほぼゼロ**（Google Sheetsに入力するだけ）
- ✓ PCへのソフトウェアインストール不要
- ✓ 手動トリガーまたは自動実行
- ✓ 無料（月2000分まで）

**使い方**:
1. Google Sheetsに行を追加
2. GitHubのボタンをクリック（または自動実行を待つ）
3. 結果がGoogle Sheetsに自動書き込み

詳細は **[SETUP_FOR_CLIENT.md](SETUP_FOR_CLIENT.md)** を参照

---

### ローカル実行（開発者向け）

**こんな方におすすめ**:
- Python環境のセットアップに慣れている方
- ローカルでカスタマイズしたい方
- 即座に実行結果を確認したい方

**必要なもの**:
- Python 3.8以上
- Google Chrome + ChromeDriver
- コマンドライン操作の基本知識

詳細は下記の「セットアップ」セクションを参照

---

## ⚡️ 重要: スクレイピング方法

KickstarterはBot保護が非常に強力なため、**Selenium（実ブラウザ自動化）を使用**します。

詳細は [SCRAPING_STRATEGIES.md](SCRAPING_STRATEGIES.md) を参照してください。

## 📋 必要なもの

- Python 3.8以上
- **Google Chrome**（Seleniumで使用）
- **ChromeDriver**（自動インストール可能）
- OpenAI APIキー
- Google Cloud Platformアカウント（Google Sheets API用）
- （オプション）SMTPサーバー（メール送信用）

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd kickstarter-market-analyzer
```

### 2. 仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. ChromeDriverのインストール

#### Mac
```bash
brew install --cask chromedriver

# セキュリティ設定を解除
xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver
```

#### Linux
```bash
# ChromeDriverをダウンロード
wget https://chromedriver.chromium.org/downloads

# 解凍して/usr/local/binに配置
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

#### Windows
[ChromeDriver公式サイト](https://chromedriver.chromium.org/)からダウンロードし、PATHに追加

### 5. 環境変数の設定

`.env.example`を`.env`にコピーして設定：

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Google Sheets
SPREADSHEET_ID=your_spreadsheet_id_here
SHEET_NAME=kickstarter

# Email (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
RECIPIENT_EMAIL=recipient@gmail.com
```

### 6. Google Sheets APIの設定

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Google Sheets APIを有効化
3. OAuth 2.0クライアントIDを作成（デスクトップアプリケーション）
4. `credentials.json`をダウンロードしてプロジェクトルートに配置

詳細は [SETUP_GOOGLE_SHEETS.md](SETUP_GOOGLE_SHEETS.md) を参照

## 📊 スプレッドシートの列構成

| 列 | 内容 | 入力方法 |
|----|------|----------|
| A | 番号 | 手動 |
| B | Kickstarter URL | 手動 |
| C | 商品名 | 手動（または自動取得） |
| D | メーカー名 | 手動 |
| E | クリエーター名 | 手動 |
| F | 日本語レポート | 自動生成 |
| G | 英語レポート | 自動生成 |

## 🔧 使い方

### 基本的な実行

```bash
# 仮想環境を有効化
source venv/bin/activate

# スクリプトを実行
python check_kickstarter.py
```

### デバッグモード

```bash
# メール送信をスキップ
export DEBUG_MODE=true
python check_kickstarter.py
```

### 特定の行のみ処理

```bash
# 3行目のみ処理
python check_kickstarter.py --row 3
```

## 📁 ファイル構成

```
kickstarter-market-analyzer/
├── check_kickstarter.py              # メインスクリプト
├── kickstarter_scraper.py            # Kickstarterスクレイピング（Requests版・参考）
├── kickstarter_scraper_selenium.py   # Kickstarterスクレイピング（Selenium版・推奨）⭐️
├── openai_client.py                  # OpenAI API連携
├── sheets_client.py                  # Google Sheets連携（OAuth & サービスアカウント対応）
├── requirements.txt                  # Python依存関係
├── .env.example                      # 環境変数サンプル
├── .env                              # 環境変数（作成する、コミットしない）
├── .gitignore                        # Git除外設定
├── README.md                         # このファイル
├── SETUP_FOR_CLIENT.md               # クライアント向けセットアップガイド（GitHub Actions）⭐️
├── SETUP_GOOGLE_SHEETS.md            # Google Sheets APIセットアップ手順
├── SCRAPING_STRATEGIES.md            # スクレイピング戦略の詳細⭐️
├── .github/workflows/
│   └── analyze_kickstarter.yml       # GitHub Actionsワークフロー⭐️
├── credentials.json                  # Google認証情報（作成する、コミットしない）
├── token.json                        # Googleアクセストークン（自動生成、コミットしない）
└── data/                             # データ保存ディレクトリ（自動生成）
```

## ⚙️ 自動実行（cron）

定期的に実行する場合：

```bash
# crontabを編集
crontab -e

# 毎日10:00に実行
0 10 * * * cd /Users/r.umeyama/work/kickstarter-market-analyzer && /Users/r.umeyama/work/kickstarter-market-analyzer/venv/bin/python check_kickstarter.py >> logs/cron.log 2>&1
```

## 🧪 テスト

### Kickstarterスクレイピングのテスト

#### Selenium版（推奨）
```bash
python kickstarter_scraper_selenium.py
```

#### Requests版（参考・ブロックされる）
```bash
python kickstarter_scraper.py
```

### OpenAI API接続テスト

```bash
python test_openai.py
```

### Google Sheets接続テスト

```bash
python test_sheets.py
```

## ⚠️ トラブルシューティング

### Kickstarterアクセスが403エラー

- User-Agentやヘッダーを調整
- アクセス頻度を下げる（sleep追加）
- プロキシの使用を検討

### Google Sheets認証エラー

- `token.json`を削除して再認証
- `credentials.json`が正しいか確認

### OpenAI APIエラー

- APIキーが正しいか確認
- 利用制限を確認
- `max_tokens`を調整

## 💰 コスト

### GitHub Actions実行の場合
- **GitHub Actions**: 月2000分まで無料（1回2〜5分 = 月400回まで無料）
- **OpenAI API**: 1レポート約$0.01〜$0.05（使用量に応じて課金）
  - GPT-4o-mini: ~$0.15 per 1M tokens (入力)
- **Google Sheets API**: 無料（制限内）
- **合計**: 月$1〜$5程度（主にOpenAI API）

### ローカル実行の場合
- **OpenAI API**: 上記と同じ
- **Google Sheets API**: 無料（制限内）
- **その他**: 無料

## 📝 ライセンス

MIT License

## 🔗 参考リンク

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Kickstarter](https://www.kickstarter.com/)
