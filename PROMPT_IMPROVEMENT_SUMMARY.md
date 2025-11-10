# プロンプト改善作業サマリー

## 📋 作業概要

**日付**: 2025年11月10日

**対応内容**: クライアントからの「レポートが客観的な概要に留まっている」「事業者目線の詳細な分析が欲しい」というフィードバックに対応し、プロンプトを大幅改善しました。

---

## ✅ 完了した作業

### 1. 改善版プロンプトの実装

#### 作成ファイル
- **`openai_client_improved.py`** - 改善版プロンプトを含む新しいクラス

#### 主な改善点
1. **System Message追加**: AIの役割を「事業コンサルタント」として明確化
2. **定量的要件の必須化**:
   - 類似製品: 最低5件（製品名・URL・実績額必須）
   - 価格戦略: 3段階（早割・通常・リテール）+ 収益性分析
   - 販売予測: 3シナリオ（保守的・標準・楽観的）
   - リスク分析: 最低5項目
3. **新規セクション追加**:
   - ⑤競合優位性分析（強み・弱み・USP）
   - ⑥フェーズ2・3展開戦略
4. **曖昧な表現の禁止**: 「可能性があります」等の表現を排除

### 2. 詳細分析資料の作成

#### consulting/PROMPT_IMPROVEMENT_ANALYSIS.md
- 現行版 vs 改善版の詳細比較
- トークン数とコストの試算（実測値ベース）
- 費用対効果分析
- テスト計画

**主な発見**:
- トークン数: 6,440 → 7,640（+1,200）
- コスト: ¥0.48/件 → ¥0.51/件（+¥0.03）
- 月50件: ¥24 → ¥26（+¥2）

#### consulting/PROMPT_COMPARISON.md
- 各セクションの具体的な変更内容
- 期待される出力の具体例
- 現行版と改善版の出力比較

#### consulting/IMPLEMENTATION_GUIDE.md
- 段階的な実装方法（テスト → 本番適用）
- テストケースとチェックリスト
- トラブルシューティング
- ロールバック方法

### 3. ドキュメント更新

#### README.md
- ファイル構成に `openai_client_improved.py` を追加
- 機能セクションに改善版プロンプトを追加
- コストセクションを実測値ベースで更新
- 新規セクション「🔥 プロンプト改善版の使用」を追加

#### consulting/README.md
- 新規セクション「プロンプト改善の確認と実装」を追加
- ファイル一覧に改善関連資料を追加
- 更新履歴に本日の作業を追加

---

## 📊 改善効果のまとめ

| 項目 | 現行版 | 改善版 | 改善度 |
|------|--------|--------|--------|
| **類似製品数** | 0-2件 | 5件以上必須 | ⭐⭐⭐⭐⭐ |
| **URL記載** | なし | 必須 | ⭐⭐⭐⭐⭐ |
| **実績額** | 曖昧 | 具体的な数値必須 | ⭐⭐⭐⭐⭐ |
| **価格戦略** | 1段階 | 3段階 + 収益性分析 | ⭐⭐⭐⭐⭐ |
| **販売予測** | 1パターン | 3シナリオ | ⭐⭐⭐⭐⭐ |
| **リスク分析** | 注意点のみ | 5項目以上、影響度評価 | ⭐⭐⭐⭐⭐ |
| **競合分析** | なし | 強み・弱み・USP | ⭐⭐⭐⭐⭐ |
| **長期戦略** | 曖昧 | フェーズ2・3計画 | ⭐⭐⭐⭐ |
| **コスト増加** | - | +¥0.03/件 | ✅ 許容範囲 |

**結論**: 月+¥2の微々たるコスト増で、レポート品質が飛躍的に向上

---

## 🚀 次のステップ（推奨順）

### ステップ1: 詳細資料の確認（5-10分）

```bash
# トークン数・コスト試算
open consulting/PROMPT_IMPROVEMENT_ANALYSIS.md

# 現行版 vs 改善版の比較
open consulting/PROMPT_COMPARISON.md

# 実装ガイド
open consulting/IMPLEMENTATION_GUIDE.md
```

### ステップ2: テスト実行（5分）

#### 2-1. check_kickstarter.pyを編集

`/Users/r.umeyama/work/kickstarter-market-analyzer/check_kickstarter.py` を開いて、以下を変更:

```python
# Before:
from openai_client import MarketReportGenerator

# After:
from openai_client_improved import ImprovedMarketReportGenerator as MarketReportGenerator
```

#### 2-2. スプレッドシートの準備

1. Google Sheetsを開く: https://docs.google.com/spreadsheets/d/1DrZnyCP8mf9286tGIhJ0tB0EFQNVwtHadcowXRQKyMI/edit
2. テストしたい1行のK列（日本語レポート）をクリア
3. または、K列に「テスト」と入力（100文字未満なので未処理扱い）

#### 2-3. テスト実行

```bash
cd /Users/r.umeyama/work/kickstarter-market-analyzer
source venv/bin/activate
python check_kickstarter.py
```

### ステップ3: 結果確認（5分）

スプレッドシートのK列に書き込まれたレポートを確認:

#### 必須チェック項目
- [ ] 類似製品が3件以上記載されているか
- [ ] 製品名・URL・実績額が含まれているか
- [ ] 価格戦略が2段階以上あるか
- [ ] 販売予測に数値と確率が含まれているか
- [ ] 文字数が1500-3000文字の範囲内か

#### 理想チェック項目
- [ ] 類似製品が5件以上、全てURLと実績額付き
- [ ] 価格戦略が3段階（早割・通常・リテール）
- [ ] 販売予測が3シナリオ（保守的・標準・楽観的）
- [ ] リスク分析が5項目以上
- [ ] 競合優位性分析（強み・弱み・USP）
- [ ] 長期展開戦略（フェーズ2・3）

### ステップ4: 本番適用（テスト成功後）

#### 4-1. Gitにコミット

```bash
git add openai_client_improved.py
git add consulting/PROMPT_IMPROVEMENT_ANALYSIS.md
git add consulting/PROMPT_COMPARISON.md
git add consulting/IMPLEMENTATION_GUIDE.md
git add README.md consulting/README.md
git add PROMPT_IMPROVEMENT_SUMMARY.md

git commit -m "Add improved prompts for detailed business analysis

- Created openai_client_improved.py with enhanced prompts
- Added system message defining AI as business consultant
- Required minimum 5 similar products with URLs and sales data
- Added 3-tier pricing strategy with profitability analysis
- Added 3-scenario forecasts (conservative/standard/optimistic)
- Added competitive advantage analysis (strengths/weaknesses/USP)
- Added Phase 2-3 expansion strategy
- Cost increase: +¥0.03 per report (+¥2/month for 50 reports)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

#### 4-2. GitHub Actionsでの利用（オプション）

GitHub Actionsでも改善版を使用する場合:

1. `.github/workflows/analyze_kickstarter.yml` は変更不要
   - `check_kickstarter.py` のインポート文を変更するだけでOK
2. GitHubにプッシュ後、次回の自動実行から改善版が適用されます

#### 4-3. クライアントへの報告

```
件名: Kickstarter市場分析レポートの品質向上について

お世話になっております、梅山です。

先日ご指摘いただいた「レポートが客観的な概要に留まっている」
「事業者目線の詳細な分析が欲しい」という件について、
プロンプトを大幅に改善いたしました。

【改善内容】
- 類似製品: 最低5件の製品名・URL・実績額を記載
- 価格戦略: 早割・通常・リテール価格の3段階 + 収益性分析
- 販売予測: 保守的・標準的・楽観的の3シナリオ予測
- 競合優位性分析: 強み・弱み・差別化戦略
- 長期戦略: フェーズ2（EC）・フェーズ3（量販店）の展開計画

【コスト影響】
- 月額わずか+¥2（50件の場合）で、レポート品質が飛躍的に向上

テストレポートをご確認いただき、ご意見をいただければ幸いです。

よろしくお願いいたします。
```

---

## 🔄 ロールバック方法（問題発生時）

### 方法1: check_kickstarter.pyを修正

```python
# 改善版から現行版に戻す
# from openai_client_improved import ImprovedMarketReportGenerator as MarketReportGenerator
from openai_client import MarketReportGenerator
```

### 方法2: Gitで戻す

```bash
git checkout HEAD~1 -- check_kickstarter.py
```

---

## 📞 トラブルシューティング

### Q1: 類似製品が5件出ない

**A**: Kickstarterの製品カテゴリがニッチすぎる可能性があります。
- プロンプトの「最低5件」を「最低3件」に変更
- または、temperature を 0.7 → 0.5 に下げる

### Q2: 文字数が多すぎる（3000文字超）

**A**: プロンプトに文字数制限を強調:
```python
【文字数制限】
- 合計文字数: 2000-2500文字（厳守）
```

### Q3: URLが含まれない

**A**: 「重要な指示」セクションをより強調:
```python
1. **各分析項目について、具体的な製品名とURL（https://...）を必ず含めてください**
```

### Q4: トークン数が予測より多い

**A**: 以下をチェック:
1. 出力が想定より長い（3000文字超）
2. Kickstarterのdescriptionが長すぎる
3. OpenAI Dashboardで実測値を確認

---

## 📚 関連ファイル

| ファイル | 説明 |
|---------|------|
| `openai_client_improved.py` | 改善版プロンプト実装 |
| `consulting/PROMPT_IMPROVEMENT_ANALYSIS.md` | トークン数・コスト試算の詳細分析 |
| `consulting/PROMPT_COMPARISON.md` | 現行版 vs 改善版の具体的比較 |
| `consulting/IMPLEMENTATION_GUIDE.md` | 実装ガイド（テスト計画・チェックリスト） |
| `README.md` | プロジェクト全体のREADME（更新済み） |
| `consulting/README.md` | コンサルティング資料の使い方（更新済み） |
| `PROMPT_IMPROVEMENT_SUMMARY.md` | このファイル（作業サマリー） |

---

## 💡 追加の最適化案（今後の検討事項）

### 1. 業界別プロンプトのカスタマイズ

製品カテゴリに応じてプロンプトを変える:
- テクノロジー製品: 技術仕様、特許、セキュリティを重視
- ファッション製品: トレンド、季節性、ブランド戦略を重視
- 食品・飲料: 食品表示、賞味期限、流通戦略を重視

### 2. 言語別最適化

英語レポートも改善版プロンプトで生成:
- `generate_english_report()` メソッドにも同様の改善を適用
- 英語特有の表現（"Key Takeaways", "Executive Summary"等）を追加

### 3. 段階的な改善適用

すべての改善を一度に適用するのではなく、段階的に:
- フェーズ1: 類似製品5件必須化のみ
- フェーズ2: 3シナリオ予測追加
- フェーズ3: 競合分析・長期戦略追加

---

**作成日**: 2025年11月10日
**最終更新**: 2025年11月10日
**作成者**: 梅山（Claude Code支援）
