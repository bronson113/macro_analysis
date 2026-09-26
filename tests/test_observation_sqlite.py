"""Behavior tests for the compact SQLite observation store."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from storage import MacroStorage
from observation_sqlite import ObservationSQLiteStore


def sqlite_storage(database: Path) -> MacroStorage:
    """Build a storage object with all ledgers isolated in a temporary directory."""
    base = database.parent
    return MacroStorage(
        indicators_csv=base / "indicators.csv",
        observations_db=database,
        observations_csv=None,
        snapshots_csv=base / "snapshots.csv",
        news_csv=base / "news.csv",
        run_logs_csv=base / "run_logs.csv",
    )


class TestObservationSQLite(unittest.TestCase):
    def test_sqlite_reads_latest_and_as_of_revisions_and_retains_unknown_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = sqlite_storage(Path(temp_dir) / "observations.sqlite")
            storage.save_observations(
                "core_pce",
                pd.DataFrame([
                    {
                        "date": "2026-06-30",
                        "value": 120.0,
                        "vintage_date": "2026-07-31",
                        "operator_note": "initial estimate",
                    },
                    {
                        "date": "2026-06-30",
                        "value": 121.0,
                        "vintage_date": "2026-08-29",
                        "operator_note": "revised estimate",
                    },
                ]),
            )

            early = storage.get_indicator_series(
                "core_pce", limit=None, as_of="2026-08-15", include_metadata=True
            )
            all_revisions = storage.get_observation_revisions("core_pce")
            latest = storage.get_latest_observation("core_pce")

        self.assertEqual(len(early), 1)
        self.assertEqual(early.iloc[0]["value"], 120.0)
        self.assertEqual(early.iloc[0]["vintage_date"], pd.Timestamp("2026-07-31"))
        self.assertEqual(len(all_revisions), 2)
        self.assertEqual(all_revisions["operator_note"].tolist(), [
            "initial estimate", "revised estimate"
        ])
        self.assertEqual(latest["operator_note"], "revised estimate")

    def test_batch_updates_are_atomic_when_one_indicator_cannot_be_encoded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = sqlite_storage(Path(temp_dir) / "observations.sqlite")
            storage.save_observation_batches({
                "cpi": pd.DataFrame([{"date": "2026-01-01", "value": 1.0}]),
                "pce": pd.DataFrame([{"date": "2026-01-01", "value": 2.0}]),
            })
            store = storage._observation_store
            original_compress = store._compress

            def fail_on_pce(frame):
                if frame["indicator_key"].eq("pce").any():
                    raise ValueError("injected serialization failure")
                return original_compress(frame)

            with patch.object(store, "_compress", side_effect=fail_on_pce):
                with self.assertRaisesRegex(ValueError, "injected serialization failure"):
                    storage.save_observation_batches({
                        "cpi": pd.DataFrame([{"date": "2026-01-02", "value": 1.1}]),
                        "pce": pd.DataFrame([{"date": "2026-01-02", "value": 2.1}]),
                    })

            cpi = storage.get_indicator_series("cpi", limit=None)
            pce = storage.get_indicator_series("pce", limit=None)

        self.assertEqual(cpi["date"].dt.strftime("%Y-%m-%d").tolist(), ["2026-01-01"])
        self.assertEqual(pce["date"].dt.strftime("%Y-%m-%d").tolist(), ["2026-01-01"])

    def test_csv_migration_verifies_all_rows_and_keeps_source_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "legacy.csv.gz"
            database = base / "observations.sqlite"
            original = pd.DataFrame([
                {
                    "indicator_key": "cpi",
                    "date": "2026-01-01",
                    "value": 1.0,
                    "vintage_date": "2026-01-02",
                    "operator_note": "preserve",
                },
                {
                    "indicator_key": "pce",
                    "date": "2026-01-01",
                    "value": 2.0,
                    "vintage_date": "2026-01-03",
                },
            ])
            original.to_csv(source, index=False, compression="gzip")
            storage = sqlite_storage(database)

            imported = storage.migrate_observations_csv(source)
            migrated = storage.get_all_observations()
            source_still_exists = source.exists()

        self.assertEqual(imported, len(original))
        self.assertTrue(source_still_exists)
        self.assertEqual(len(migrated), len(original))
        self.assertEqual(migrated["operator_note"].dropna().tolist(), ["preserve"])
        self.assertEqual(
            set(zip(migrated["indicator_key"], migrated["date"].astype(str))),
            {("cpi", "2026-01-01"), ("pce", "2026-01-01")},
        )

    def test_batch_save_preserves_omitted_operator_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = sqlite_storage(Path(temp_dir) / "observations.sqlite")
            storage.save_observations(
                "cpi",
                pd.DataFrame([{
                    "date": "2026-01-01",
                    "value": 1.0,
                    "operator_note": "keep",
                }]),
            )
            storage.save_observation_batches({
                "cpi": pd.DataFrame([{"date": "2026-01-01", "value": 1.1}]),
            })
            revisions = storage.get_observation_revisions("cpi")

        self.assertEqual(revisions.iloc[0]["value"], 1.1)
        self.assertEqual(revisions.iloc[0]["operator_note"], "keep")

    def test_weekly_digest_bulk_loads_the_sqlite_store(self):
        from weekly_digest import WeeklyDigestGenerator

        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "observations.sqlite"
            ObservationSQLiteStore(database).replace_all({
                "cpi": pd.DataFrame([{
                    "indicator_key": "cpi",
                    "date": "2026-09-01",
                    "value": 3.0,
                }]),
            })
            digest = WeeklyDigestGenerator(observations_path=database)

            observations = digest._load_observations()

        self.assertEqual(observations["indicator_key"].tolist(), ["cpi"])
        self.assertEqual(observations.iloc[0]["value"], 3.0)

    def test_backfill_bulk_loads_the_sqlite_store(self):
        import backfill_snapshots
        import config

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            database = base / "observations.sqlite"
            snapshots = base / "daily_snapshots.csv"
            recent = (pd.Timestamp.now().normalize() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
            ObservationSQLiteStore(database).replace_all({
                "treasury_10y": pd.DataFrame([
                    {"indicator_key": "treasury_10y", "date": recent, "value": 4.5},
                ]),
            })
            old_db = backfill_snapshots.OBSERVATIONS_DB
            old_indicators = backfill_snapshots.INDICATORS_CSV
            old_snapshots = config.SNAPSHOTS_CSV
            try:
                backfill_snapshots.OBSERVATIONS_DB = database
                backfill_snapshots.INDICATORS_CSV = base / "indicators.csv"
                config.SNAPSHOTS_CSV = snapshots
                backfill_snapshots.backfill()
                output = pd.read_csv(snapshots)
            finally:
                backfill_snapshots.OBSERVATIONS_DB = old_db
                backfill_snapshots.INDICATORS_CSV = old_indicators
                config.SNAPSHOTS_CSV = old_snapshots

        self.assertIn(recent, output["date"].tolist())

    def test_fresh_data_validator_reads_sqlite_observations(self):
        from datetime import date, timedelta
        from validate_fresh_macro_data import validate_observations

        today = date(2026, 9, 26)
        latest_values = {
            "fed_total_assets": (7_000_000.0, "millions"),
            "tga_balance": (800_000.0, "millions"),
            "reverse_repo": (200.0, "billions"),
            "nominal_gdp": (30_000.0, "billions"),
            "dff": (4.25, "percent"),
            "core_pce": (120.0, "index"),
            "rstar": (0.1, "percent"),
            "effr": (4.25, "percent"),
            "iorb": (4.4, "percent"),
            "sofr": (4.3, "percent"),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "observations.sqlite"
            by_indicator = {}
            for key, (value, unit) in latest_values.items():
                by_indicator[key] = pd.DataFrame([
                    {
                        "indicator_key": key,
                        "date": (today - timedelta(days=35)).isoformat(),
                        "value": value - 0.01 if key in {"dff", "effr", "iorb", "sofr", "rstar"} else value,
                        "unit": unit,
                    },
                    {
                        "indicator_key": key,
                        "date": today.isoformat(),
                        "value": value,
                        "unit": unit,
                    },
                ])
            ObservationSQLiteStore(database).replace_all(by_indicator)

            errors = validate_observations(database, today=today)

        self.assertEqual(errors, [])

    def test_status_count_uses_sqlite_row_counts_without_decompressing(self):
        from observation_sqlite import count_observations

        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "observations.sqlite"
            ObservationSQLiteStore(database).replace_all({
                "cpi": pd.DataFrame([
                    {"indicator_key": "cpi", "date": "2026-01-01", "value": 1.0},
                    {"indicator_key": "cpi", "date": "2026-01-02", "value": 1.1},
                ]),
            })
            with patch.object(
                ObservationSQLiteStore,
                "_decompress",
                side_effect=AssertionError("status must not decompress payloads"),
            ):
                count = count_observations(database)

        self.assertEqual(count, 2)

    def test_migration_removes_csv_only_after_integrity_and_size_checks(self):
        from migrate_observations import migrate

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "legacy.csv.gz"
            database = base / "observations.sqlite"
            pd.DataFrame([{
                "indicator_key": "cpi",
                "date": "2026-01-01",
                "value": 1.0,
            }]).to_csv(source, index=False, compression="gzip")

            with self.assertRaisesRegex(RuntimeError, "too large"):
                migrate(source, database, max_bytes=1, remove_source=True)
            self.assertTrue(source.exists())

            row_count, size = migrate(
                source, database, max_bytes=5_000_000, remove_source=True
            )
            source_removed = not source.exists()

        self.assertEqual(row_count, 1)
        self.assertLessEqual(size, 5_000_000)
        self.assertTrue(source_removed)

    def test_repeated_migration_never_replaces_a_populated_sqlite_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "legacy.csv.gz"
            database = base / "observations.sqlite"
            pd.DataFrame([{
                "indicator_key": "cpi",
                "date": "2026-01-01",
                "value": 1.0,
            }]).to_csv(source, index=False, compression="gzip")
            storage = sqlite_storage(database)

            storage.migrate_observations_csv(source)
            storage.save_observations(
                "cpi", pd.DataFrame([{"date": "2026-01-02", "value": 1.1}])
            )
            storage.migrate_observations_csv(source)
            series = storage.get_indicator_series("cpi", limit=None)

        self.assertEqual(series["date"].dt.strftime("%Y-%m-%d").tolist(), [
            "2026-01-01", "2026-01-02"
        ])

    def test_missing_sqlite_bulk_read_returns_empty_without_creating_file(self):
        from observation_sqlite import count_observations, read_observations

        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "missing.sqlite"

            frame = read_observations(database)
            count = count_observations(database)
            exists = database.exists()

        self.assertTrue(frame.empty)
        self.assertEqual(count, 0)
        self.assertFalse(exists)


if __name__ == "__main__":
    unittest.main()
