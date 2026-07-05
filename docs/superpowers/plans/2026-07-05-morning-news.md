# morning-news Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 毎朝 GitHub Actions が各社 RSS を取得して単一の静的 `index.html` を生成し、GitHub Pages で公開する。スマホのブラウザから URL を開くだけで国内・世界のニュース見出しを確認できる。

**Architecture:** Python 標準ライブラリのみで書いた `build.py` が、ソース定義に従い RSS を取得 → パース → HTML を生成する。パース・時刻整形・HTML生成の純粋関数はユニットテスト可能に分離し、ネットワーク取得層と分ける。GitHub Actions が毎朝 6:00 JST に実行し、差分があれば commit & push。Pages が main ブランチのルートから配信する。

**Tech Stack:** Python 3.9（標準ライブラリのみ: `urllib.request`, `xml.etree.ElementTree`, `email.utils`, `datetime`, `html`）、GitHub Actions、GitHub Pages。pip 依存なし。

**検証済みソース（2026-07-05 時点で全て HTTP 200・item 取得可）:**
- 国内 総合: NHK主要 `https://www.nhk.or.jp/rss/news/cat0.xml`（301→リダイレクト追従で200）、Yahoo top-picks `https://news.yahoo.co.jp/rss/topics/top-picks.xml`
- 世界: NHK国際 `https://www.nhk.or.jp/rss/news/cat6.xml`、BBC News Japan `https://feeds.bbci.co.uk/japanese/rss.xml`
- 経済・ビジネス: NHK経済 `https://www.nhk.or.jp/rss/news/cat5.xml`、Yahoo経済 `https://news.yahoo.co.jp/rss/topics/business.xml`
- テクノロジー・IT: ITmedia `https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml`、Yahoo IT `https://news.yahoo.co.jp/rss/topics/it.xml`、はてブ テク `https://b.hatena.ne.jp/hotentry/it.rss`
- スポーツ・エンタメ: Yahooスポーツ `https://news.yahoo.co.jp/rss/topics/sports.xml`、Yahooエンタメ `https://news.yahoo.co.jp/rss/topics/entertainment.xml`

**日付形式（実測）:** RSS2.0 系（NHK/Yahoo/BBC/ITmedia）は `<pubDate>` の RFC822（例 `Sun, 05 Jul 2026 20:54:29 +0900` / `... GMT`）。RDF系（はてブ）は `<dc:date>` の ISO8601（例 `2026-07-01T04:15:32Z`）。パーサは両対応する。すべての item は `<item>/<title>/<link>` を持つ。

**Python 3.9 制約:** ローカル Mac の Python は 3.9.6 のみ（`X | None` 記法不可）。型注釈を使う場合はファイル冒頭に `from __future__ import annotations` を置く。Actions も `python-version: '3.9'` を指定する。

---

### Task 1: プロジェクト初期化

**Files:**
- Create: `~/cc/morning-news/.gitignore`
- Create: `~/cc/morning-news/README.md`

- [ ] **Step 1: `.gitignore` を作成**

```
__pycache__/
*.pyc
.DS_Store
/tmp/
```

- [ ] **Step 2: `README.md` を作成**

```markdown
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
```

- [ ] **Step 3: コミット**

```bash
cd ~/cc/morning-news
git add .gitignore README.md
git commit -m "chore: プロジェクト初期化"
```

---

### Task 2: フィードのパース（純粋関数 + ユニットテスト）

RSS2.0 と RDF/RSS1.0 の両方の XML 文字列から記事リストを抽出する純粋関数を作る。ネットワークは触らない。

**Files:**
- Create: `~/cc/morning-news/build.py`
- Create: `~/cc/morning-news/tests/test_parse.py`
- Create: `~/cc/morning-news/tests/__init__.py`（空ファイル）

- [ ] **Step 1: 失敗するテストを書く**

`tests/__init__.py` は空で作成。`tests/test_parse.py`:

```python
import unittest
from datetime import datetime, timezone
from build import parse_feed, Article


RSS2 = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
  <item>
    <title>速報タイトルA</title>
    <link>https://example.com/a</link>
    <pubDate>Sun, 05 Jul 2026 20:54:29 +0900</pubDate>
  </item>
  <item>
    <title>タイトルB &amp; 記号</title>
    <link>https://example.com/b</link>
    <pubDate>Sun, 05 Jul 2026 14:17:49 GMT</pubDate>
  </item>
</channel></rss>"""

RDF = """<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <item>
    <title>はてなタイトル</title>
    <link>https://example.com/hatena</link>
    <dc:date>2026-07-01T04:15:32Z</dc:date>
  </item>
</rdf:RDF>"""


class TestParseFeed(unittest.TestCase):
    def test_rss2_extracts_articles(self):
        arts = parse_feed(RSS2, source_name="テスト源")
        self.assertEqual(len(arts), 2)
        self.assertEqual(arts[0].title, "速報タイトルA")
        self.assertEqual(arts[0].link, "https://example.com/a")
        self.assertEqual(arts[0].source_name, "テスト源")

    def test_rss2_parses_rfc822_date(self):
        arts = parse_feed(RSS2, source_name="テスト源")
        # +0900 の 20:54:29 は UTC 11:54:29
        self.assertEqual(
            arts[0].published.astimezone(timezone.utc),
            datetime(2026, 7, 5, 11, 54, 29, tzinfo=timezone.utc),
        )

    def test_rss2_unescapes_entities(self):
        arts = parse_feed(RSS2, source_name="テスト源")
        self.assertEqual(arts[1].title, "タイトルB & 記号")

    def test_rdf_extracts_and_parses_iso_date(self):
        arts = parse_feed(RDF, source_name="はてブ")
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0].title, "はてなタイトル")
        self.assertEqual(
            arts[0].published.astimezone(timezone.utc),
            datetime(2026, 7, 1, 4, 15, 32, tzinfo=timezone.utc),
        )

    def test_missing_date_yields_none_published(self):
        xml = RSS2.replace(
            "<pubDate>Sun, 05 Jul 2026 20:54:29 +0900</pubDate>", ""
        )
        arts = parse_feed(xml, source_name="テスト源")
        self.assertIsNone(arts[0].published)

    def test_malformed_xml_returns_empty(self):
        arts = parse_feed("<not-xml", source_name="X")
        self.assertEqual(arts, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd ~/cc/morning-news && python3 -m unittest tests.test_parse -v`
Expected: FAIL（`ImportError: cannot import name 'parse_feed' from 'build'`）

- [ ] **Step 3: 最小実装を書く**

`build.py`（このタスクの範囲のみ。後続タスクで追記する）:

```python
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional


@dataclass
class Article:
    title: str
    link: str
    source_name: str
    published: Optional[datetime]


def _localname(tag: str) -> str:
    """'{namespace}tag' -> 'tag'。名前空間を除いたローカル名を返す。"""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_child_text(item: ET.Element, name: str) -> Optional[str]:
    for child in item:
        if _localname(child.tag) == name:
            return child.text.strip() if child.text else ""
    return None


def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    # RFC822 (pubDate)
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (TypeError, ValueError):
        pass
    # ISO8601 (dc:date)。Python 3.9 は 'Z' を解釈できないので置換する。
    try:
        iso = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def parse_feed(xml_text: str, source_name: str) -> List[Article]:
    """RSS2.0 / RDF(RSS1.0) の XML 文字列から Article のリストを返す。
    パース不能なら空リストを返す（呼び出し側で握りつぶさない）。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    articles: List[Article] = []
    for elem in root.iter():
        if _localname(elem.tag) != "item":
            continue
        title = _find_child_text(elem, "title") or ""
        link = _find_child_text(elem, "link") or ""
        date_raw = _find_child_text(elem, "pubDate")
        if date_raw is None:
            date_raw = _find_child_text(elem, "date")  # dc:date
        if not title or not link:
            continue
        articles.append(
            Article(
                title=title,
                link=link,
                source_name=source_name,
                published=_parse_date(date_raw),
            )
        )
    return articles
```

注: `ET.fromstring` は XML の実体参照（`&amp;` 等）を自動でアンエスケープするため、`test_rss2_unescapes_entities` は追加処理なしで通る。

- [ ] **Step 4: テストが通ることを確認**

Run: `cd ~/cc/morning-news && python3 -m unittest tests.test_parse -v`
Expected: PASS（6 tests OK）

- [ ] **Step 5: コミット**

```bash
cd ~/cc/morning-news
git add build.py tests/__init__.py tests/test_parse.py
git commit -m "feat: RSS2.0/RDF 両対応のフィードパーサを追加"
```

---

### Task 3: 相対時刻の整形（純粋関数 + ユニットテスト）

「○分前 / ○時間前 / ○日前」の文字列を作る純粋関数。基準時刻を引数で受け取りテスト可能にする。

**Files:**
- Modify: `~/cc/morning-news/build.py`（関数追記）
- Create: `~/cc/morning-news/tests/test_reltime.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_reltime.py`:

```python
import unittest
from datetime import datetime, timedelta, timezone
from build import format_relative


NOW = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)


class TestFormatRelative(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(format_relative(None, NOW), "")

    def test_just_now(self):
        self.assertEqual(format_relative(NOW - timedelta(seconds=30), NOW), "たった今")

    def test_minutes(self):
        self.assertEqual(format_relative(NOW - timedelta(minutes=5), NOW), "5分前")

    def test_hours(self):
        self.assertEqual(format_relative(NOW - timedelta(hours=3), NOW), "3時間前")

    def test_days(self):
        self.assertEqual(format_relative(NOW - timedelta(days=2), NOW), "2日前")

    def test_future_clamped_to_just_now(self):
        self.assertEqual(format_relative(NOW + timedelta(minutes=5), NOW), "たった今")
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd ~/cc/morning-news && python3 -m unittest tests.test_reltime -v`
Expected: FAIL（`cannot import name 'format_relative'`）

- [ ] **Step 3: 最小実装を書く（build.py の import 群の直後、Article 定義付近に追記）**

```python
def format_relative(published: Optional[datetime], now: datetime) -> str:
    """published から now までの経過を日本語の相対表現で返す。"""
    if published is None:
        return ""
    delta = now - published
    secs = delta.total_seconds()
    if secs < 60:
        return "たった今"
    mins = int(secs // 60)
    if mins < 60:
        return f"{mins}分前"
    hours = mins // 60
    if hours < 24:
        return f"{hours}時間前"
    days = hours // 24
    return f"{days}日前"
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd ~/cc/morning-news && python3 -m unittest tests.test_reltime -v`
Expected: PASS（6 tests OK）

- [ ] **Step 5: コミット**

```bash
cd ~/cc/morning-news
git add build.py tests/test_reltime.py
git commit -m "feat: 相対時刻フォーマッタを追加"
```

---

### Task 4: HTML レンダリング（純粋関数 + ユニットテスト）

セクション（見出し＋記事リスト）のデータ構造から完全な HTML 文字列を生成する純粋関数。ネットワーク非依存。

**Files:**
- Modify: `~/cc/morning-news/build.py`（関数・データ構造追記）
- Create: `~/cc/morning-news/tests/test_render.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_render.py`:

```python
import unittest
from datetime import datetime, timezone
from build import Article, Section, render_html


class TestRenderHtml(unittest.TestCase):
    def _sections(self):
        art = Article(
            title="テスト<見出し>",
            link="https://example.com/a?x=1&y=2",
            source_name="NHK",
            published=datetime(2026, 7, 5, 11, 0, 0, tzinfo=timezone.utc),
        )
        return [Section(name="国内 総合", articles=[art], failed_sources=[])]

    def test_contains_doctype_and_viewport(self):
        now = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)
        html_out = render_html(self._sections(), now)
        self.assertIn("<!DOCTYPE html>", html_out)
        self.assertIn('name="viewport"', html_out)

    def test_escapes_title_and_url(self):
        now = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)
        html_out = render_html(self._sections(), now)
        self.assertIn("テスト&lt;見出し&gt;", html_out)
        self.assertIn("x=1&amp;y=2", html_out)
        self.assertNotIn("<見出し>", html_out)

    def test_shows_section_name_and_relative_time(self):
        now = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)
        html_out = render_html(self._sections(), now)
        self.assertIn("国内 総合", html_out)
        self.assertIn("1時間前", html_out)

    def test_shows_failed_source_notice(self):
        now = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)
        secs = [Section(name="世界", articles=[], failed_sources=["BBC"])]
        html_out = render_html(secs, now)
        self.assertIn("取得失敗", html_out)
        self.assertIn("BBC", html_out)

    def test_links_open_in_new_tab(self):
        now = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)
        html_out = render_html(self._sections(), now)
        self.assertIn('target="_blank"', html_out)
        self.assertIn('rel="noopener"', html_out)
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd ~/cc/morning-news && python3 -m unittest tests.test_render -v`
Expected: FAIL（`cannot import name 'Section'`）

- [ ] **Step 3: 最小実装を書く（build.py に追記）**

`import html as html_lib` をファイル冒頭の import 群に追加。`from dataclasses import dataclass, field` に変更（`field` を使う）。以下を追記:

```python
@dataclass
class Section:
    name: str
    articles: List[Article]
    failed_sources: List[str] = field(default_factory=list)


def _slugify(name: str) -> str:
    """セクション名からアンカー用 id を作る（日本語はインデックス側で連番付与するため簡易でよい）。"""
    return "sec-" + str(abs(hash(name)) % 100000)


PAGE_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", sans-serif;
       line-height: 1.5; background: #fafafa; color: #1a1a1a; }
header { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #ddd;
         padding: 12px 16px; z-index: 10; }
header h1 { margin: 0; font-size: 18px; }
.updated { color: #888; font-size: 12px; margin-top: 2px; }
nav { display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 16px; background: #fff;
      border-bottom: 1px solid #eee; position: sticky; top: 52px; z-index: 9; }
nav a { font-size: 13px; text-decoration: none; color: #0645ad; background: #eef; padding: 4px 10px;
        border-radius: 12px; }
main { padding: 0 16px 40px; max-width: 720px; margin: 0 auto; }
section { margin-top: 24px; }
section h2 { font-size: 16px; border-left: 4px solid #0645ad; padding-left: 8px; margin-bottom: 8px; }
ul { list-style: none; padding: 0; margin: 0; }
li { padding: 10px 0; border-bottom: 1px solid #eee; }
li a { text-decoration: none; color: #1a1a1a; font-size: 15px; }
li a:active { color: #0645ad; }
.meta { display: block; color: #888; font-size: 12px; margin-top: 3px; }
.failed { color: #b00; font-size: 12px; padding: 8px 0; }
@media (prefers-color-scheme: dark) {
  body { background: #16181c; color: #e6e6e6; }
  header, nav { background: #1f2228; border-color: #333; }
  nav a { background: #2a2f3a; color: #8ab4f8; }
  li { border-color: #2a2a2a; }
  li a { color: #e6e6e6; }
  section h2 { border-color: #8ab4f8; }
}
"""


def render_html(sections: List[Section], now: datetime) -> str:
    esc = html_lib.escape
    jst = timezone(timedelta(hours=9))
    updated = now.astimezone(jst).strftime("%Y-%m-%d %H:%M")

    # 各セクションに一意なアンカー id を付与（連番）
    anchors = [f"sec-{i}" for i in range(len(sections))]

    nav_links = "".join(
        f'<a href="#{anchors[i]}">{esc(sec.name)}</a>' for i, sec in enumerate(sections)
    )

    body_parts = []
    for i, sec in enumerate(sections):
        items = []
        for art in sec.articles:
            rel = format_relative(art.published, now)
            meta = f"{esc(art.source_name)}"
            if rel:
                meta += f" ・ {rel}"
            items.append(
                f'<li><a href="{esc(art.link)}" target="_blank" rel="noopener">'
                f"{esc(art.title)}</a>"
                f'<span class="meta">{meta}</span></li>'
            )
        failed = ""
        if sec.failed_sources:
            failed = (
                '<div class="failed">取得失敗: '
                + esc("、".join(sec.failed_sources))
                + "</div>"
            )
        body_parts.append(
            f'<section id="{anchors[i]}"><h2>{esc(sec.name)}</h2>'
            f"<ul>{''.join(items)}</ul>{failed}</section>"
        )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ja"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>今朝のニュース</title>"
        f"<style>{PAGE_CSS}</style>"
        "</head><body>"
        f'<header><h1>今朝のニュース</h1><div class="updated">最終更新: {updated} JST</div></header>'
        f"<nav>{nav_links}</nav>"
        f"<main>{''.join(body_parts)}</main>"
        "</body></html>"
    )
```

注: `_slugify` は使わず連番アンカーにするため、Step 3 のコードに `_slugify` は含めない（上のブロックから削除して実装すること）。`field` を使うので import 変更を忘れないこと。

- [ ] **Step 4: テストが通ることを確認**

Run: `cd ~/cc/morning-news && python3 -m unittest tests.test_render -v`
Expected: PASS（5 tests OK）

- [ ] **Step 5: コミット**

```bash
cd ~/cc/morning-news
git add build.py tests/test_render.py
git commit -m "feat: スマホ最適化HTMLレンダラを追加"
```

---

### Task 5: フェッチ層とソース定義、main の結線

ネットワーク取得（`fetch`）、ソース定義（`SOURCES`）、全体を組み立てる `main` を追加する。ネットワークを使う層なのでユニットテストは行わず、実行して目視確認する。

**Files:**
- Modify: `~/cc/morning-news/build.py`

- [ ] **Step 1: フェッチ・ソース定義・main を追記**

`import` 群に以下を追加:

```python
import urllib.request
import urllib.error
```

build.py 末尾に追記:

```python
# (セクション名, ソース名, RSS URL)
SOURCES = [
    ("国内 総合", "NHK 主要", "https://www.nhk.or.jp/rss/news/cat0.xml"),
    ("国内 総合", "Yahoo!トピックス", "https://news.yahoo.co.jp/rss/topics/top-picks.xml"),
    ("世界", "NHK 国際", "https://www.nhk.or.jp/rss/news/cat6.xml"),
    ("世界", "BBC News Japan", "https://feeds.bbci.co.uk/japanese/rss.xml"),
    ("経済・ビジネス", "NHK 経済", "https://www.nhk.or.jp/rss/news/cat5.xml"),
    ("経済・ビジネス", "Yahoo! 経済", "https://news.yahoo.co.jp/rss/topics/business.xml"),
    ("テクノロジー・IT", "ITmedia", "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml"),
    ("テクノロジー・IT", "Yahoo! IT", "https://news.yahoo.co.jp/rss/topics/it.xml"),
    ("テクノロジー・IT", "はてブ テクノロジー", "https://b.hatena.ne.jp/hotentry/it.rss"),
    ("スポーツ・エンタメ", "Yahoo! スポーツ", "https://news.yahoo.co.jp/rss/topics/sports.xml"),
    ("スポーツ・エンタメ", "Yahoo! エンタメ", "https://news.yahoo.co.jp/rss/topics/entertainment.xml"),
]

MAX_PER_SECTION = 12
FETCH_TIMEOUT = 20


def fetch(url: str) -> Optional[str]:
    """URL の本文文字列を返す。失敗時は None。リダイレクトは urllib が自動追従する。"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (morning-news bot)"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read()
        return raw.decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"  [WARN] fetch failed: {url} ({e})")
        return None


def build_sections(now: datetime) -> List[Section]:
    """SOURCES を走査してセクションのリストを組み立てる。
    セクションの並びは SOURCES に初出した順を保つ。"""
    order: List[str] = []
    by_section = {}  # name -> {"arts": [...], "failed": [...]}
    for section_name, source_name, url in SOURCES:
        if section_name not in by_section:
            by_section[section_name] = {"arts": [], "failed": []}
            order.append(section_name)
        body = fetch(url)
        if body is None:
            by_section[section_name]["failed"].append(source_name)
            continue
        arts = parse_feed(body, source_name)
        if not arts:
            by_section[section_name]["failed"].append(source_name)
        by_section[section_name]["arts"].extend(arts)

    sections: List[Section] = []
    for name in order:
        arts = by_section[name]["arts"]
        # published がある記事を新しい順に。日付なしは末尾へ。
        arts.sort(
            key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        sections.append(
            Section(
                name=name,
                articles=arts[:MAX_PER_SECTION],
                failed_sources=by_section[name]["failed"],
            )
        )
    return sections


def main() -> None:
    now = datetime.now(timezone.utc)
    print("Building morning-news...")
    sections = build_sections(now)
    total = sum(len(s.articles) for s in sections)
    print(f"  {len(sections)} sections, {total} articles")
    html_out = render_html(sections, now)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_out)
    print("  wrote index.html")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: ローカル実行して疎通確認**

Run: `cd ~/cc/morning-news && python3 build.py`
Expected: `Building morning-news...` に続き `5 sections, N articles`（N は 40〜60 程度）が表示され、`wrote index.html`。全ソースが取得失敗する（N=0）ならネットワークか URL の問題なので中断して調査する。

- [ ] **Step 3: 生成物を目視確認**

Run: `cd ~/cc/morning-news && open index.html`
Expected: ブラウザで5セクションの見出しが表示される。リンクをタップすると元記事へ遷移。上部タブでセクションへジャンプ。macOS のダークモード切替で配色が変わる。

- [ ] **Step 4: 生成物を Pages 配信対象にしつつ再生成可能にする**

`index.html` は生成物だがルート配信に必要なのでコミットする。ローカル生成物とActions生成物の差分は許容する。

```bash
cd ~/cc/morning-news
git add build.py index.html
git commit -m "feat: フェッチ層・ソース定義・main を結線し index.html を生成"
```

---

### Task 6: GitHub Actions ワークフロー

毎朝 6:00 JST と手動実行で `build.py` を回し、差分があれば commit & push する。

**Files:**
- Create: `~/cc/morning-news/.github/workflows/build.yml`

- [ ] **Step 1: ワークフローを作成**

`.github/workflows/build.yml`:

```yaml
name: Build morning news

on:
  schedule:
    # 6:00 JST = 21:00 UTC（前日）
    - cron: "0 21 * * *"
  workflow_dispatch: {}

permissions:
  contents: write

concurrency:
  group: build-morning-news
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.9"

      - name: Generate index.html
        run: python3 build.py

      - name: Commit if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          if [ -n "$(git status --porcelain index.html)" ]; then
            git add index.html
            git commit -m "chore: 自動更新 $(date -u +%Y-%m-%dT%H:%MZ)"
            git push
          else
            echo "変更なし"
          fi
```

- [ ] **Step 2: コミット**

```bash
cd ~/cc/morning-news
git add .github/workflows/build.yml
git commit -m "ci: 毎朝6:00 JSTにページを自動生成するワークフローを追加"
```

---

### Task 7: 公開手順（GitHub へ push して Pages 有効化）

このタスクは手動操作を伴う。ユーザーの GitHub アカウントが必要。gh CLI 未インストールのため導入から案内する。

**Files:** なし（操作のみ）

- [ ] **Step 1: gh CLI を導入して認証**

Homebrew が無い環境のため（メモ: このMacは homebrew 不可の可能性）、まず確認する:

Run: `which gh || echo "gh未導入"`

未導入なら、ユーザーにブラウザ操作を依頼する方式へ切替（Step 2b）。導入済み／導入できる場合:

Run（ユーザー自身が実行）: `! gh auth login`

- [ ] **Step 2a: gh でリポジトリ作成して push（gh が使える場合）**

```bash
cd ~/cc/morning-news
gh repo create morning-news --public --source=. --remote=origin --push
gh api -X POST repos/:owner/morning-news/pages -f "source[branch]=main" -f "source[path]=/" 2>/dev/null || \
  echo "Pages はブラウザの Settings > Pages で 'main / (root)' を選択して有効化してください"
```

- [ ] **Step 2b: gh が使えない場合の手動手順（ユーザーに案内）**

1. github.com で新規リポジトリ `morning-news`（Public）を作成
2. ローカルで remote 追加と push:

```bash
cd ~/cc/morning-news
git remote add origin https://github.com/<ユーザー名>/morning-news.git
git push -u origin main
```

3. リポジトリの Settings > Pages で Source を `Deploy from a branch`、Branch を `main` / `(root)` に設定して Save
4. Settings > Actions > General > Workflow permissions を `Read and write permissions` に設定（Actions が push できるようにする）

- [ ] **Step 3: 動作確認**

1. Actions タブで `Build morning news` を `Run workflow`（workflow_dispatch）から手動実行 → 成功を確認
2. 数分後 `https://<ユーザー名>.github.io/morning-news/` をスマホで開く
3. スマホのブラウザで「ホーム画面に追加」してアプリのように使えることを確認

- [ ] **Step 4: 完了**

以降は毎朝 6:00 JST に自動更新される。ソースの追加・削除は `build.py` の `SOURCES` を編集して push するだけ。

---

## Self-Review 結果

- **Spec coverage:** 目的/アーキ/コンポーネント(build.py・ソース定義・index.html・Actions)/エラー処理/テスト方針/公開手順 すべて Task に対応済み。AI要約・通知等はスコープ外として実装しない（spec 準拠）。
- **Placeholder scan:** 各コード step は実コードを記載。`<ユーザー名>` はユーザー固有値のため意図的なプレースホルダ（手順内で明示）。
- **Type consistency:** `Article(title, link, source_name, published)`、`Section(name, articles, failed_sources)`、`parse_feed(xml_text, source_name)`、`format_relative(published, now)`、`render_html(sections, now)`、`fetch(url)`、`build_sections(now)` が全タスクで一貫。
- **注意点:** Task 4 の実装ブロックに含めた `_slugify` は未使用のため実装時に除外する旨を明記済み。`field` の import 追加を明記済み。
