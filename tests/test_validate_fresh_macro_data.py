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


def _write_complete_observations(path, today, overrides=None):
    overrides = overrides or {}
    rows = []
    latest_values = {
        "fed_total_assets": 7_000_000.0,
        "tga_balance": 800_000.0,
        "reverse_repo": 200.0,
        "nominal_gdp": 30_000.0,
        "dff": 4.25,
        "core_pce": 120.0,
        "rstar": 0.1,
        "effr": 4.25,
        "iorb": 4.4,
        "sofr": 4.3,
    }
    latest_values.update(overrides.get("values", {}))
    units = {
        "fed_total_assets": "millions",
        "tga_balance": "millions",
        "reverse_repo": "billions",
        "nominal_gdp": "billions",
        "dff": "percent",
        "core_pce": "index",
        "rstar": "percent",
        "effr": "percent",
        "iorb": "percent",
        "sofr": "percent",
    }
    for key, value in latest_values.items():
        latest = overrides.get(key, today)
        rows.extend(
            [
                {
                    "indicator_key": key,
                    "date": latest - timedelta(days=35),
                    "value": value - 0.01 if key in {"dff", "effr", "iorb", "sofr", "rstar"} else value,
                    "unit": units[key],
                },
                {"indicator_key": key, "date": latest, "value": value, "unit": units[key]},
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
        _write_complete_observations(observations, today)

        self.assertEqual(validate_observations(observations, today=today), [])

    def test_rejects_stale_daily_policy_data(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_complete_observations(observations, today, {"dff": today - timedelta(days=8)})

        errors = validate_observations(observations, today=today)

        self.assertTrue(any("dff" in error and "stale" in error for error in errors))

    def test_rejects_missing_30_day_history(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_complete_observations(observations, today)
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

    def test_rejects_mis_scaled_nominal_gdp(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_complete_observations(
            observations,
            today,
            {"values": {"nominal_gdp": 30_000_000.0}},
        )

        errors = validate_observations(observations, today=today)

        assert any("nominal_gdp" in error and "scale" in error for error in errors)

    def test_requires_core_pce_rstar_nominal_gdp_and_daily_corroboration(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        _write_observations(observations, today)

        errors = validate_observations(observations, today=today)

        assert any("core_pce" in error for error in errors)
        assert any("rstar" in error for error in errors)
        assert any("nominal_gdp" in error for error in errors)
        assert any("iorb" in error for error in errors)
        assert any("sofr" in error for error in errors)

    def test_checks_source_health_when_a_health_file_is_supplied(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        health = self.tmp_path / "source_health.csv"
        _write_complete_observations(observations, today)
        pd.DataFrame([
            {
                "fetch_key": "rstar",
                "status": "ERROR",
                "is_stale": True,
                "observation_time": str(today),
            }
        ]).to_csv(health, index=False)

        errors = validate_observations(observations, today=today, source_health_path=health)

        assert any("rstar" in error and "source health" in error for error in errors)

    def test_rejects_source_health_file_without_fetch_keys(self):
        today = date(2026, 7, 27)
        observations = self.tmp_path / "observations.csv"
        health = self.tmp_path / "source_health.csv"
        _write_complete_observations(observations, today)
        pd.DataFrame([{"status": "CURRENT"}]).to_csv(health, index=False)

        errors = validate_observations(observations, today=today, source_health_path=health)

        assert any("source health" in error for error in errors)

    def test_accepts_administered_rate_up_to_four_days_in_future(self):
        today = date(2026, 8, 16)
        observations = self.tmp_path / "observations.csv"
        _write_complete_observations(observations, today, {"iorb": today + timedelta(days=3)})

        errors = validate_observations(observations, today=today)

        self.assertFalse(any("iorb" in error and "future" in error for error in errors))

    def test_rejects_truly_future_observation(self):
        today = date(2026, 8, 16)
        observations = self.tmp_path / "observations.csv"
        _write_complete_observations(observations, today, {"iorb": today + timedelta(days=10)})

        errors = validate_observations(observations, today=today)

        self.assertTrue(any("iorb" in error and "future" in error for error in errors))

    def test_rejects_stale_quarterly_and_monthly_series(self):
        today = date(2026, 8, 16)
        observations = self.tmp_path / "observations.csv"
        _write_complete_observations(
            observations,
            today,
            {
                "nominal_gdp": today - timedelta(days=245),
                "core_pce": today - timedelta(days=105),
                "rstar": today - timedelta(days=275),
            },
        )

        errors = validate_observations(observations, today=today)

        self.assertTrue(any("nominal_gdp" in error and "stale" in error for error in errors))
        self.assertTrue(any("core_pce" in error and "stale" in error for error in errors))
        self.assertTrue(any("rstar" in error and "stale" in error for error in errors))
