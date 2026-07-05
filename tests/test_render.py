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


if __name__ == "__main__":
    unittest.main()
