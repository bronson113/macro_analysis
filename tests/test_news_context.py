import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news_analyzer import MacroNewsAnalyzer
from storage import MacroStorage


class FakeStorage:
    pass


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body.encode("utf-8")


class TestNewsContext(unittest.TestCase):
    def test_keyword_tags_are_context_not_directional_scores(self):
        """Removing a keyword must not turn an article into a directional score."""
        result = MacroNewsAnalyzer(FakeStorage())._build_context(
            "CEO says rate hike fears are not justified",
            "The company rejected reports of a crisis.",
        )

        self.assertEqual(result["topic_tags"], ["monetary_policy", "stress"])
        self.assertEqual(result["interpretation_status"], "uninterpreted")
        self.assertIsNone(result["impact_score"])
        self.assertIsNone(result["sentiment"])

    def test_google_news_keeps_source_and_retrieval_provenance(self):
        """Published source time and fetch time stay attached to an uninterpreted item."""
        feed = """<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel><item>
            <title>Company warns of layoffs</title>
            <link>https://example.test/story</link>
            <source>Example News</source>
            <description>Management cited a crisis.</description>
            <pubDate>2026-08-01T12:00:00Z</pubDate>
        </item></channel></rss>"""

        with patch("news_analyzer.NEWS_RSS_QUERIES", [("Test", "https://example.test/rss")]), patch(
            "news_analyzer.urllib.request.urlopen", return_value=FakeResponse(feed)
        ):
            events = MacroNewsAnalyzer(FakeStorage()).fetch_google_news()

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["topic_tags"], ["corporate_fundamentals", "stress"])
        self.assertEqual(event["published_at"], "2026-08-01T12:00:00Z")
        self.assertTrue(event["retrieved_at"])
        self.assertEqual(event["interpretation_status"], "uninterpreted")
        self.assertIsNone(event["impact_score"])
        self.assertIsNone(event["sentiment"])

    def test_storage_round_trips_context_and_legacy_rows(self):
        """Storage must preserve null interpretation fields while old rows remain readable."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            legacy_path = base / "legacy_news.csv"
            legacy_path.write_text(
                "id,date,title,summary,source,link,category,impact_score,sentiment,created_at\n"
                "1,2026-07-31,Old article,,,,General Macro,0.0,Neutral,2026-07-31T00:00:00\n",
                encoding="utf-8",
            )
            storage = MacroStorage(
                indicators_csv=base / "indicators.csv",
                observations_csv=base / "observations.csv",
                snapshots_csv=base / "snapshots.csv",
                news_csv=legacy_path,
                run_logs_csv=base / "runs.csv",
            )
            storage.save_news_events([
                {
                    "date": "2026-08-01",
                    "title": "Contextual article",
                    "topic_tags": ["stress", "monetary_policy"],
                    "interpretation_status": "uninterpreted",
                    "published_at": "2026-08-01T12:00:00Z",
                    "retrieved_at": "2026-08-01T12:05:00Z",
                    "impact_score": None,
                    "sentiment": None,
                }
            ])

            saved = storage.get_recent_news(limit=2)
            with legacy_path.open(encoding="utf-8", newline="") as news_file:
                persisted_rows = list(csv.DictReader(news_file))

        current = next(item for item in saved if item["title"] == "Contextual article")
        legacy = next(item for item in saved if item["title"] == "Old article")
        persisted_current = next(
            item for item in persisted_rows if item["title"] == "Contextual article"
        )
        self.assertEqual(
            persisted_current["topic_tags"], '["monetary_policy","stress"]'
        )
        self.assertEqual(current["topic_tags"], ["monetary_policy", "stress"])
        self.assertEqual(current["interpretation_status"], "uninterpreted")
        self.assertEqual(current["published_at"], "2026-08-01T12:00:00Z")
        self.assertEqual(current["retrieved_at"], "2026-08-01T12:05:00Z")
        self.assertIsNone(current["impact_score"])
        self.assertIsNone(current["sentiment"])
        self.assertEqual(legacy["topic_tags"], [])
        self.assertEqual(legacy["interpretation_status"], "legacy_uninterpreted")


if __name__ == "__main__":
    unittest.main()
