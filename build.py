from __future__ import annotations

import html as html_lib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional


@dataclass
class Article:
    title: str
    link: str
    source_name: str
    published: Optional[datetime]


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


@dataclass
class Section:
    name: str
    articles: List[Article]
    failed_sources: List[str] = field(default_factory=list)


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
