# Kickstarter Market Analyzer - Claude Code 設定

## 重要：Git プッシュルール

**コミット後は必ず両方のリポジトリにプッシュすること！**

```bash
git push origin main && git push client main
```

| リモート名 | リポジトリ | 用途 |
|-----------|-----------|------|
| origin | RyoUmeyama/kickstarter-market-analyzer | バックアップ |
| client | koki4117/kickstarter-market-analyzer | **本番（GitHub Actions実行）** |

**絶対に `client` へのプッシュを忘れないこと。GitHub Actionsはkoki4117リポジトリで実行される。**

## GitHub Secrets（koki4117リポジトリ）

以下のSecretsが設定済み：
- SPREADSHEET_ID
- OPENAI_API_KEY
- GOOGLE_CREDENTIALS_JSON
- BRIGHT_DATA_USERNAME
- BRIGHT_DATA_PASSWORD
- PAT_TOKEN

## データ取得の優先順位

1. 直接接続（Playwright）- 無料
2. Kicktraq - 無料
3. Bright Data プロキシ - 有料（最後の手段）

## 重要な注意事項

- Kickstarterの数値を捏造しない
- データ取得失敗時は「データ取得失敗」として正直に報告
- AIに例として具体的な金額を提示しない（コピーされる危険性）
