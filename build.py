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
