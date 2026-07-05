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
