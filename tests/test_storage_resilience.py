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

    def test_latest_observation_keeps_legacy_string_date_shape(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_observations(
                "cpi", pd.DataFrame([{"date": "2026-08-01", "value": 3.1}])
            )

            latest = storage.get_latest_observation("cpi")

        assert latest["date"] == "2026-08-01"

    def test_observation_revisions_are_preserved_by_vintage_metadata(self):
        """A revised observation must remain alongside its earlier vintage."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_observations(
                "core_pce",
                pd.DataFrame([
                    {
                        "date": "2026-06-30",
                        "value": 120.0,
                        "vintage_date": "2026-07-31",
                        "publication_date": "2026-07-31",
                        "source_url": "https://example.test/pce",
                        "unit": "index",
                    },
                    {
                        "date": "2026-06-30",
                        "value": 121.0,
                        "vintage_date": "2026-08-29",
                        "publication_date": "2026-08-29",
                        "source_url": "https://example.test/pce",
                        "unit": "index",
                    },
                ]),
            )

            rows = storage.get_indicator_series(
                "core_pce", limit=None, as_of=pd.Timestamp("2026-08-31"), include_metadata=True
            )

        assert len(rows) == 1
        assert rows.iloc[0]["value"] == 121.0
        assert rows.iloc[0]["vintage_date"] == pd.Timestamp("2026-08-29")

    def test_observation_as_of_uses_only_vintages_available_by_date(self):
        """An earlier analysis date must not see a later revision."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_observations(
                "core_pce",
                pd.DataFrame([
                    {"date": "2026-06-30", "value": 120.0, "vintage_date": "2026-07-31"},
                    {"date": "2026-06-30", "value": 121.0, "vintage_date": "2026-08-29"},
                ]),
            )

            rows = storage.get_indicator_series(
                "core_pce", limit=None, as_of=pd.Timestamp("2026-08-15"), include_metadata=True
            )

        assert len(rows) == 1
        assert rows.iloc[0]["value"] == 120.0
        assert rows.iloc[0]["vintage_date"] == pd.Timestamp("2026-07-31")

    def test_fred_fetch_persists_source_and_vintage_metadata(self):
        """Fetcher writes source URL, declared unit, and fetch vintage metadata."""
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"DATE,TEST\n2026-08-01,3.0\n"

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            fetcher = MacroFetcher(storage)
            with patch("fetcher.urllib.request.urlopen", return_value=FakeResponse()):
                count, error = fetcher.fetch_fred_series(
                    "test_metric",
                    {
                        "id": "TEST",
                        "unit": "percent",
                        "source_url": "https://fred.stlouisfed.org/series/TEST",
                    },
                    max_retries=1,
                )
            rows = storage.get_indicator_series(
                "test_metric", limit=None, include_metadata=True
            )

        assert error is None
        assert count == 1
        assert rows.iloc[0]["unit"] == "percent"
        assert rows.iloc[0]["source_url"].endswith("/series/TEST")
        assert pd.notna(rows.iloc[0]["vintage_date"])

    def test_fred_fetch_rejects_wrong_regime_source_unit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            fetcher = MacroFetcher(storage)
            count, error = fetcher.fetch_fred_series(
                "nominal_gdp",
                {"id": "GDP", "unit": "millions"},
                max_retries=1,
            )

        assert count == 0
        assert error is not None
        assert "unit" in error.lower()

    def test_consensus_storage_preserves_point_in_time_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_consensus_records(
                [
                    {
                        "survey_reference_date": "2026-07-01",
                        "publication_date": "2026-07-10",
                        "target_date": "2027-01-01",
                        "horizon_months": 6,
                        "metric": "FED_FUNDS_RATE_AND_FED_BALANCE_SHEET_ASSETS",
                        "expected_dff": 4.0,
                        "expected_fed_assets": 7040.0,
                        "unit": "percent_and_billions_usd",
                        "source_url": "https://example.test/sme",
                        "parsing_status": "OK",
                    },
                    {
                        "survey_reference_date": "2026-07-01",
                        "publication_date": "2026-08-01",
                        "target_date": "2027-01-01",
                        "horizon_months": 6,
                        "metric": "FED_FUNDS_RATE_AND_FED_BALANCE_SHEET_ASSETS",
                        "expected_dff": 3.9,
                        "expected_fed_assets": 7050.0,
                        "unit": "percent_and_billions_usd",
                        "source_url": "https://example.test/sme",
                        "parsing_status": "OK",
                    },
                ]
            )
            records = storage.get_consensus_records(as_of=pd.Timestamp("2026-07-31"))

        assert len(records) == 1
        assert records[0]["expected_dff"] == 4.0
        assert records[0]["publication_date"] == pd.Timestamp("2026-07-10")
        assert records[0]["source_url"].endswith("/sme")
        assert records[0]["parsing_status"] == "OK"

    def test_legacy_observation_without_vintage_is_excluded_from_strict_as_of_reads(self):
        """Unknown legacy availability must not be treated as point-in-time evidence."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = temp_storage(Path(tmp_dir))
            storage.save_observations(
                "rstar", pd.DataFrame([{"date": "2026-06-30", "value": 0.1}])
            )

            strict_rows = storage.get_indicator_series(
                "rstar", limit=None, as_of=pd.Timestamp("2026-08-15"), include_metadata=True
            )
            legacy_rows = storage.get_indicator_series(
                "rstar", limit=None, as_of=pd.Timestamp("2026-08-15"),
                include_metadata=True, allow_legacy=True,
            )

        assert strict_rows.empty
        assert len(legacy_rows) == 1

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
            fetcher.fetch_hlw_rstar = lambda: (1, None)
            fetcher.fetch_consensus = lambda: (1, None)
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
            fetcher.fetch_hlw_rstar = lambda: (1, None)
            fetcher.fetch_consensus = lambda: (1, None)
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
            fetcher.fetch_hlw_rstar = lambda: (1, None)
            fetcher.fetch_consensus = lambda: (1, None)
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
            fetcher.fetch_hlw_rstar = lambda: (1, None)
            fetcher.fetch_consensus = lambda: (1, None)
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
