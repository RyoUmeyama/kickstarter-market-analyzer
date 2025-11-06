# Kickstarter Market Analyzer

KickstarterプロジェクトのデータをスクレイピングしてChatGPT APIで市場分析レポートを生成し、Google Sheetsに自動書き込みするツールです。

## 🎯 機能

- **Kickstarterスクレイピング**: プロジェクトURLから製品情報を自動取得
  - 製品名、価格、支援総額、支援者数、説明文など
- **ChatGPT API連携**: 取得したデータをもとに日本市場向けレポートを自動生成
- **Google Sheets統合**: レポートを自動的にスプレッドシートに書き込み
- **メール送信**: 生成されたレポートをメールで送信

## 📋 必要なもの

- Python 3.8以上
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

### 4. 環境変数の設定

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

### 5. Google Sheets APIの設定

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
├── check_kickstarter.py       # メインスクリプト
├── kickstarter_scraper.py     # Kickstarterスクレイピング
├── openai_client.py            # OpenAI API連携
├── sheets_client.py            # Google Sheets連携
├── requirements.txt            # Python依存関係
├── .env.example                # 環境変数サンプル
├── .env                        # 環境変数（作成する、コミットしない）
├── .gitignore                  # Git除外設定
├── README.md                   # このファイル
├── SETUP_GOOGLE_SHEETS.md      # Google Sheets APIセットアップ手順
├── credentials.json            # Google認証情報（作成する、コミットしない）
├── token.json                  # Googleアクセストークン（自動生成、コミットしない）
└── data/                       # データ保存ディレクトリ（自動生成）
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

```bash
python test_scraper.py
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

- **OpenAI API**: 使用量に応じて課金
  - GPT-4o-mini: ~$0.15 per 1M tokens (入力)
  - 1レポート生成: 約$0.01-0.05
- **Google Sheets API**: 無料（制限内）
- **その他**: 無料

## 📝 ライセンス

MIT License

## 🔗 参考リンク

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Kickstarter](https://www.kickstarter.com/)
