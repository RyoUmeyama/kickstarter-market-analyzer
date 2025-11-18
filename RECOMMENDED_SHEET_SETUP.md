# Kickstarter市場分析用シート - 推奨構成

## 推奨: 新しいシンプルなシートを作成

既存のスプレッドシートは業務管理用で複雑すぎるため、**Kickstarter市場分析専用の新しいシート**を作成することを推奨します。

---

## 新しいシートの作成手順

### 1. Google Sheetsで新規スプレッドシートを作成

1. https://sheets.google.com/ にアクセス
2. 「空白」をクリックして新規作成
3. スプレッドシート名: **「Kickstarter Market Analyzer」**
4. シート名: **「kickstarter」**

### 2. 列を設定（A〜L列の12列構成）

以下の列を1行目に入力：

| 列 | 列名 | 説明 |
|----|------|------|
| A | NO | 番号（1, 2, 3...） |
| B | product_url | Kickstarter URL（必須） |
| C | product_name | 製品名（任意、空欄可） |
| D | name | メーカー名（任意、空欄可） |
| E | to_email | 送信先メールアドレス（任意） |
| F | subject | メール件名（任意） |
| G | jp_email | 日本語メールテンプレート（任意） |
| H | en_email | 英語メールテンプレート（任意） |
| I | jp_status | 日本語レポートステータス（自動） |
| J | en_status | 英語レポートステータス（自動） |
| **K** | **jp_body** | **日本語市場分析レポート（自動生成）** |
| **L** | **en_body** | **英語市場分析レポート（自動生成）** |

### 3. サンプルデータを入力

2行目以降にサンプルを入力：

```
1	https://www.kickstarter.com/projects/washwow/washwow-the-first-airbag-technology-for-wine-preservation		Ryo Umeyama1	ryo.umeyama.1224+1@gmail.com	Proposal for Market Entry Strategy in Japan	(日本語メールテンプレート)	(英語メールテンプレート)
```

最小限の入力項目：
- **A列（NO）**: 1, 2, 3...
- **B列（product_url）**: Kickstarter URL

他の列は空欄でもOKです。

### 4. スプレッドシートIDをコピー

URLから`/d/`と`/edit`の間の文字列をコピー：

```
https://docs.google.com/spreadsheets/d/【ここがスプレッドシートID】/edit
```

### 5. .envファイルに設定

```bash
cd /Users/r.umeyama/work/kickstarter-market-analyzer
cp .env.example .env
```

`.env`ファイルを編集：

```
SPREADSHEET_ID=【コピーしたスプレッドシートID】
SHEET_NAME=kickstarter
OPENAI_API_KEY=【既存のAPIキー】
```

---

## 実行方法

### 初回実行（認証が必要）

```bash
cd /Users/r.umeyama/work/kickstarter-market-analyzer
python3 main.py
```

ブラウザが開いてGoogleアカウントでログインします（OAuth認証）。

### 2回目以降

認証情報が`token.json`に保存されるため、自動的に実行されます。

---

## 既存のスプレッドシートを使用する場合

既存のスプレッドシート（GID=0のシート）を使用する場合：

1. **Kickstarter URL列を確認**
   - 現在はAA列（27列目）にURLがあります

2. **レポート書き込み列を決定**
   - 例: AO列（41列目）に日本語レポート
   - 例: AP列（42列目）に英語レポート

3. **sheets_client.py を修正**
   - `read_rows()`のrange: `A:AP`（41列目まで読む）
   - `get_unprocessed_rows()`のurl列: `row[26]`（AA列=27列目、0始まりで26）
   - `write_report()`の書き込み列を変更

---

## 推奨: どちらを選ぶべきか？

| | 新しいシート作成 | 既存シート使用 |
|---|---|---|
| **設定時間** | 5分 | 30分（コード修正が必要） |
| **管理のしやすさ** | ◎ シンプル | △ 複雑（57列） |
| **データの独立性** | ◎ 専用シート | △ 業務管理と混在 |
| **推奨度** | ⭐⭐⭐ **強く推奨** | △ 可能だが複雑 |

---

**結論: 新しいシンプルなシートを作成することを強く推奨します。**

既存のスプレッドシートは業務管理用として残し、Kickstarter市場分析は専用シートで運用する方が、
長期的にメンテナンスしやすく、エラーも少なくなります。
