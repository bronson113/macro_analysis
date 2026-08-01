"""Behavior tests for durable CSV storage and source-health persistence."""

import csv
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from fetcher import MacroFetcher
from news_analyzer import MacroNewsAnalyzer
from source_health import classify_source_error
from storage import CSV_SCHEMAS, MacroStorage, atomic_write_csv


def temp_storage(base: Path) -> MacroStorage:
    """Build a storage instance whose entire CSV set lives in one temporary directory."""
    return MacroStorage(
        indicators_csv=base / "indicators.csv",
        observations_csv=base / "observations.csv",
        snapshots_csv=base / "snapshots.csv",
        news_csv=base / "news.csv",
        run_logs_csv=base / "run_logs.csv",
    )


class TestStorageResilience(unittest.TestCase):
    def test_atomic_write_keeps_original_when_replacement_fails(self):
        """A failed replace must leave the last complete CSV in place."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "observations.csv"
            path.write_text("value\n1\n", encoding="utf-8")

            with patch("storage.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    atomic_write_csv(path, pd.DataFrame([{"value": 2}]))

            self.assertEqual(path.read_text(encoding="utf-8"), "value\n1\n")
            self.assertEqual(list(Path(tmp_dir).glob("*.tmp")), [])

    def test_existing_csv_gains_schema_columns_without_losing_unknown_columns(self):
        """Schema migration must retain operator-owned columns while adding required ones."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            observations = base / "observations.csv"
            observations.write_text(
                "indicator_key,date,operator_note\ntest,2026-08-01,keep me\n",
                encoding="utf-8",
            )

            temp_storage(base)

            with observations.open(encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))
                columns = csv_file.seek(0) or next(csv.reader(csv_file))

        self.assertEqual(columns[: len(CSV_SCHEMAS["observations"]["columns"])], CSV_SCHEMAS["observations"]["columns"])
        self.assertEqual(columns[-1], "operator_note")
        self.assertEqual(rows[0]["operator_note"], "keep me")
        self.assertEqual(rows[0]["value"], "")
        self.assertEqual(rows[0]["updated_at"], "")

    def test_indicator_seed_keeps_custom_values_for_known_indicators(self):
        """Refreshing built-in metadata must not erase an operator's custom indicator fields."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            indicators = base / "indicators.csv"
            indicators.write_text(
                "key,name,operator_note\ncpi,Custom CPI,manual override\n",
                encoding="utf-8",
            )

            temp_storage(base)

            with indicators.open(encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))
        cpi = next(row for row in rows if row["key"] == "cpi")
        self.assertEqual(cpi["operator_note"], "manual override")

    def test_observation_update_keeps_existing_operator_owned_columns(self):
        """Refreshing a canonical observation must not blank its operator-owned context."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            storage = temp_storage(base)
            storage.save_observations(
                "cpi", pd.DataFrame([{"date": "2026-08-01", "value": 3.0}])
            )
            observations = pd.read_csv(base / "observations.csv")
            observations["operator_note"] = "preserve this"
            atomic_write_csv(base / "observations.csv", observations)

            storage.save_observations(
                "cpi", pd.DataFrame([{"date": "2026-08-01", "value": 3.1}])
            )
            updated = pd.read_csv(base / "observations.csv")

        row = updated.iloc[0]
        self.assertEqual(row["value"], 3.1)
        self.assertEqual(row["operator_note"], "preserve this")

    def test_daily_snapshot_update_keeps_existing_operator_owned_columns(self):
        """Refreshing a canonical snapshot must retain its operator-owned context."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            storage = temp_storage(base)
            storage.save_daily_snapshot({"date": "2026-08-01", "vix": 18.0})
            snapshots = pd.read_csv(base / "snapshots.csv")
            snapshots["operator_note"] = "preserve this"
            atomic_write_csv(base / "snapshots.csv", snapshots)

            storage.save_daily_snapshot({"date": "2026-08-01", "vix": 19.5})
            updated = pd.read_csv(base / "snapshots.csv")

        row = updated.iloc[0]
        self.assertEqual(row["vix"], 19.5)
        self.assertEqual(row["operator_note"], "preserve this")

    def test_migrated_observation_refresh_preserves_operator_fields_with_blank_timestamp(self):
        """A legacy blank updated_at column must accept a refreshed timestamp and retain context."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "observations.csv").write_text(
                "indicator_key,date,value,operator_note\ncpi,2026-08-01,3.0,preserve this\n",
                encoding="utf-8",
            )
            storage = temp_storage(base)

            storage.save_observations(
                "cpi", pd.DataFrame([{"date": "2026-08-01", "value": 3.1}])
            )
            updated = pd.read_csv(base / "observations.csv")

        row = updated.iloc[0]
        self.assertEqual(row["value"], 3.1)
        self.assertEqual(row["operator_note"], "preserve this")
        self.assertTrue(row["updated_at"])

    def test_migrated_snapshot_refresh_preserves_operator_fields_with_blank_timestamp(self):
        """A legacy blank created_at column must accept a refreshed timestamp and retain context."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "snapshots.csv").write_text(
                "date,vix,operator_note\n2026-08-01,18.0,preserve this\n",
                encoding="utf-8",
            )
            storage = temp_storage(base)

            storage.save_daily_snapshot({"date": "2026-08-01", "vix": 19.5})
            updated = pd.read_csv(base / "snapshots.csv")

        row = updated.iloc[0]
        self.assertEqual(row["vix"], 19.5)
        self.assertEqual(row["operator_note"], "preserve this")
        self.assertTrue(row["created_at"])

    def test_snapshot_update_can_add_an_operator_owned_column(self):
        """A duplicate-date snapshot may introduce a new operator field without failing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            storage = temp_storage(base)
            storage.save_daily_snapshot({"date": "2026-08-01", "vix": 18.0})

            storage.save_daily_snapshot({
                "date": "2026-08-01",
                "vix": 19.5,
                "operator_note": "added later",
            })
            updated = pd.read_csv(base / "snapshots.csv")

        row = updated.iloc[0]
        self.assertEqual(row["vix"], 19.5)
        self.assertEqual(row["operator_note"], "added later")

    def test_source_error_classification_has_stable_machine_categories(self):
        """Changing error wording must not turn known failures into an opaque category."""
        self.assertEqual(classify_source_error("request timed out"), "network")
        self.assertEqual(classify_source_error("JSON payload missing score"), "parse")
        self.assertEqual(classify_source_error("value outside expected range"), "validation")
        self.assertEqual(classify_source_error("unexpected provider failure"), "unknown")

    def test_fetch_failure_is_recorded_as_stale_machine_readable_health(self):
        """A failed fetch records its retained prior observation as stale source health."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_observations(
                "fed_total_assets",
                pd.DataFrame([{"date": "2026-07-31", "value": 7000000.0}]),
            )
            fetcher = MacroFetcher(storage=storage)
            fetcher.fetch_fred_series = lambda key, info: (0, "timed out")
            fetcher.fetch_yahoo_ticker = lambda key, ticker: (1, None)
            fetcher.fetch_cnn_fear_greed_index = lambda: (1, None)
            fetcher.fetch_shiller_pe_ratio = lambda: (1, None)
            fetcher.news_analyzer.fetch_and_store_news = lambda: 0

            fetcher.fetch_all()
            health = storage.get_latest_source_health(
                source="FRED", fetch_key="fed_total_assets"
            )

        self.assertEqual(health["status"], "ERROR")
        self.assertEqual(health["error_category"], "network")
        self.assertIs(health["is_stale"], True)
        self.assertEqual(health["observation_time"], "2026-07-31")

    def test_successful_fetch_is_persisted_as_current_health(self):
        """A successful result must be distinguishable from stale or failed source state."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            fetcher = MacroFetcher(storage=storage)
            fetcher.fetch_fred_series = lambda key, info: (3, None)
            fetcher.fetch_yahoo_ticker = lambda key, ticker: (1, None)
            fetcher.fetch_cnn_fear_greed_index = lambda: (1, None)
            fetcher.fetch_shiller_pe_ratio = lambda: (1, None)
            fetcher.news_analyzer.fetch_and_store_news = lambda: 0

            fetcher.fetch_all()
            health = storage.get_latest_source_health(
                source="FRED", fetch_key="fed_total_assets"
            )

        self.assertEqual(health["status"], "CURRENT")
        self.assertIs(health["is_stale"], False)
        self.assertEqual(health["record_count"], 3)
        self.assertEqual(health["error_category"], "")

    def test_zero_usable_fetch_results_are_error_health_when_prior_data_remains(self):
        """A syntactically valid but empty result cannot claim a retained observation is current."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_observations(
                "fed_total_assets",
                pd.DataFrame([{"date": "2026-07-31", "value": 7000000.0}]),
            )
            fetcher = MacroFetcher(storage=storage)
            fetcher.fetch_fred_series = lambda key, info: (0, None)
            fetcher.fetch_yahoo_ticker = lambda key, ticker: (1, None)
            fetcher.fetch_cnn_fear_greed_index = lambda: (1, None)
            fetcher.fetch_shiller_pe_ratio = lambda: (1, None)
            fetcher.news_analyzer.fetch_and_store_news = lambda: 0

            fetcher.fetch_all()
            health = storage.get_latest_source_health(
                source="FRED", fetch_key="fed_total_assets"
            )

        self.assertEqual(health["status"], "ERROR")
        self.assertIs(health["is_stale"], True)
        self.assertEqual(health["error_category"], "parse")

    def test_google_news_timeout_is_persisted_in_source_health_and_counts(self):
        """A swallowed RSS timeout must remain visible to the scheduler's health consumers."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            fetcher = MacroFetcher(storage=storage)
            fetcher.fetch_fred_series = lambda key, info: (1, None)
            fetcher.fetch_yahoo_ticker = lambda key, ticker: (1, None)
            fetcher.fetch_cnn_fear_greed_index = lambda: (1, None)
            fetcher.fetch_shiller_pe_ratio = lambda: (1, None)
            news = MacroNewsAnalyzer(storage=storage)
            fetcher.news_analyzer = news

            with patch.object(news, "fetch_bellwether_sector_news", return_value=[]), patch(
                "news_analyzer.NEWS_RSS_QUERIES",
                [("Test Category", "https://example.test/rss")],
            ), patch(
                "news_analyzer.urllib.request.urlopen",
                side_effect=TimeoutError("timed out"),
            ):
                result = fetcher.fetch_all()
            health = storage.get_latest_source_health(
                source="Google News", fetch_key="google_news:test_category"
            )

        self.assertEqual(health["status"], "ERROR")
        self.assertEqual(health["error_category"], "network")
        self.assertEqual(result["source_status_counts"]["Google News"]["ERROR"], 1)

    def test_independent_storage_instances_keep_all_concurrent_observation_updates(self):
        """Separate writers sharing a CSV must not lose rows during read-modify-write cycles."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            first = temp_storage(base)
            second = temp_storage(base)

            def save_many(storage, prefix):
                for index in range(12):
                    storage.save_observations(
                        f"{prefix}_{index}",
                        pd.DataFrame([{"date": "2026-08-01", "value": index}]),
                    )

            with ThreadPoolExecutor(max_workers=2) as executor:
                first_future = executor.submit(save_many, first, "first")
                second_future = executor.submit(save_many, second, "second")
                first_future.result()
                second_future.result()

            observations = pd.read_csv(base / "observations.csv")

        self.assertEqual(len(observations), 24)
        self.assertEqual(set(observations["indicator_key"]), {
            *(f"first_{index}" for index in range(12)),
            *(f"second_{index}" for index in range(12)),
        })


if __name__ == "__main__":
    unittest.main()
