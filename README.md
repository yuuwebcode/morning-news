# morning-news

毎朝、国内・世界のニュース見出しを1ページで確認できる静的サイト。

- `build.py` が各社 RSS を取得して `index.html` を生成
- GitHub Actions が毎朝 6:00 JST に実行し Pages を更新
- 公開URL: `https://<ユーザー名>.github.io/morning-news/`

## ローカル実行

    python3 build.py

生成された `index.html` をブラウザで開いて確認する。

## テスト

    python3 -m unittest discover -s tests -v

## ソースの追加・削除

`build.py` の `SOURCES` リストを編集する（セクション名・ソース名・RSS URL の3要素）。
