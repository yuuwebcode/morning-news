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
