# Kickstarter Market Analyzer - スプレッドシート構造

## 📊 実際のスプレッドシート構成

スプレッドシートID: `1DrZnyCP8mf9286tGIhJ0tB0EFQNVwtHadcowXRQKyMI`

### 列構成（A〜L列）

| 列 | ヘッダー名 | 用途 | 入力方法 | 備考 |
|----|-----------|------|---------|------|
| A | NO | 番号 | 手動 | 1, 2, 3... |
| B | product_url | Kickstarter URL | 手動 | 必須 |
| C | product_name | 商品名 | 手動（任意） | 空欄可（自動取得） |
| D | name | 名前 | 手動（任意） | メーカー担当者名など |
| E | to_email | 送信先メール | 手動（任意） | メール送信機能用 |
| F | subject | メール件名 | 手動（任意） | メール送信機能用 |
| G | jp_email | 日本語メール本文 | 手動（任意） | メール送信機能用 |
| H | en_email | 英語メール本文 | 手動（任意） | メール送信機能用 |
| I | status | ステータス | 手動（任意） | "done"などの管理用 |
| J | （空欄） | 英語マーケットブリーフ | 手動（任意） | 既存データ保持用 |
| K | （空欄） | **日本語レポート** | **自動生成** | **ChatGPT生成** ⭐ |
| L | （空欄） | **英語レポート** | **自動生成** | **ChatGPT生成** ⭐ |

### 未処理行の判定ロジック

以下の条件を**両方満たす**行が自動処理対象になります：

1. **B列（product_url）にKickstarter URLが入っている**
2. **K列（日本語レポート）が空、または100文字未満**

```python
# sheets_client.py の実装
if url and (not japanese_report or len(japanese_report.strip()) < 100):
    # この行を処理対象とする
```

### 現在のデータ状況

- 総データ行数: 3行（ヘッダー除く）
- URLが入っている行: 2行
- K列に既にレポートがある行: 2行（どちらも2000文字以上）
- **未処理行: 0行**（すべてレポート生成済み）

### F〜J列の役割

F〜J列は既存のメール送信システムで使用されている列です：

- **F列**: メール件名（subject）
- **G列**: 日本語メール本文（jp_email）
- **H列**: 英語メール本文（en_email）
- **I列**: ステータス（status）- "done"などの管理用フラグ
- **J列**: 英語版マーケットブリーフ（手動入力）

これらの列は**ChatGPT自動生成機能では使用しません**が、既存データとして保持されます。

### K列・L列（新規追加）

K列とL列は、今回のChatGPT自動生成機能で**新たに追加された列**です：

- **K列**: ChatGPTが生成する日本語の市場分析レポート
- **L列**: ChatGPTが生成する英語の市場分析レポート

既存のF〜J列のデータを保持したまま、別の列にレポートを出力することで、
既存のワークフローとの共存を実現しています。

## 🔧 実装との対応

### コード内での列番号

```python
# sheets_client.py

# 読み取り範囲
range=f'{self.sheet_name}!A:L'  # A列からL列まで

# レポート書き込み
self._update_cell(row_number, 11, japanese_report)  # K列（11列目）
self._update_cell(row_number, 12, english_report)   # L列（12列目）

# 未処理行判定
japanese_report = row[10] if len(row) > 10 else ''  # K列（インデックス10）
```

### 列インデックスの対応表

| 列 | 列名 | 列番号 | Pythonインデックス |
|----|-----|-------|------------------|
| A | NO | 1 | 0 |
| B | product_url | 2 | 1 |
| C | product_name | 3 | 2 |
| D | name | 4 | 3 |
| E | to_email | 5 | 4 |
| F | subject | 6 | 5 |
| G | jp_email | 7 | 6 |
| H | en_email | 8 | 7 |
| I | status | 9 | 8 |
| J | (empty) | 10 | 9 |
| K | (japanese_report) | 11 | 10 |
| L | (english_report) | 12 | 11 |

## 📝 まとめ

このスプレッドシートは：

1. **既存のメール送信システム**（F〜I列）と
2. **新しいChatGPT自動レポート生成システム**（K〜L列）

の両方を1つのスプレッドシートで管理する設計になっています。

K列とL列に出力することで、既存データを保護しながら新機能を追加できています。
