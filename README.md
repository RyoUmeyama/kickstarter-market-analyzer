# Kickstarter Market Analyzer

KickstarterプロジェクトのデータをスクレイピングしてChatGPT APIで市場分析レポートを生成し、Google Sheetsに自動書き込みするツールです。

## 🎯 機能

- **Kickstarterスクレイピング**: プロジェクトURLから製品情報を自動取得
  - 製品名、価格、支援総額、支援者数、説明文など
  - **Selenium使用**: Bot検出を回避して確実にデータ取得
- **ChatGPT API連携**: 取得したデータをもとに日本市場向けレポートを自動生成
  - **改善版プロンプト対応**⭐: 事業者目線の詳細な分析レポート（類似製品5件以上、3シナリオ予測、収益性分析等）
  - コスト増加: 月+¥2（50件の場合）で品質飛躍的向上
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
| F〜J | （任意・既存データ用） | 手動 |
| K | 日本語レポート | 自動生成 |
| L | 英語レポート | 自動生成 |

**注意**:
- K列（日本語レポート）が空、または100文字未満の場合に未処理として検出されます
- 既存の長いレポート（100文字以上）は再処理されません

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

## 🔥 プロンプト改善版の使用⭐ **NEW**

クライアントから「レポートが客観的な概要に留まっている」「事業者目線の詳細な分析が欲しい」というフィードバックを受けた場合、改善版プロンプトを使用できます。

### 改善内容

| 項目 | 現行版 | 改善版 |
|------|--------|--------|
| **類似製品調査** | 曖昧 | **最低5件**の製品名・URL・実績額 |
| **価格戦略** | 1段階 | **3段階**（早割・通常・リテール） + 収益性分析 |
| **販売予測** | 1パターン | **3シナリオ**（保守的・標準・楽観的） |
| **競合分析** | なし | **新規**: 強み・弱み・USP |
| **長期戦略** | なし | **新規**: フェーズ2・3計画 |

### コスト影響

- **1件あたり**: +¥0.03（現行¥0.48 → 改善版¥0.51）
- **月50件**: +¥2
- **月100件**: +¥4

### 使い方

#### 1. 詳細ドキュメントを確認

```bash
# トークン数・コスト試算
open consulting/PROMPT_IMPROVEMENT_ANALYSIS.md

# 現行版 vs 改善版の比較
open consulting/PROMPT_COMPARISON.md

# 実装ガイド
open consulting/IMPLEMENTATION_GUIDE.md
```

#### 2. check_kickstarter.pyでインポートを変更

```python
# Before:
from openai_client import MarketReportGenerator

# After:
from openai_client_improved import ImprovedMarketReportGenerator as MarketReportGenerator
```

#### 3. テスト実行

```bash
# スプレッドシートのK列（処理済みマーカー）を1行だけクリア
# その後実行
python check_kickstarter.py
```

#### 4. 結果確認

以下が含まれていることを確認:
- [ ] 類似製品が5件以上記載
- [ ] 製品名・URL・実績額が具体的
- [ ] 価格戦略が3段階（早割・通常・リテール）
- [ ] 販売予測が3シナリオ
- [ ] 成功確率がパーセンテージで記載
- [ ] リスク分析が5項目以上
- [ ] 競合優位性分析（強み・弱み）
- [ ] 文字数が2000-2500文字程度

詳細は `consulting/IMPLEMENTATION_GUIDE.md` を参照してください。

---

## 📁 ファイル構成

```
kickstarter-market-analyzer/
├── check_kickstarter.py              # メインスクリプト
├── kickstarter_scraper.py            # Kickstarterスクレイピング（Requests版・参考）
├── kickstarter_scraper_selenium.py   # Kickstarterスクレイピング（Selenium版・推奨）⭐️
├── openai_client.py                  # OpenAI API連携（現行版）
├── openai_client_improved.py         # OpenAI API連携（改善版・事業者目線の詳細分析）⭐️ **NEW**
├── sheets_client.py                  # Google Sheets連携（OAuth & サービスアカウント対応）
├── convert_to_docx.py                # Markdown → Word変換スクリプト
├── generate_html.py                  # Markdown → HTML変換スクリプト（Bootstrap付き）⭐️
├── requirements.txt                  # Python依存関係
├── .env.example                      # 環境変数サンプル
├── .env                              # 環境変数（作成する、コミットしない）
├── .gitignore                        # Git除外設定
├── README.md                         # このファイル
├── SETUP_FOR_CLIENT.md               # クライアント向けセットアップガイド（GitHub Actions）⭐️
├── SETUP_GOOGLE_SHEETS.md            # Google Sheets APIセットアップ手順
├── SCRAPING_STRATEGIES.md            # スクレイピング戦略の詳細⭐️
├── SPREADSHEET_STRUCTURE.md          # スプレッドシート構造の詳細⭐️
├── .github/workflows/
│   └── analyze_kickstarter.yml       # GitHub Actionsワークフロー⭐️
├── consulting/                       # コンサルティング資料（.gitignore対象）⭐️
│   ├── README.md                     # 使い方ガイド
│   ├── PROMPT_IMPROVEMENT_ANALYSIS.md # プロンプト改善の詳細分析⭐️ **NEW**
│   ├── PROMPT_COMPARISON.md          # 現行版 vs 改善版の比較⭐️ **NEW**
│   ├── IMPLEMENTATION_GUIDE.md       # 改善版プロンプトの実装ガイド⭐️ **NEW**
│   ├── SHARING_GUIDE.md              # Markdown共有方法（HackMD等）⭐️
│   ├── *.docx                        # Word形式の資料（ITリテラシーが高くない方向け）
│   ├── *.html                        # HTML形式の資料（ブラウザで閲覧）
│   ├── *.md                          # Markdown形式の資料
│   └── *.csv                         # Google Sheets用CSV
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

### OpenAI API（実測値ベース）

#### GPT-4o-mini（推奨）

| プロンプト版 | 1件あたり | 月50件 | 月100件 |
|-------------|----------|--------|---------|
| **現行版** | ¥0.48 | ¥24 | ¥48 |
| **改善版**⭐ | ¥0.51 | ¥26 | ¥52 |
| **差分** | +¥0.03 | +¥2 | +¥4 |

- 入力: $0.15/1M tokens
- 出力: $0.60/1M tokens
- 現行版: 約6,440トークン（入力1,400 + 出力5,040）
- 改善版: 約7,640トークン（入力2,600 + 出力5,040）

#### GPT-4o

| プロンプト版 | 1件あたり | 月50件 | 月100件 |
|-------------|----------|--------|---------|
| **現行版** | ¥8.06 | ¥403 | ¥806 |
| **改善版** | ¥8.94 | ¥447 | ¥894 |
| **差分** | +¥0.88 | +¥44 | +¥88 |

**推奨**: GPT-4o-miniで十分な品質が得られます。

### その他のコスト

- **GitHub Actions**: 月2000分まで無料（1回2〜5分 = 月400回まで無料）
- **Google Sheets API**: 無料（制限内）

### 合計コスト目安

| 構成 | 月50件 | 月100件 |
|------|--------|---------|
| **現行版 + GPT-4o-mini** | ¥24 | ¥48 |
| **改善版⭐ + GPT-4o-mini** | ¥26 | ¥52 |
| **現行版 + GPT-4o** | ¥403 | ¥806 |
| **改善版 + GPT-4o** | ¥447 | ¥894 |

**結論**: 改善版でも月+¥2程度の追加コストで、レポート品質が飛躍的に向上

## 📝 ライセンス

MIT License

## 🔗 参考リンク

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Kickstarter](https://www.kickstarter.com/)
