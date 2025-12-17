# Kickstarter Market Analyzer

Kickstarter製品の日本市場参入提案レポートを自動生成するシステムです。

## 主な機能

### 1. V2詳細レポート生成システム

**プロのマーケッターによる16セクション構成の詳細レポート**を自動生成：

| セクション | 内容 |
|-----------|------|
| エグゼクティブサマリー | Kickstarter実績、成功確度、推奨価格帯、主要リスク |
| ① 製品特徴・日本市場での通用度評価 | 製品仕様、日本での通用性分析 |
| ② Kickstarter販売価格 | 平均Pledge、想定リテール価格 |
| ③ 調達実績 | 調達額、バッカー数、達成率 |
| ④ 日本CFでの既出可否 | Makuake/CAMPFIRE検索結果 |
| ⑤ 日本EC（Amazon等）での既出可否 | Amazon.co.jp流通状況 |
| ⑥ 日本CFにおける主要競合比較 | 実データに基づく競合分析 |
| ⑦ ターゲット顧客・マーケティング方向性 | ターゲット層、訴求ポイント、プロモーション戦略 |
| ⑧ 日本での独占販売契約の可能性 | 難易度、交渉条件 |
| ⑨ 規制（PSE/技適） | 認証要否、費用、期間 |
| ⑩ 想定仕入単価（FOB） | MSRP、FOB推定（楽観/標準/悲観） |
| ⑪ 収支シミュレーション（Makuake） | 価格帯別・仕入れ別の粗利シミュレーション |
| ⑫ 日本EC成功可能性・課題 | Amazon等での展開可能性 |
| ⑬ 量販への卸の可能性・課題 | ドン・キホーテ等への卸可能性 |
| ⑭ Makuakeで利益100万円超の可否 | 到達条件、必要台数 |
| ⑮ リスク分析と対応策 | 市場/オペレーション/規制リスク |
| ⑯ 最終判定（出品提案・成功戦略） | 成功確度、必須条件、推奨アクション |

### 2. 管理表からの自動抽出

- 管理表のステータス（F列）でフィルタリング
- 選択したステータスの行を自動でkickstarterシートにコピー
- ステータスに応じたテンプレートを自動選択
- 処理件数の上限設定（**1件から100件**まで選択可能）

### 3. 多角的データ収集

| データソース | 取得内容 |
|-------------|----------|
| Kickstarter | タイトル、調達額、バッカー数、目標金額 |
| Kicktraq | 達成率、バッカー統計（フォールバック） |
| BackerKit | 平均Pledge、詳細統計 |
| Amazon.co.jp | 同一ブランド・類似製品の流通状況 |
| Makuake | 競合製品、カテゴリ別プロジェクト |
| CAMPFIRE | 競合製品（日本IPプロキシ経由） |
| DuckDuckGo | Web検索による補足情報 |

### 4. AI分析エンジン

- **WebResearcher**: Web調査による製品・市場情報収集
- **IndustryAnalyzer**: 業界分析（市場規模、成熟度、参入障壁）
- **CompetitorAnalyzer**: 競合分析（直接競合、間接競合、差別化戦略）
- **StrictEvaluator**: 厳格評価（データ品質、レッドフラグ、Go/No-Go判定）
- **CalculationEngine**: 収支シミュレーション（FOB推定、価格帯別利益計算）

### 5. データ正確性の保証

- 実データのみ使用（架空のデータは生成禁止）
- すべての数値にソースURLを記載
- AI推定の競合他社名は記載禁止
- 取得できなかったデータは「データ取得失敗」として正直に報告

## システム構成

### 運用フロー

```
Octoparse（スクレイピング）
    ↓
管理表（データ管理・ステータス管理）
    ↓
GitHub Actions「管理表から抽出してメール生成」
    ↓
V2レポート生成（6パート分割生成）
    ↓
kickstarterシート（メール本文）
    ↓
CSV出力 → Thunderbirdメールマージ → 送信
```

### プロジェクト構成

```
kickstarter-market-analyzer/
├── .github/workflows/
│   ├── extract_and_generate.yml    # メイン: 管理表から抽出してメール生成
│   ├── sync_workflow_options.yml   # ステータス選択肢を同期
│   └── fix_template_typos.yml      # テンプレート誤字修正
├── main.py                         # メール生成メインスクリプト
├── analyzer_v2.py                  # V2分析オーケストレーター
├── report_generator_v2.py          # V2レポート生成（6パート分割）
├── report_generator.py             # レポート生成（統合）
├── data_collector.py               # データ収集（Kickstarter/CF/Amazon）
├── web_researcher.py               # Web調査（DuckDuckGo検索）
├── calculation_engine.py           # 収支計算エンジン
├── industry_analyzer.py            # 業界分析
├── competitor_analyzer.py          # 競合分析
├── strict_evaluator.py             # 厳格評価
├── market_search.py                # 市場検索（Makuake/CAMPFIRE）
├── sheets_client.py                # Google Sheets連携
├── extract_from_management.py      # 管理表からの抽出
├── fix_template_typos.py           # テンプレート誤字修正
├── test_single_report.py           # 単一製品テスト
├── sync_workflow_options.py        # 選択肢同期
├── setup_industry_data.py          # 業界データ設定（初期設定用）
├── update_settings.py              # 設定更新（初期設定用）
├── templates/
│   └── sample_report_v2.md         # レポートサンプル
├── docs/
│   ├── progress_report_20241209.md # 進捗報告
│   └── market_research_expansion_proposal.md
├── requirements.txt
├── CLAUDE.md                       # Claude Code設定
├── CLIENT_SETUP_GUIDE.md           # クライアント向けセットアップガイド
├── QUICK_START_GUIDE.md            # クイックスタートガイド
└── README.md
```

## 日常的な使い方

### 1. 管理表でステータスを設定

管理表のF列（状況）でプルダウンからステータスを選択

### 2. GitHub Actionsで実行

1. GitHubリポジトリの「Actions」タブを開く
2. **「管理表から抽出してメール生成」** を選択
3. 「Run workflow」ボタンをクリック
4. **ステータス**と**処理件数の上限**を選択（1件から100件）
5. 「Run workflow」をクリックして実行

### 3. 結果確認・メール送信

1. Google Sheetsでkickstarterシートを確認
2. CSV出力 → Thunderbirdメールマージで送信

## ローカルでのテスト

単一製品のレポート生成をテストできます：

```bash
# デフォルトURL（AKASO Sight）でテスト
python test_single_report.py

# 特定のURLでテスト
python test_single_report.py "https://www.kickstarter.com/projects/xxx/yyy"
```

## シート構成

| シート名 | 用途 |
|---------|------|
| 管理表（AMANE） | データ管理。F列でステータス管理 |
| kickstarter | メール生成用。管理表から抽出したデータを処理 |
| 設定 | 共通プロンプト、システム設定、ステータス→テンプレート対応表 |
| ①〜⑤テンプレート | 各ステータス用のメールテンプレート |

## 技術仕様

### 使用技術

- Python 3.11+
- OpenAI API (gpt-4o-mini / gpt-4o)
- Google Sheets API (service account認証)
- Playwright (headless Chromium)
- Bright Data (日本IPプロキシ、CAMPFIRE海外IP制限対応)
- DuckDuckGo Search API
- GitHub Actions

### データ取得の優先順位

1. **直接接続**（Playwright） - 無料
2. **Kicktraq/BackerKit** - 無料フォールバック
3. **Bright Data プロキシ** - 有料、CAMPFIRE等の日本IP制限対応

### 処理時間の目安

- 1件あたり約3-5分（V2詳細レポート生成含む）
- GitHub Actions タイムアウト: 120分

### コスト目安

- OpenAI API: 1回の処理で約10-20円（V2レポート6パート生成）
- Bright Data: 必要時のみ使用

## 開発者向け情報

### Gitリポジトリ構成

```bash
# 両方にpush（必須）
git push origin main && git push client main
```

| リモート | リポジトリ | 用途 |
|---------|-----------|------|
| origin | RyoUmeyama/kickstarter-market-analyzer | バックアップ |
| client | koki4117/kickstarter-market-analyzer | **本番（GitHub Actions実行）** |

### GitHub Secrets（koki4117リポジトリ）

| Secret名 | 説明 |
|----------|------|
| SPREADSHEET_ID | Google SpreadsheetのID |
| OPENAI_API_KEY | OpenAI APIキー |
| GOOGLE_CREDENTIALS_JSON | サービスアカウントの認証情報JSON |
| BRIGHT_DATA_USERNAME | Bright Dataのユーザー名 |
| BRIGHT_DATA_PASSWORD | Bright Dataのパスワード |
| PAT_TOKEN | GitHub Personal Access Token |

## 更新履歴

### 2024-12-17
- 処理件数の最小値を1件に変更（1件単位でのテスト実行が可能に）
- エグゼクティブサマリーをレポート冒頭に追加
- セクション⑦（ターゲット顧客・マーケティング方向性）追加
- セクション⑮（リスク分析と対応策）追加
- セクション⑯（最終判定）追加
- テンプレート誤字修正ワークフロー追加
- 達成率0%表示問題を修正

### 2024-12-16
- URL括弧内スペース問題修正（Thunderbirdメールマージ対応）
- en_body/en_subject英語翻訳対応

### 2024-12-12
- V2詳細レポート生成システム導入
- 6パート分割生成による高品質レポート
- Bright Data日本IPプロキシ導入
