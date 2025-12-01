# Kickstarter Market Analyzer

Kickstarter製品の日本市場参入提案メールを自動生成するシステムです。

## 主な機能

1. **管理表からの自動抽出**
   - 管理表のステータス（F列）でフィルタリング
   - 選択したステータスの行を自動でkickstarterシートにコピー
   - ステータスに応じたテンプレートを自動選択
   - 処理件数の上限設定（10/20/30/50/100件から選択）

2. **テンプレートベースのメール生成**
   - Google Sheetsでテンプレートを管理
   - ステータス→テンプレート対応を設定シートで管理
   - テンプレートの追加・編集が自由に可能

3. **OpenAI API統合（任意）**
   - テンプレートにプロンプト（A3セル）を設定すると、OpenAI APIで市場分析レポートを生成
   - プロンプトがなければ、テンプレート本文をそのまま使用

4. **日本市場の類似製品検索**
   - SeleniumによるMakuake自動検索
   - 検索結果（製品名、資金調達額、URL、支援者数）をレポートに挿入
   - **実データのみ使用**（架空のデータは生成しない）

5. **データ正確性の保証**
   - Makuakeから取得した実データのみをレポートに使用
   - 架空の製品名・URL・金額は生成禁止
   - 予測は実データを根拠として計算

6. **共通プロンプト管理**
   - 「設定」シートで全テンプレート共通のAI出力ルールを管理
   - データ正確性、フォーマット、文体などを一元管理

7. **自動翻訳対応**
   - Google SheetsのGOOGLETRANSLATE関数により英語→日本語を自動翻訳

8. **メールマージ対応**
   - Google SheetsをCSV出力してThunderbirdのメールマージで一括送信可能
   - HTML形式メール対応

## システム構成

### 運用フロー

```
Octoparse（スクレイピング）
    ↓
管理表（データ管理・ステータス管理）
    ↓
GitHub Actions「管理表から抽出してメール生成」
    ↓
kickstarterシート（メール本文生成）
    ↓
CSV出力 → Thunderbirdメールマージ → 送信
```

### シート構成

| シート名 | 用途 |
|---------|------|
| 管理表（AMANE） | データ管理。F列でステータス管理 |
| kickstarter | メール生成用。管理表から抽出したデータを処理 |
| 設定 | 共通プロンプト、ステータス→テンプレート対応表 |
| ①〜⑤テンプレート | 各ステータス用のメールテンプレート |

### 設定シート

| セル範囲 | 内容 |
|---------|------|
| A2 | 共通プロンプト（AI出力ルール） |
| C3:D以降 | ステータス→テンプレート対応表 |

### 管理表の列構成

| 列 | 内容 |
|----|------|
| A | 番号 |
| F | 状況（ステータス） |
| Y | name（メーカー名） |
| Z | email（送信先メールアドレス） |
| AA | URL（Kickstarter URL） |

## 日常的な使い方

### 1. 管理表でステータスを設定

管理表のF列（状況）でプルダウンからステータスを選択

### 2. GitHub Actionsで実行

1. GitHubリポジトリの「Actions」タブを開く
2. **「管理表から抽出してメール生成」** を選択
3. 「Run workflow」ボタンをクリック
4. **ステータス**と**処理件数の上限**を選択
5. 「Run workflow」をクリックして実行

### 3. 結果確認・メール送信

1. Google Sheetsでkickstarterシートを確認
2. CSV出力 → Thunderbirdメールマージで送信

## テンプレート・ステータスの追加

### 新しいテンプレートを追加する場合

1. **新しいシートを作成**
2. **テンプレート構造**:
   ```
   A1: 英語件名
   B1: =GOOGLETRANSLATE(A1, "en", "ja")

   A2: 英語本文
   B2: =GOOGLETRANSLATE(A2, "en", "ja")

   A3: プロンプト（日本語、任意）
   ```
3. **設定シートのC:D列**に対応を追加
4. **「ステータス選択肢を同期」** を実行

### プレースホルダー

- `{{URL}}`: Kickstarter URLに置換
- `{{name}}`: メーカー名に置換
- `{{レポート}}`: OpenAI生成レポートに置換

## プロジェクト構成

```
kickstarter-market-analyzer/
├── .github/workflows/
│   ├── extract_and_generate.yml    # 管理表から抽出してメール生成
│   └── sync_workflow_options.yml   # ステータス選択肢を同期
├── main.py                         # メール生成メインスクリプト
├── extract_from_management.py      # 管理表からの抽出スクリプト
├── sheets_client.py                # Google Sheets連携
├── report_generator.py             # レポート生成（OpenAI API）
├── market_search.py                # 類似製品検索（Selenium）
├── sync_workflow_options.py        # 選択肢同期スクリプト
├── requirements.txt                # 依存関係
├── README.md                       # 本ドキュメント
├── CLIENT_SETUP_GUIDE.md           # セットアップガイド（詳細）
└── QUICK_START_GUIDE.md            # クイックスタートガイド
```

## 共通プロンプト管理

### 共通プロンプトの編集

1. スプレッドシートの「設定」シートを開く
2. **A2セル**の内容を編集

### 主要なルール

- **データの正確性**: 市場調査結果の実データのみ使用
- **予測の書き方**: 実データを根拠として明記
- **情報源の明記**: 全データにURLを記載

## 技術仕様

### 使用技術
- Python 3.11+
- Google Sheets API (service account認証)
- OpenAI API (gpt-4o-mini)
- Selenium WebDriver (headless Chrome)
- GitHub Actions

### コスト目安
- OpenAI API: 1回の処理で約1-3円
- 月間100件処理: 約100-300円

## ドキュメント

- [CLIENT_SETUP_GUIDE.md](CLIENT_SETUP_GUIDE.md) - 詳細セットアップガイド
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - クイックスタートガイド
