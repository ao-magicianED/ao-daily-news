# あおのデイリーニュース

AI・民泊・レンタルスペースの最新ニュースを毎朝自動配信するニュースサイトです。

## 機能

- **3つのカテゴリ**: AI / 民泊 / レンタルスペース
- **毎朝自動更新**: GitHub Actionsで毎朝7時（日本時間）に自動更新
- **AIによる要約**: Gemini APIでニュースを要約・コメント生成
- **あおの一言**: 各ニュースにオーナー目線のアドバイス付き
- **アーカイブ機能**: 過去の記事を保存・閲覧可能
- **レスポンシブ対応**: スマホ・タブレット・PCに対応

## セットアップ手順

### 1. GitHubリポジトリの作成

1. GitHubで新しいリポジトリを作成
2. このプロジェクトのファイルをすべてプッシュ

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/リポジトリ名.git
git push -u origin main
```

### 2. Gemini API キーの取得（無料）

1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. Googleアカウントでログイン
3. 「Create API Key」をクリック
4. 生成されたAPIキーをコピー

### 3. GitHub Secretsの設定

1. GitHubリポジトリの「Settings」→「Secrets and variables」→「Actions」
2. 「New repository secret」をクリック
3. Name: `GEMINI_API_KEY`
4. Secret: 取得したAPIキーを貼り付け
5. 「Add secret」をクリック

### 4. GitHub Pagesの有効化

1. GitHubリポジトリの「Settings」→「Pages」
2. Source: 「Deploy from a branch」を選択
3. Branch: 「main」「/ (root)」を選択
4. 「Save」をクリック

数分後、`https://あなたのユーザー名.github.io/リポジトリ名/` でサイトが公開されます。

### 5. 初回のニュース取得（任意）

GitHub Actionsを手動実行して、すぐにニュースを取得できます：

1. リポジトリの「Actions」タブ
2. 「Daily News Update」を選択
3. 「Run workflow」→「Run workflow」をクリック

## ディレクトリ構成

```
/
├── index.html              # メインページ
├── css/
│   └── style.css           # スタイルシート
├── js/
│   └── main.js             # フロントエンドJS
├── data/
│   ├── news.json           # 最新ニュースデータ
│   └── archive/            # アーカイブ
│       ├── index.json      # アーカイブ一覧
│       └── YYYY-MM-DD.json # 日付別データ
├── scripts/
│   └── fetch_news.py       # ニュース収集スクリプト
├── .github/
│   └── workflows/
│       └── daily_news.yml  # GitHub Actions
└── README.md
```

## カスタマイズ

### RSSフィードの変更

`scripts/fetch_news.py` の `RSS_FEEDS` を編集してニュースソースを変更できます。

### デザインの変更

`css/style.css` でカラーやレイアウトをカスタマイズできます。

### 更新時間の変更

`.github/workflows/daily_news.yml` の `cron` を編集：

```yaml
# 例: 毎朝6時（日本時間）= UTC 21:00
schedule:
  - cron: '0 21 * * *'
```

## 料金について

すべて無料で運用可能です：

| サービス | 無料枠 |
|----------|--------|
| GitHub Pages | 無制限 |
| GitHub Actions | 2,000分/月 |
| Gemini API | 60リクエスト/分 |

※ 1日1回の更新なら、月間のGitHub Actions使用量は約30分程度です。

## トラブルシューティング

### ニュースが更新されない

1. GitHub Actions の実行ログを確認
2. `GEMINI_API_KEY` が正しく設定されているか確認
3. APIの無料枠を超えていないか確認

### サイトが表示されない

1. GitHub Pages が有効になっているか確認
2. ブランチが `main` になっているか確認
3. 数分待ってから再度アクセス

## ライセンス

MIT License

---

開発: あお
