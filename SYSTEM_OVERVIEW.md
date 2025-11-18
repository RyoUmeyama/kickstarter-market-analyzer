# Kickstarter Market Analyzer - システム概要

## 🎯 システムの目的

Kickstarter製品に対する日本市場参入提案メールを、複数のテンプレートから選択して自動生成するシステムです。

## 📊 システム構成

### 1. Google Spreadsheet構成

#### kickstarterシート（一覧管理シート）
製品URL、テンプレート選択、送信先情報を管理するマスターシート

| 列 | 列名 | 説明 |
|----|------|------|
| A | NO | 番号（1, 2, 3...） |
| B | product_url | Kickstarter URL（必須） |
| C | template | テンプレート名（ドロップダウンリスト選択） |
| D | name | 担当者名 |
| E | to_email | 送信先メールアドレス |
| F | subject | メール件名 |
| G | status | 処理ステータス（自動更新） |
| H | jp_report | 日本語レポート（自動生成） |
| I | en_report | 英語レポート（自動生成） |

**テンプレート選択肢（C列のドロップダウンリスト）:**
1. ①1回目送信文
2. ②無返信用2回目送信
3. ➂無返信3回目
4. ④自動返信用　2回目送信
5. ⑤好返信用　詳細レポート送信

#### テンプレートシート（5種類）
各テンプレートは独立したシートとして存在

**構造:**
- 1行目 A列: 英語件名
- 2行目 A列: 英語本文テンプレート
- 2行目 B列: 日本語本文テンプレート

**プレースホルダー:**
- `{{URL}}`: Kickstarter URLに置換
- `{{name}}`: メーカー名に置換

### 2. ファイル構成

```
kickstarter-market-analyzer/
├── .env                          # 環境変数（SPREADSHEET_ID等）
├── credentials.json              # OAuth 2.0認証情報
├── token.json/token.pickle       # 認証トークン（自動生成）
├── main.py                       # メイン処理
├── sheets_client.py              # Google Sheets連携
├── openai_client_improved.py     # OpenAI API連携（将来用）
├── setup_template_dropdown.py    # ドロップダウンリスト設定
├── test_template_reading.py      # テンプレート読み込みテスト
├── inspect_template_sheet.py     # テンプレート構造確認
└── test_sheets_access.py         # Sheets接続テスト
```

### 3. 処理フロー

```
1. kickstarterシートから未処理行を取得
   ↓
2. 各行のtemplate列を読み取り
   ↓
3. 選択されたテンプレートシートから本文を取得
   ↓
4. テンプレート内の{{URL}}と{{name}}を置換
   ↓
5. H列（jp_report）とI列（en_report）に書き込み
   ↓
6. G列（status）を「完了」に更新
```

## 🚀 使用方法

### 初回セットアップ

1. **Google Sheets API認証設定**
   ```bash
   # setup_auth_quick.mdの手順に従ってcredentials.jsonを取得
   ```

2. **.envファイルを設定**
   ```bash
   SPREADSHEET_ID=1C1NvFExNAAeUIxXAzsvnq69B50NcIbu8HfVOoRIOAH8
   SHEET_NAME=kickstarter
   ```

3. **ドロップダウンリストを設定（初回のみ）**
   ```bash
   python3 setup_template_dropdown.py
   ```

### 日常運用

1. **スプレッドシートにデータを追加**
   - B列（product_url）: Kickstarter URL
   - C列（template）: ドロップダウンからテンプレートを選択
   - D列（name）: メーカー名（任意）

2. **スクリプトを実行**
   ```bash
   python3 main.py
   ```

3. **結果を確認**
   - H列: 日本語レポート
   - I列: 英語レポート
   - G列: 「完了」ステータス

## 🔧 メンテナンス

### 新しいテンプレートの追加

1. スプレッドシートに新しいシートを作成
2. 以下の構造でテンプレートを記述：
   - A1: 英語件名
   - A2: 英語本文（`{{URL}}`と`{{name}}`のプレースホルダーを使用可能）
   - B2: 日本語本文（`{{URL}}`と`{{name}}`のプレースホルダーを使用可能）

3. `setup_template_dropdown.py`を編集してテンプレート名を追加
4. `setup_template_dropdown.py`を実行してドロップダウンリストを更新

### データ検証

```bash
# 全シート確認
python3 inspect_spreadsheet.py

# テンプレート読み込みテスト
python3 test_template_reading.py

# Sheets接続テスト
python3 test_sheets_access.py
```

## 📝 既存システムとの違い

### 旧システム（単一シート、固定列構成）
- 1つのシートにプロンプト、本文、レポートが混在
- 列数が多い（A:L列の12列構成）
- テンプレート変更時にコード修正が必要

### 新システム（複数シート、テンプレート選択）
- kickstarterシート: 一覧管理専用（A:I列の9列構成）
- テンプレートシート: 5種類のテンプレートを独立管理
- ドロップダウンリストでテンプレート選択
- テンプレート追加時もコード修正不要（ドロップダウンリスト更新のみ）

## 🔐 セキュリティ

- `credentials.json`: OAuth 2.0クライアント認証情報（ローカル保存、Git管理外）
- `token.json/token.pickle`: アクセストークン（自動生成、Git管理外）
- `.env`: 環境変数（Git管理外）

## 🎓 トラブルシューティング

### Error 403: access_denied
- OAuth同意画面にテストユーザーを追加
- Google Cloud Console → OAuth同意画面 → テストユーザー

### テンプレートが読み込めない
- `inspect_template_sheet.py`でテンプレート構造を確認
- シート名がドロップダウンリストと一致しているか確認

### 未処理行が検出されない
- B列（product_url）にURLが入力されているか確認
- H列（jp_report）が空白、または100文字未満か確認

## 📈 今後の拡張予定

- [ ] OpenAI APIを使用した動的レポート生成機能
- [ ] メール送信機能の統合
- [ ] 送信履歴管理
- [ ] レスポンス追跡機能
- [ ] GitHub Actionsによる自動実行
