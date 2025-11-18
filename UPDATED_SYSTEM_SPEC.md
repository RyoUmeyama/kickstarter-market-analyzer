# 更新後のシステム仕様

## 📋 テンプレートシート構造（確定版）

### 構成

| 行 | A列 | B列 |
|----|-----|-----|
| 1 | 英語件名 | 日本語件名（`=GOOGLETRANSLATE(A1, "en", "ja")`） |
| 2 | 英語本文 | 日本語本文（`=GOOGLETRANSLATE(A2, "en", "ja")`） |
| 3 | プロンプト（日本語、任意） | （空） |

### プレースホルダー

- `{{URL}}`: Kickstarter URLに置換
- `{{name}}`: メーカー名に置換

## 🔄 処理フロー

### パターン1: プロンプトなし（A3が空）

1. テンプレートシートから読み取り：
   - A1（英語件名）→ kickstarterシートのG列
   - B1（日本語件名、GOOGLETRANSLATE関数の結果）→ kickstarterシートのF列
   - A2（英語本文）→ kickstarterシートのJ列
   - B2（日本語本文、GOOGLETRANSLATE関数の結果）→ kickstarterシートのI列

2. プレースホルダー（`{{URL}}`、`{{name}}`）を置換

3. kickstarterシートに書き込み

### パターン2: プロンプトあり（A3に値がある）

1. テンプレートシートから読み取り：
   - A1（英語件名）→ kickstarterシートのG列
   - B1（日本語件名、GOOGLETRANSLATE関数の結果）→ kickstarterシートのF列
   - A3（プロンプト、日本語）

2. プロンプトのプレースホルダー（`{{URL}}`、`{{name}}`）を置換

3. **OpenAI APIを呼び出し**：
   - システムメッセージ: "You are a professional business consultant. The user will provide a prompt in Japanese. Please respond in English with a detailed business report."
   - ユーザーメッセージ: A3のプロンプト（日本語、プレースホルダー置換済み）
   - レスポンス: **英語**でレポートを生成

4. kickstarterシートに書き込み：
   - G列: 英語件名（A1）
   - F列: 日本語件名（B1、GOOGLETRANSLATE関数の結果）
   - J列: 英語レポート（OpenAI APIの結果）
   - I列: **空文字列**（後でGOOGLETRANSLATE関数を手動設定）

## 📊 kickstarterシート構造

| 列 | 列名 | 説明 | 値の入り方 |
|----|------|------|-----------|
| A | NO | 番号 | 手動入力 |
| B | product_url | Kickstarter URL | 手動入力 |
| C | template | テンプレート名 | ドロップダウンから選択 |
| D | name | メーカー名 | 手動入力 |
| E | to_email | 送信先メールアドレス | 手動入力 |
| F | jp_subject | 日本語件名 | 自動生成（テンプレートのB1） |
| G | en_subject | 英語件名 | 自動生成（テンプレートのA1） |
| H | status | ステータス | 自動生成（「完了」） |
| I | jp_report | 日本語本文 | 自動生成 or 空（後で関数設定） |
| J | en_report | 英語本文 | 自動生成 |

### I列（jp_report）の設定

**プロンプトなしの場合:**
- main.pyが日本語本文を自動書き込み（テンプレートのB2）

**プロンプトありの場合:**
- main.pyは空文字列を書き込み
- **手動でGOOGLETRANSLATE関数を設定する必要あり**:
  ```
  =IF(J2="", "", GOOGLETRANSLATE(J2, "en", "ja"))
  ```

## 🎯 使用例

### 例1: プロンプトなし（固定文テンプレート）

**テンプレートシート「①1回目送信文」:**
```
A1: Proposal for Japan Market Collaboration
B1: =GOOGLETRANSLATE(A1, "en", "ja")  → 「日本市場における協業の提案」

A2: Dear {{name}} Sales Team, ...（固定文）
B2: =GOOGLETRANSLATE(A2, "en", "ja")  → 「{{name}} 営業チーム様、...」

A3: （空）
```

**結果:**
- F列: 日本市場における協業の提案
- G列: Proposal for Japan Market Collaboration
- I列: {{name}} 営業チーム様、...（プレースホルダー置換済み）
- J列: Dear {{name}} Sales Team, ...（プレースホルダー置換済み）

### 例2: プロンプトあり（AI生成テンプレート）

**テンプレートシート「⑥AI分析レポート」（例）:**
```
A1: Japan Market Analysis Report for {{name}}
B1: =GOOGLETRANSLATE(A1, "en", "ja")  → 「{{name}}の日本市場分析レポート」

A2: （使用しない、または空）
B2: =GOOGLETRANSLATE(A2, "en", "ja")

A3: 以下のKickstarter製品について、日本市場参入の詳細な分析レポートを英語で作成してください。

製品URL: {{URL}}
メーカー名: {{name}}

分析内容:
1. 日本市場におけるクラウドファンディングの成功可能性
2. 競合製品の分析（具体的な製品名とURLを含む）
3. 推奨販売チャネル（Makuake、Amazon Japanなど）
4. 予想収益予測
5. リスク分析

全て英語で詳細に記述してください。
```

**結果:**
- F列: WashWowの日本市場分析レポート（プレースホルダー置換済み）
- G列: Japan Market Analysis Report for WashWow（プレースホルダー置換済み）
- I列: **空文字列** → 手動で`=GOOGLETRANSLATE(J2, "en", "ja")`を設定
- J列: OpenAI APIが生成した英語レポート（詳細な市場分析）

## ⚙️ 設定手順

### I列にGOOGLETRANSLATE関数を設定する方法

プロンプトありのテンプレートを使用する場合、最初の1行のみ手動で設定すれば、後はオートフィル（下方向にコピー）できます。

1. kickstarterシートのI2セルに以下の関数を入力:
   ```
   =IF(J2="", "", GOOGLETRANSLATE(J2, "en", "ja"))
   ```

2. I2セルの右下の小さな四角（フィルハンドル）をダブルクリック
   → 下方向に自動コピーされます

3. main.pyを実行
   → J列に英語レポートが書き込まれる
   → I列のGOOGLETRANSLATE関数が自動的に日本語に翻訳

## 📝 メールマージでの使用

### CSV出力時の注意点

GOOGLETRANSLATE関数の結果をCSVで出力すると、関数ではなく値がエクスポートされます。

1. Google Sheets → ファイル → ダウンロード → カンマ区切り形式（.csv）
2. Thunderbirdのメールマージで読み込み
3. 送信先: `{{to_email}}`
4. 件名: `{{jp_subject}}` または `{{en_subject}}`
5. 本文: `{{jp_report}}` または `{{en_report}}`

## 🚀 今後の改善案

### オプション1: スクリプト側でGOOGLETRANSLATE関数を自動設定

`sheets_client.py`の`write_report()`メソッドを修正して、jp_bodyが空文字列の場合にGOOGLETRANSLATE関数を書き込む。

```python
if japanese_report == '':
    # 関数を書き込み
    formula = f'=IF(J{row_number}="", "", GOOGLETRANSLATE(J{row_number}, "en", "ja"))'
    self._update_cell(row_number, 9, formula)
else:
    # 値を書き込み
    self._update_cell(row_number, 9, japanese_report)
```

### オプション2: Python側でGoogle Translateを使用

`googletrans`ライブラリを使用して、Python側で翻訳してから書き込む。

```python
from googletrans import Translator

translator = Translator()
jp_body = translator.translate(en_body, src='en', dest='ja').text
```

## 🎓 どちらを選ぶべきか？

| | 手動設定 | スクリプト自動設定 | Python翻訳 |
|---|---|---|---|
| **設定の手間** | 初回のみ手動 | 不要 | 不要 |
| **翻訳の品質** | Google公式 | Google公式 | Google非公式API |
| **リアルタイム性** | ◎ | ◎ | △ |
| **依存関係** | なし | なし | googletransライブラリ |
| **推奨度** | ⭐⭐⭐ | ⭐⭐ | ⭐ |

**推奨**: 手動設定（オプション1）
- 一度設定すれば全行に適用可能
- Google Sheets標準機能なので安定
- リアルタイムで翻訳が更新される
