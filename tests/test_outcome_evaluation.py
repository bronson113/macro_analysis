"""Behavior tests for prospective signal outcome evaluation."""

import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from analyzer import MacroAnalyzer
from main import run_evaluation
from outcome_evaluation import SignalRecord, evaluate_signals
from recommendations import SectorEvidenceEngine
from storage import MacroStorage


def signal(**overrides):
    """Return one canonical prospective signal, with explicit overrides."""
    record = {
        "signal_date": "2026-01-02",
        "sector_group": "Technology (XLK)",
        "instrument": "XLK",
        "benchmark": "SPY",
        "posture": "WATCH",
        "score": 4.0,
        "score_range": [2.0, 6.0],
        "coverage_pct": 85.0,
        "factor_snapshot": {"positive_factors": [{"factor_id": "liquidity"}]},
    }
    record.update(overrides)
    return record


class TestOutcomeEvaluation(unittest.TestCase):
    def test_forward_return_starts_after_signal_and_subtracts_benchmark_and_cost(self):
        prices = {
            "XLK": [("2026-01-02", 100.0), ("2026-02-02", 110.0)],
            "SPY": [("2026-01-02", 200.0), ("2026-02-02", 210.0)],
        }

        result = evaluate_signals([signal()], prices, horizons=(1,), transaction_cost_bps=10)

        row = result["outcomes"][0]
        self.assertEqual(row["asset_return_pct"], 10.0)
        self.assertEqual(row["benchmark_return_pct"], 5.0)
        self.assertEqual(row["net_excess_return_pct"], 4.9)
        self.assertEqual(row["transaction_cost_bps"], 10)

    def test_entry_and_horizon_prices_never_precede_the_signal_or_target(self):
        prices = {
            "XLK": [
                ("2026-01-01", 50.0),
                ("2026-01-05", 100.0),
                ("2026-01-06", 110.0),
            ],
            "SPY": [
                ("2026-01-01", 100.0),
                ("2026-01-05", 100.0),
                ("2026-01-06", 100.0),
            ],
        }

        result = evaluate_signals([signal()], prices, horizons=(1,), transaction_cost_bps=0)

        row = result["outcomes"][0]
        self.assertEqual(row["entry_date"], "2026-01-05")
        self.assertEqual(row["outcome_date"], "2026-01-06")
        self.assertEqual(row["asset_return_pct"], 10.0)

    def test_asset_and_benchmark_returns_share_one_post_horizon_observation_date(self):
        prices = {
            "XLK": [
                ("2026-01-02", 100.0),
                ("2026-01-05", 110.0),
                ("2026-01-07", 120.0),
            ],
            "SPY": [
                ("2026-01-02", 100.0),
                ("2026-01-06", 105.0),
                ("2026-01-07", 106.0),
            ],
        }

        result = evaluate_signals([signal()], prices, horizons=(1,), transaction_cost_bps=0)

        row = result["outcomes"][0]
        self.assertEqual(row["outcome_date"], "2026-01-07")
        self.assertEqual(row["asset_return_pct"], 20.0)
        self.assertEqual(row["benchmark_return_pct"], 6.0)

    def test_horizon_counts_observed_market_sessions_not_weekdays(self):
        prices = {
            "XLK": [
                ("2026-05-22", 100.0),  # Friday before Memorial Day.
                ("2026-05-26", 101.0),
                ("2026-05-27", 102.0),
            ],
            "SPY": [
                ("2026-05-22", 100.0),
                ("2026-05-26", 100.0),
                ("2026-05-27", 100.0),
            ],
        }

        result = evaluate_signals(
            [signal(signal_date="2026-05-22")], prices, horizons=(2,), transaction_cost_bps=0
        )

        row = result["outcomes"][0]
        self.assertEqual(row["outcome_date"], "2026-05-27")
        self.assertEqual(row["asset_return_pct"], 2.0)

    def test_synthetic_basket_rebases_at_each_signal_entry_with_equal_weights(self):
        prices = {
            "AAA": [
                ("2025-01-02", 100.0),
                ("2025-01-03", 200.0),
                ("2025-01-06", 200.0),
                ("2025-01-07", 220.0),
            ],
            "BBB": [
                ("2025-01-02", 100.0),
                ("2025-01-03", 50.0),
                ("2025-01-06", 50.0),
                ("2025-01-07", 60.0),
            ],
            "SPY": [
                ("2025-01-02", 100.0),
                ("2025-01-03", 100.0),
                ("2025-01-06", 100.0),
                ("2025-01-07", 100.0),
            ],
        }
        older = signal(
            signal_date="2025-01-02",
            sector_group="Older basket",
            instrument="AAA/BBB",
        )
        later = signal(
            signal_date="2025-01-06",
            sector_group="Later basket",
            instrument="AAA/BBB",
        )

        later_only = evaluate_signals([later], prices, horizons=(1,), transaction_cost_bps=0)
        with_older_history = evaluate_signals(
            [older, later], prices, horizons=(1,), transaction_cost_bps=0
        )
        later_only_row = later_only["outcomes"][0]
        later_history_row = next(
            row for row in with_older_history["outcomes"] if row["sector_group"] == "Later basket"
        )

        self.assertEqual(later_only_row["entry_date"], "2025-01-06")
        self.assertEqual(later_only_row["asset_return_pct"], 15.0)
        self.assertEqual(later_history_row["asset_return_pct"], 15.0)
        self.assertEqual(
            later_only_row["basket_entry_weights"], {"AAA": 0.5, "BBB": 0.5}
        )

    def test_drawdown_score_band_and_posture_summary_use_the_matured_path(self):
        prices = {
            "XLK": [
                ("2025-01-02", 100.0),
                ("2025-01-03", 110.0),
                ("2025-01-06", 90.0),
                ("2025-01-07", 105.0),
            ],
            "SPY": [
                ("2025-01-02", 100.0),
                ("2025-01-03", 100.0),
                ("2025-01-06", 100.0),
                ("2025-01-07", 100.0),
            ],
        }

        result = evaluate_signals(
            [signal(signal_date="2025-01-02")], prices, horizons=(3,), transaction_cost_bps=0
        )

        row = result["outcomes"][0]
        self.assertAlmostEqual(row["max_drawdown_pct"], -18.1818, places=4)
        self.assertEqual(row["score_band"], 4)
        grouped = result["summary"]["by_horizon"]["3"]["by_posture"]["WATCH"]
        self.assertEqual(grouped["sample_size"], 1)
        self.assertEqual(grouped["hit_rate_pct"], 100.0)
        self.assertEqual(grouped["mean_net_excess_return_pct"], 5.0)
        self.assertEqual(grouped["by_score_band"]["4"]["sample_size"], 1)

    def test_avoid_hit_rate_requires_negative_net_excess_return(self):
        prices = {
            "XLF": [("2025-01-02", 100.0), ("2025-01-03", 95.0)],
            "SPY": [("2025-01-02", 100.0), ("2025-01-03", 100.0)],
        }
        avoid = signal(
            signal_date="2025-01-02",
            sector_group="Financials (XLF)",
            instrument="XLF",
            posture="AVOID",
            score=-4.0,
        )

        result = evaluate_signals([avoid], prices, horizons=(1,), transaction_cost_bps=0)

        row = result["outcomes"][0]
        self.assertTrue(row["hit"])
        self.assertEqual(result["summary"]["by_horizon"]["1"]["by_posture"]["AVOID"]["hit_rate_pct"], 100.0)

    def test_unmatured_horizon_is_excluded_and_labeled_insufficient(self):
        prices = {
            "XLK": [("2026-01-02", 100.0), ("2026-01-05", 101.0)],
            "SPY": [("2026-01-02", 100.0), ("2026-01-05", 101.0)],
        }

        result = evaluate_signals([signal()], prices, horizons=(252,))

        self.assertEqual(result["outcomes"], [])
        self.assertEqual(result["summary"]["status"], "INSUFFICIENT_SAMPLE")
        self.assertEqual(result["summary"]["sample_size"], 0)

    def test_small_sample_remains_insufficient_even_when_outcomes_are_positive(self):
        prices = {
            "XLK": [("2025-01-02", 100.0), ("2025-01-03", 101.0)],
            "SPY": [("2025-01-02", 100.0), ("2025-01-03", 100.0)],
        }

        result = evaluate_signals(
            [signal(signal_date="2025-01-02")], prices, horizons=(1,), transaction_cost_bps=0
        )

        self.assertEqual(result["summary"]["status"], "INSUFFICIENT_SAMPLE")
        self.assertEqual(result["summary"]["sample_size"], 1)
        self.assertLess(result["summary"]["elapsed_days"], 365)

    def test_signal_record_round_trips_stable_factor_and_uncertainty_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = MacroStorage(
                indicators_csv=root / "indicators.csv",
                observations_csv=root / "observations.csv",
                snapshots_csv=root / "snapshots.csv",
                news_csv=root / "news.csv",
                run_logs_csv=root / "runs.csv",
                signals_csv=root / "signals.csv",
            )
            assessment = signal(
                factor_snapshot={"b": 2, "a": 1}, score_range=[1.0, 5.0]
            )

            saved = storage.save_signal_assessments([assessment])
            stored = storage.get_signal_assessments()

            self.assertEqual(saved, 1)
            self.assertEqual(stored[0]["factor_snapshot"], {"a": 1, "b": 2})
            self.assertEqual(stored[0]["uncertainty"], [1.0, 5.0])
            with (root / "signals.csv").open(newline="", encoding="utf-8") as handle:
                raw = next(csv.DictReader(handle))
            self.assertEqual(raw["factor_snapshot_json"], '{"a":1,"b":2}')
            self.assertEqual(raw["uncertainty_json"], "[1.0,5.0]")

    def test_default_ledger_path_follows_injected_storage_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = MacroStorage(
                indicators_csv=root / "indicators.csv",
                observations_csv=root / "observations.csv",
                snapshots_csv=root / "snapshots.csv",
                news_csv=root / "news.csv",
                run_logs_csv=root / "runs.csv",
            )

            storage.save_signal_assessments([signal()])

            self.assertEqual(Path(storage.signals_csv), root / "signal_assessments.csv")
            self.assertTrue((root / "signal_assessments.csv").exists())

    def test_ledger_fallback_snapshot_preserves_the_complete_assessment_factors(self):
        assessment = SectorEvidenceEngine().generate_assessments(
            summary={
                "date": "2026-01-02",
                "liquidity_regime": "Expanding (+30d)",
                "treasury_10y": 4.6,
                "breakeven_10y": 2.1,
                "housing_yoy": -12.0,
            },
            credit={"high_yield_oas": 3.0},
            valuations=[{"sector": "Technology (XLK)", "history": {"percentile": 20.0}}],
            ai_ecosystem=[],
            news_events=[],
            macro_situation={
                "quality": "OK",
                "name": "Fixture",
                "favored_sectors": ["Technology (XLK)"],
                "disfavored_sectors": [],
            },
        )[0]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = MacroStorage(
                indicators_csv=root / "indicators.csv",
                observations_csv=root / "observations.csv",
                snapshots_csv=root / "snapshots.csv",
                news_csv=root / "news.csv",
                run_logs_csv=root / "runs.csv",
                signals_csv=root / "signals.csv",
            )

            storage.save_signal_assessments([assessment])
            factor_snapshot = storage.get_signal_assessments()[0]["factor_snapshot"]

            self.assertTrue({
                "positive_factors", "negative_factors", "neutral_factors",
                "missing_evidence", "factors", "methodology", "as_of_date",
            } <= set(factor_snapshot))
            self.assertEqual(factor_snapshot["factors"], assessment["factors"])

    def test_same_day_rerun_preserves_the_first_prospective_assessment(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = MacroStorage(
                indicators_csv=root / "indicators.csv",
                observations_csv=root / "observations.csv",
                snapshots_csv=root / "snapshots.csv",
                news_csv=root / "news.csv",
                run_logs_csv=root / "runs.csv",
                signals_csv=root / "signals.csv",
            )

            first_saved = storage.save_signal_assessments([signal(score=4.0)])
            duplicate_saved = storage.save_signal_assessments([signal(score=-4.0)])
            records = storage.get_signal_assessments()

            self.assertEqual(first_saved, 1)
            self.assertEqual(duplicate_saved, 0)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["score"], 4.0)

    def test_signal_record_preserves_the_public_ledger_fields(self):
        record = SignalRecord.from_mapping(signal())

        self.assertEqual(record.instrument, "XLK")
        self.assertEqual(record.benchmark, "SPY")
        self.assertEqual(record.to_mapping()["signal_date"], "2026-01-02")

    def test_snapshot_appends_current_assessments_to_the_prospective_ledger(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = MacroStorage(
                indicators_csv=root / "indicators.csv",
                observations_csv=root / "observations.csv",
                snapshots_csv=root / "snapshots.csv",
                news_csv=root / "news.csv",
                run_logs_csv=root / "runs.csv",
                signals_csv=root / "signals.csv",
            )
            analyzer = MacroAnalyzer(storage)
            analyzer.calculate_net_liquidity = lambda: {
                "net_liquidity": 1.0,
                "fed_assets_billion": 2.0,
                "tga_billion": 0.5,
                "rrp_billion": 0.5,
                "change_30d_billion": 1.0,
                "m2_yoy": 2.0,
                "quality": "OK",
            }
            analyzer.analyze_yield_curve = lambda: {
                "treasury_10y": 4.0,
                "treasury_2y": 3.0,
                "spread_10y_2y": 1.0,
                "regime": "Normal",
            }
            analyzer.analyze_policy_stance = lambda: {
                "policy_stance": "CUTTING",
                "policy_rate": 4.0,
                "policy_rate_change_30d": -0.25,
                "real_yield_10y": 2.0,
            }
            analyzer.analyze_credit_markets = lambda: {
                "high_yield_oas": 3.0,
                "regime": "Normal",
            }
            analyzer.analyze_market_sentiment = lambda: {
                "vix": 15.0,
                "dxy": 100.0,
                "sp500": 5000.0,
                "cnn_fear_greed_index": None,
                "shiller_pe": None,
            }
            analyzer.analyze_labor_and_inflation = lambda: {
                "unemployment_rate": 4.0,
                "cpi_yoy": 2.0,
                "housing_yoy": 1.0,
                "breakeven_10y": 2.0,
                "sahm_rule_triggered": False,
            }
            analyzer.news_analyzer.get_major_event_summary = lambda limit: []
            analyzer.valuation_engine.calculate_sector_valuations = lambda: []
            analyzer.valuation_engine.save_valuations_to_storage = lambda values: None
            analyzer.ai_tracker.analyze_ecosystem_valuations = lambda: []
            analyzer.matrix_engine.classify_situation = lambda *args: {
                "name": "Fixture",
                "rates_label": "Cutting",
                "bs_label": "Expanding",
            }
            analyzer.evidence_engine.generate_assessments = lambda *args: [signal()]
            analyzer.raw_engine.build_raw_payload = lambda **kwargs: {}
            analyzer.mechanical_analyst.analyze_raw_payload = lambda payload: {}

            analysis = analyzer.generate_full_snapshot()
            records = storage.get_signal_assessments()

            self.assertEqual(len(analysis["evidence_assessments"]), 1)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["sector_group"], "Technology (XLK)")
            self.assertEqual(records[0]["signal_date"], analysis["summary"]["date"])

    def test_evaluation_runner_loads_ledger_and_atomically_writes_result(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = MacroStorage(
                indicators_csv=root / "indicators.csv",
                observations_csv=root / "observations.csv",
                snapshots_csv=root / "snapshots.csv",
                news_csv=root / "news.csv",
                run_logs_csv=root / "runs.csv",
                signals_csv=root / "signals.csv",
            )
            storage.save_signal_assessments([signal(signal_date="2025-01-02")])
            dates = []
            current = date(2025, 1, 2)
            while len(dates) < 22:
                if current.weekday() < 5:
                    dates.append(current)
                current += timedelta(days=1)
            expected_prices = {
                "XLK": [(day.isoformat(), 100.0 + index) for index, day in enumerate(dates)],
                "SPY": [(day.isoformat(), 100.0 + index / 2) for index, day in enumerate(dates)],
            }
            destination = root / "outcome_evaluation.json"
            loader = unittest.mock.Mock(return_value=expected_prices)

            result = run_evaluation(
                storage=storage, output_path=destination, price_loader=loader
            )

            loader.assert_called_once()
            self.assertTrue(destination.exists())
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), result)
            self.assertEqual(result["summary"]["sample_size"], 1)
