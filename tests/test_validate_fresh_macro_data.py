from datetime import date, timedelta
import unittest

import pandas as pd

from validate_fresh_macro_data import validate_observations


def _write_observations(path, today, overrides=None):
    overrides = overrides or {}
    rows = []
    for key in ("fed_total_assets", "tga_balance", "reverse_repo", "dff"):
        latest = overrides.get(key, today)
        rows.extend(
            [
                {"indicator_key": key, "date": latest - timedelta(days=35), "value": 1.0},
                {"indicator_key": key, "date": latest, "value": 2.0},
            ]
        )
    pd.DataFrame(rows).to_csv(path, index=False)


class TestFreshMacroDataValidator(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_accepts_fresh_core_series_with_30_day_history(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_observations(observations, today)

        self.assertEqual(validate_observations(observations, today=today), [])

    def test_rejects_stale_daily_policy_data(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_observations(observations, today, {"dff": today - timedelta(days=6)})

        errors = validate_observations(observations, today=today)

        self.assertTrue(any("dff" in error and "stale" in error for error in errors))

    def test_rejects_missing_30_day_history(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_observations(observations, today)
        frame = pd.read_csv(observations)
        frame = frame[
            ~(
                (frame["indicator_key"] == "reverse_repo")
                & (frame["date"] == str(today - timedelta(days=35)))
            )
        ]
        frame.to_csv(observations, index=False)

        errors = validate_observations(observations, today=today)

        self.assertTrue(
            any("reverse_repo" in error and "30-day trend" in error for error in errors)
        )
