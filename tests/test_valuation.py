"""Regression tests for aggregate sector valuation calculations."""

import unittest

import pandas as pd

from valuation import SectorValuationEngine, aggregate_sector_fundamentals


class FakeStorage:
    """In-memory valuation history with the same read contract as MacroStorage."""

    def __init__(self, values, day_spacing=1):
        start = pd.Timestamp("2026-01-01")
        self.series = pd.DataFrame([
            {"date": start + pd.Timedelta(days=index * day_spacing), "value": value}
            for index, value in enumerate(values)
        ])

    def get_indicator_series(self, indicator_key, limit=365):
        return self.series.tail(limit).copy()


class RecordingStorage:
    """Captures valuation writes without relying on the file-backed storage layer."""

    def __init__(self):
        self.saved_observations = {}

    def save_observations(self, indicator_key, observations):
        self.saved_observations[indicator_key] = observations.to_dict("records")


class TestAggregateSectorFundamentals(unittest.TestCase):
    def test_aggregate_multiples_use_implied_fundamentals_not_mean_ratios(self):
        """Large constituents must contribute proportionally to aggregate earnings."""
        result = aggregate_sector_fundamentals([
            {
                "ticker": "A",
                "marketCap": 900.0,
                "enterpriseValue": 1000.0,
                "trailingPE": 30.0,
                "forwardPE": 18.0,
                "enterpriseToEbitda": 10.0,
            },
            {
                "ticker": "B",
                "marketCap": 100.0,
                "enterpriseValue": 120.0,
                "trailingPE": 10.0,
                "forwardPE": 10.0,
                "enterpriseToEbitda": 6.0,
            },
        ])

        self.assertEqual(result["trailing_pe"], 25.0)
        self.assertEqual(result["forward_pe"], 16.67)
        self.assertEqual(result["ev_ebitda"], 9.33)
        self.assertEqual(result["coverage"]["forward_pe_pct"], 100.0)

    def test_negative_and_missing_denominators_reduce_coverage_instead_of_entering_ratio(self):
        """Loss-making or unavailable estimates must not distort valid aggregate earnings."""
        result = aggregate_sector_fundamentals([
            {"ticker": "A", "marketCap": 80.0, "forwardPE": 20.0},
            {"ticker": "LOSS", "marketCap": 20.0, "forwardPE": -5.0},
        ])

        self.assertEqual(result["forward_pe"], 20.0)
        self.assertEqual(result["coverage"]["forward_pe_pct"], 80.0)
        self.assertEqual(result["coverage"]["excluded_forward_pe"], ["LOSS"])


class TestHistoricalValuationClassification(unittest.TestCase):
    def test_history_classification_refuses_short_samples(self):
        """Three recent observations cannot establish a sector valuation range."""
        storage = FakeStorage([10.0, 11.0, 12.0])

        result = SectorValuationEngine(storage).classify_history(
            "Technology (XLK)", "forward_pe", 15.0
        )

        self.assertEqual(result, {
            "status": "Insufficient History",
            "percentile": None,
            "sample_size": 3,
            "span_days": 2,
        })

    def test_history_classification_refuses_dense_samples_without_time_span(self):
        """Sixty closely spaced samples still lack the required six-month context."""
        storage = FakeStorage(list(range(10, 70)), day_spacing=3)

        result = SectorValuationEngine(storage).classify_history(
            "Technology (XLK)", "forward_pe", 15.0
        )

        self.assertEqual(result, {
            "status": "Insufficient History",
            "percentile": None,
            "sample_size": 60,
            "span_days": 177,
        })

    def test_history_classification_uses_percentile_not_fixed_fair_multiple(self):
        """A value near the top of a long history must be rich despite any fixed norm."""
        storage = FakeStorage(list(range(10, 70)), day_spacing=4)

        result = SectorValuationEngine(storage).classify_history(
            "Technology (XLK)", "forward_pe", 65.0
        )

        self.assertEqual(result["status"], "Rich Historical Range")
        self.assertGreaterEqual(result["percentile"], 75.0)


class TestValuationPersistence(unittest.TestCase):
    def test_save_valuations_persists_each_available_aggregate_multiple(self):
        """All three aggregate series must be available for future history checks."""
        storage = RecordingStorage()
        engine = SectorValuationEngine(storage)

        engine.save_valuations_to_storage([{
            "sector": "Technology (XLK)",
            "trailing_pe": 25.0,
            "forward_pe": 16.67,
            "ev_ebitda": 9.33,
        }])

        self.assertEqual(set(storage.saved_observations), {
            "val_v2_trailing_pe_xlk",
            "val_v2_forward_pe_xlk",
            "val_v2_ev_ebitda_xlk",
        })
        self.assertEqual(
            storage.saved_observations["val_v2_trailing_pe_xlk"][0]["value"], 25.0
        )

    def test_save_valuations_keeps_consumer_sector_histories_distinct(self):
        """Consumer Discretionary and Staples must not overwrite each other's history."""
        storage = RecordingStorage()
        engine = SectorValuationEngine(storage)

        engine.save_valuations_to_storage([
            {
                "sector": "Consumer Discretionary (XLY)",
                "forward_pe": 20.0,
            },
            {
                "sector": "Consumer Staples (XLP)",
                "forward_pe": 15.0,
            },
        ])

        self.assertEqual(
            storage.saved_observations["val_v2_forward_pe_xly"][0]["value"], 20.0
        )
        self.assertEqual(
            storage.saved_observations["val_v2_forward_pe_xlp"][0]["value"], 15.0
        )
