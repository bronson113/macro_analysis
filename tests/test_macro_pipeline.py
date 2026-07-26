"""
Unit and Integration Test Suite for Defiant Gatekeeper Macro Analysis Pipeline.
Verifies 100% data trust, defensive error handling, matrix classification,
single-stock dispersion detection, and report rendering safety.
"""

import os
import json
import unittest
import tempfile
import contextlib
import io
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from storage import MacroStorage
from fetcher import MacroFetcher
from analyzer import MacroAnalyzer
from valuation import SectorValuationEngine
from ai_ecosystem import AIRoboticsEcosystemTracker
from macro_matrix import MacroMatrixEngine
from llm_analyst import DynamicMacroAnalyst
from raw_data_engine import RawDataEngine
from reporter import MacroReporter


class TestMacroPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.tmp_path = Path(cls._tmpdir.name)
        cls.storage = MacroStorage(cls.tmp_path / "macro_test.db")
        cls.analyzer = MacroAnalyzer(cls.storage)
        cls.matrix_engine = MacroMatrixEngine()
        cls.llm_analyst = DynamicMacroAnalyst(cls.storage)
        cls.raw_engine = RawDataEngine(cls.storage, output_dir=cls.tmp_path / "raw_output", verbose=False)
        cls.reporter = MacroReporter(cls.storage, cls.analyzer, output_dir=cls.tmp_path / "report_output", verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def test_01_storage_observations(self):
        """Test observation saving and retrieval from SQLite storage."""
        test_df = pd.DataFrame([
            {"date": "2026-07-01", "value": 100.5},
            {"date": "2026-07-02", "value": 101.2}
        ])
        count = self.storage.save_observations("test_metric", test_df)
        self.assertGreaterEqual(count, 2)
        
        latest = self.storage.get_latest_observation("test_metric")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["value"], 101.2)

    def test_01b_fred_fetch_keeps_ten_year_history_window(self):
        """FRED backfill should retain observations inside the dashboard's 10-year window."""
        class FakeResponse:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return self.body.encode("utf-8")

        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            fetcher = MacroFetcher(storage)
            inside_window = (datetime.now() - timedelta(days=365 * 8)).strftime("%Y-%m-%d")
            outside_window = (datetime.now() - timedelta(days=365 * 11)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")
            csv_body = "\n".join([
                "DATE,TEST",
                f"{outside_window},1.0",
                f"{inside_window},2.0",
                f"{today},3.0",
            ])

            with patch("fetcher.urllib.request.urlopen", return_value=FakeResponse(csv_body)):
                count, err = fetcher.fetch_fred_series("test_fred", {"id": "TEST"})

            series = storage.get_indicator_series("test_fred", limit=5000)

        self.assertIsNone(err)
        self.assertEqual(count, 2)
        self.assertIn(inside_window, set(series["date"].dt.strftime("%Y-%m-%d")))
        self.assertNotIn(outside_window, set(series["date"].dt.strftime("%Y-%m-%d")))

    def test_01c_cpi_fetch_keeps_extra_year_for_yoy_dashboard_history(self):
        """CPI needs one extra source year so CPI YoY covers the full 10-year dashboard."""
        class FakeResponse:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return self.body.encode("utf-8")

        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            fetcher = MacroFetcher(storage)
            extra_year_date = (datetime.now() - timedelta(days=365 * 10 + 180)).strftime("%Y-%m-%d")
            too_old_date = (datetime.now() - timedelta(days=365 * 12)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")
            csv_body = "\n".join([
                "DATE,CPIAUCSL",
                f"{too_old_date},100.0",
                f"{extra_year_date},110.0",
                f"{today},120.0",
            ])

            with patch("fetcher.urllib.request.urlopen", return_value=FakeResponse(csv_body)):
                count, err = fetcher.fetch_fred_series("cpi", {"id": "CPIAUCSL"})

            series = storage.get_indicator_series("cpi", limit=5000)

        self.assertIsNone(err)
        self.assertEqual(count, 2)
        self.assertIn(extra_year_date, set(series["date"].dt.strftime("%Y-%m-%d")))
        self.assertNotIn(too_old_date, set(series["date"].dt.strftime("%Y-%m-%d")))

    def test_02_macro_matrix_classification(self):
        """Test all 4 quadrants of the Defiant Gatekeeper Macro Matrix."""
        # Quadrant 1: Rates Cutting + Balance Sheet Expanding
        q1 = self.matrix_engine.classify_situation("CUTTING", 50.0, 2.5, False, -0.50)
        self.assertEqual(q1["situation_id"], 1)
        self.assertIn("RESERVE LIQUIDITY EXPANSION", q1["name"])

        # Quadrant 2: Rates Cutting + Balance Sheet Contracting
        q2 = self.matrix_engine.classify_situation("CUTTING", -50.0, 2.5, True, 0.10)
        self.assertEqual(q2["situation_id"], 2)
        self.assertIn("LATE CYCLE", q2["name"])

        # Quadrant 3: Rates Raising + Balance Sheet Contracting
        q3 = self.matrix_engine.classify_situation("HAWKISH", -50.0, 2.5, False, -0.50)
        self.assertEqual(q3["situation_id"], 3)
        self.assertIn("RESTRICTIVE POLICY", q3["name"])

        # Quadrant 4: Rates Raising + Balance Sheet Expanding
        q4 = self.matrix_engine.classify_situation("HAWKISH", 50.0, 4.5, False, -0.50)
        self.assertEqual(q4["situation_id"], 4)
        self.assertIn("RESERVE LIQUIDITY EXPANSION", q4["name"])

    def test_03_net_liquidity_calculation(self):
        """Test Fed Net Liquidity formula (Assets - TGA - RRP)."""
        liq = self.analyzer.calculate_net_liquidity()
        self.assertIn("net_liquidity", liq)
        if liq["net_liquidity"] is not None:
            self.assertIsInstance(liq["net_liquidity"], float)
            self.assertGreater(liq["net_liquidity"], 0)

    def test_03b_net_liquidity_requires_all_components(self):
        """Net liquidity should not be reported when TGA or RRP are missing."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("fed_total_assets", pd.DataFrame([
                {"date": "2026-07-15", "value": 6743028.0}
            ]))

            liq = MacroAnalyzer(storage).calculate_net_liquidity()

        self.assertIsNone(liq["net_liquidity"])
        self.assertIn("tga_balance", liq["missing_components"])
        self.assertIn("reverse_repo", liq["missing_components"])
        self.assertEqual(liq["quality"], "INSUFFICIENT_DATA")

    def test_03c_net_liquidity_uses_roughly_30_day_delta(self):
        """30-day liquidity change should compare against the nearest 30-day history point."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("fed_total_assets", pd.DataFrame([
                {"date": "2026-01-01", "value": 6000000.0},
                {"date": "2026-06-15", "value": 6500000.0},
                {"date": "2026-07-15", "value": 6743028.0},
            ]))
            storage.save_observations("tga_balance", pd.DataFrame([
                {"date": "2026-01-01", "value": 900000.0},
                {"date": "2026-06-15", "value": 956502.0},
                {"date": "2026-07-15", "value": 795976.0},
            ]))
            storage.save_observations("reverse_repo", pd.DataFrame([
                {"date": "2026-01-01", "value": 10.0},
                {"date": "2026-06-15", "value": 6.828},
                {"date": "2026-07-15", "value": 0.151},
            ]))

            liq = MacroAnalyzer(storage).calculate_net_liquidity()

        expected_current = 6743028.0 / 1000.0 - 795976.0 / 1000.0 - 0.151
        expected_prior = 6500000.0 / 1000.0 - 956502.0 / 1000.0 - 6.828
        self.assertAlmostEqual(liq["net_liquidity"], round(expected_current, 2))
        self.assertAlmostEqual(liq["change_30d_billion"], round(expected_current - expected_prior, 2))

    def test_03d_policy_stance_uses_policy_rate_trend_not_yield_curve(self):
        """A positive yield curve alone must not be treated as Fed easing."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("dff", pd.DataFrame([
                {"date": "2026-06-15", "value": 3.63},
                {"date": "2026-07-15", "value": 3.63},
            ]))

            stance = MacroAnalyzer(storage).analyze_policy_stance()

        self.assertEqual(stance["policy_stance"], "HOLDING")
        self.assertEqual(stance["rate_trend"], "NEUTRAL")

    def test_03f_flat_policy_rate_can_be_restrictive_when_real_yields_are_high(self):
        """Holding policy should be classified as restrictive only with real-yield evidence."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("dff", pd.DataFrame([
                {"date": "2026-06-15", "value": 4.75},
                {"date": "2026-07-15", "value": 4.75},
            ]))
            storage.save_observations("treasury_10y", pd.DataFrame([
                {"date": "2026-07-15", "value": 4.60},
            ]))
            storage.save_observations("breakeven_10y", pd.DataFrame([
                {"date": "2026-07-15", "value": 2.10},
            ]))

            stance = MacroAnalyzer(storage).analyze_policy_stance()

        self.assertEqual(stance["policy_stance"], "HOLDING_RESTRICTIVE")
        self.assertEqual(stance["rate_trend"], "RESTRICTIVE")
        self.assertAlmostEqual(stance["real_yield_10y"], 2.5)

    def test_03e_macro_matrix_returns_insufficient_data_regime(self):
        """The matrix should not force a quadrant when rate or liquidity trend is missing."""
        res = self.matrix_engine.classify_situation(None, None, None, False, None)

        self.assertEqual(res["situation_id"], 0)
        self.assertEqual(res["quality"], "INSUFFICIENT_DATA")
        self.assertEqual(res["favored_sectors"], [])

    def test_03g_holding_neutral_with_expanding_liquidity_is_no_actionable_quadrant(self):
        """A non-restrictive policy hold should not be forced into the hawkish quadrants."""
        res = self.matrix_engine.classify_situation("HOLDING", 25.0, 2.4, False, 0.25)

        self.assertEqual(res["situation_id"], 0)
        self.assertEqual(res["quality"], "INSUFFICIENT_DATA")

    def test_04_raw_payload_generation(self):
        """Test un-hardcoded raw data JSON payload generation."""
        self.raw_engine.fetch_individual_stock_metrics = lambda: [
            {"ticker": f"T{i}", "name": f"Test {i}", "group": "Fixture", "price": 100.0, "forward_pe": 10.0 + i, "ev_ebitda": 8.0 + i}
            for i in range(11)
        ]
        payload = self.raw_engine.build_raw_payload()
        self.assertIn("metadata", payload)
        self.assertIn("macro_quantitative", payload)
        self.assertIn("individual_stock_constituents", payload)
        self.assertGreater(len(payload["individual_stock_constituents"]), 10)
        self.assertTrue((self.tmp_path / "raw_output" / "latest_raw_payload.json").exists())

    def test_04b_raw_payload_saves_current_stock_sector_relative_multiples(self):
        """Raw stock collection should persist relative multiple observations for future history."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            raw_engine = RawDataEngine(storage, output_dir=self.tmp_path / "raw_relative_output", verbose=False)
            raw_engine.fetch_individual_stock_metrics = lambda: [
                {"ticker": "NVDA", "name": "Nvidia", "group": "Tech", "price": 125.0, "forward_pe": 39.0, "ev_ebitda": 30.0},
                {"ticker": "AMD", "name": "AMD", "group": "Tech", "price": 160.0, "forward_pe": 39.0, "ev_ebitda": 28.0},
                {"ticker": "MU", "name": "Micron", "group": "Tech", "price": 95.0, "forward_pe": 12.0, "ev_ebitda": 10.0},
            ]

            raw_engine.build_raw_payload()
            latest_fpe = storage.get_latest_observation("stock_rel_fpe_tech_mu")
            latest_eve = storage.get_latest_observation("stock_rel_eve_tech_mu")

        self.assertIsNotNone(latest_fpe)
        self.assertAlmostEqual(latest_fpe["value"], 12.0 / 30.0)
        self.assertIsNotNone(latest_eve)
        self.assertAlmostEqual(latest_eve["value"], 10.0 / (68.0 / 3.0))

    def test_05_single_stock_lagging_detection(self):
        """Test single-stock peer lag detection in LLM analyst."""
        mock_payload = {
            "macro_quantitative": {"fed_total_assets": {"value": 7000000.0}},
            "recent_news_events": [],
            "individual_stock_constituents": [
                {"ticker": "NVDA", "name": "Nvidia", "group": "Tech", "price": 125.0, "forward_pe": 35.0, "ev_ebitda": 30.0, "dist_from_52w_high_pct": -5.0},
                {"ticker": "AMD", "name": "AMD", "group": "Tech", "price": 160.0, "forward_pe": 32.0, "ev_ebitda": 28.0, "dist_from_52w_high_pct": -8.0},
                {"ticker": "MU", "name": "Micron", "group": "Tech", "price": 95.0, "forward_pe": 12.0, "ev_ebitda": 10.0, "dist_from_52w_high_pct": -25.0}
            ]
        }
        res = self.llm_analyst.analyze_raw_payload(mock_payload)
        lags = res["single_stock_lagging_opportunities"]
        self.assertGreaterEqual(len(lags), 1)
        self.assertEqual(lags[0]["ticker"], "MU")
        self.assertIn("Lagging Value", lags[0]["action"])

    def test_05a_peer_discount_must_be_cheap_vs_historical_relative_norm(self):
        """A structurally low-multiple stock should not be flagged just for trading below peers."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("stock_rel_fpe_tech_mu", pd.DataFrame([
                {"date": "2026-07-01", "value": 0.39},
                {"date": "2026-07-08", "value": 0.40},
                {"date": "2026-07-15", "value": 0.41},
            ]))
            analyst = DynamicMacroAnalyst(storage)
            mock_payload = {
                "macro_quantitative": {"fed_total_assets": {"value": 7000000.0}},
                "recent_news_events": [],
                "individual_stock_constituents": [
                    {"ticker": "NVDA", "name": "Nvidia", "group": "Tech", "price": 125.0, "forward_pe": 39.0, "ev_ebitda": 30.0, "dist_from_52w_high_pct": -5.0},
                    {"ticker": "AMD", "name": "AMD", "group": "Tech", "price": 160.0, "forward_pe": 39.0, "ev_ebitda": 28.0, "dist_from_52w_high_pct": -8.0},
                    {"ticker": "MU", "name": "Micron", "group": "Tech", "price": 95.0, "forward_pe": 12.0, "ev_ebitda": 10.0, "dist_from_52w_high_pct": -25.0}
                ]
            }

            res = analyst.analyze_raw_payload(mock_payload)

        lags = res["single_stock_lagging_opportunities"]
        self.assertEqual(lags, [])
        mu_summary = next(s for s in res["sector_dispersion"] if s["group"] == "Tech")["constituent_relative_valuation"][0]
        self.assertEqual(mu_summary["ticker"], "MU")
        self.assertEqual(mu_summary["relative_valuation_status"], "Fair vs Historical Sector Relationship")

    def test_05a2_relative_discount_flags_when_current_ratio_is_below_history(self):
        """A stock should be flagged when it is cheap versus its own normal sector relationship."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("stock_rel_fpe_tech_mu", pd.DataFrame([
                {"date": "2026-07-01", "value": 0.70},
                {"date": "2026-07-08", "value": 0.72},
                {"date": "2026-07-15", "value": 0.68},
            ]))
            analyst = DynamicMacroAnalyst(storage)
            mock_payload = {
                "macro_quantitative": {"fed_total_assets": {"value": 7000000.0}},
                "recent_news_events": [],
                "individual_stock_constituents": [
                    {"ticker": "NVDA", "name": "Nvidia", "group": "Tech", "price": 125.0, "forward_pe": 39.0, "ev_ebitda": 30.0, "dist_from_52w_high_pct": -5.0},
                    {"ticker": "AMD", "name": "AMD", "group": "Tech", "price": 160.0, "forward_pe": 39.0, "ev_ebitda": 28.0, "dist_from_52w_high_pct": -8.0},
                    {"ticker": "MU", "name": "Micron", "group": "Tech", "price": 95.0, "forward_pe": 12.0, "ev_ebitda": 10.0, "dist_from_52w_high_pct": -25.0}
                ]
            }

            res = analyst.analyze_raw_payload(mock_payload)

        lags = res["single_stock_lagging_opportunities"]
        self.assertEqual(len(lags), 1)
        self.assertEqual(lags[0]["ticker"], "MU")
        self.assertIn("historical sector-relative norm", lags[0]["rationale"])
        self.assertGreater(lags[0]["relative_fpe_discount_pct"], 20.0)

    def test_05b_financials_not_bought_when_credit_stress_is_elevated(self):
        """Financials need a credit-quality check even in a macro-favored quadrant."""
        macro_situation = self.matrix_engine.classify_situation("HOLDING_RESTRICTIVE", 40.0, 3.5, False, 0.30)
        summary = {
            "liquidity_regime": "Expanding (+30d)",
            "overall_regime": macro_situation["name"],
            "treasury_10y": 4.5,
            "dxy": 100.0,
        }
        credit = {"high_yield_oas": 6.0, "chicago_fed_nfci": 0.25}
        valuations = [{"sector": "Financials (XLF)", "forward_pe": 11.0, "ev_ebitda": 8.0}]

        recs = self.analyzer.rec_engine.generate_recommendations(
            summary,
            credit,
            valuations,
            [],
            [],
            macro_situation,
        )

        financials = next(r for r in recs if r["sector"] == "Financials (XLF)")
        self.assertNotIn("BUY", financials["action"])
        self.assertIn("credit", financials["rationale"].lower())

    def test_05c_restrictive_real_yields_downgrade_discounted_tech_without_forcing_sell(self):
        """High real yields are a headwind, but discounted tech should become caution, not automatic sell."""
        macro_situation = self.matrix_engine.classify_situation("HOLDING_RESTRICTIVE", 40.0, 3.5, False, 0.30)
        summary = {
            "liquidity_regime": "Expanding (+30d)",
            "overall_regime": macro_situation["name"],
            "treasury_10y": 4.6,
            "breakeven_10y": 2.1,
            "dxy": 100.0,
        }
        credit = {"high_yield_oas": 2.7, "chicago_fed_nfci": -0.5}
        valuations = [{"sector": "Technology (XLK)", "forward_pe": 19.0, "ev_ebitda": 15.0}]

        recs = self.analyzer.rec_engine.generate_recommendations(
            summary,
            credit,
            valuations,
            [],
            [],
            macro_situation,
        )

        tech = next(r for r in recs if r["sector"] == "Technology (XLK)")
        self.assertNotIn("SELL", tech["action"])
        self.assertIn("CAUTION", tech["action"])

    def test_05d_negative_erp_without_valuation_stretch_is_not_automatic_sell(self):
        """Negative ERP should be a rate/valuation headwind, not a standalone sell rule."""
        macro_situation = self.matrix_engine.classify_situation("HOLDING_RESTRICTIVE", 40.0, 3.5, False, 0.30)
        summary = {
            "liquidity_regime": "Expanding (+30d)",
            "overall_regime": macro_situation["name"],
            "treasury_10y": 4.6,
            "breakeven_10y": 2.1,
            "dxy": 100.0,
        }
        credit = {"high_yield_oas": 2.7, "chicago_fed_nfci": -0.5}
        valuations = [{"sector": "AI Compute & Accelerators", "forward_pe": 24.0, "ev_ebitda": 18.0}]

        recs = self.analyzer.rec_engine.generate_recommendations(
            summary,
            credit,
            valuations,
            [],
            [],
            macro_situation,
        )

        ai = next(r for r in recs if r["sector"] == "AI Compute & Accelerators")
        self.assertNotIn("SELL", ai["action"])
        self.assertIn("headwind", ai["rationale"].lower())

    def test_05e_caution_sector_is_not_upgraded_to_selective_buy(self):
        """Lagging-stock watchlist should not override a sector-level caution signal."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            analyzer = MacroAnalyzer(storage)
            analyzer.calculate_net_liquidity = lambda: {
                "net_liquidity": 100.0,
                "fed_assets_billion": 200.0,
                "tga_billion": 50.0,
                "rrp_billion": 50.0,
                "change_30d_billion": 10.0,
                "m2_yoy": None,
                "quality": "OK",
                "missing_components": [],
            }
            analyzer.analyze_policy_stance = lambda: {
                "policy_rate": 4.5,
                "policy_rate_change_30d": 0.0,
                "real_yield_10y": 2.3,
                "policy_stance": "HOLDING_RESTRICTIVE",
                "rate_trend": "RESTRICTIVE",
                "source": "dff",
                "quality": "OK",
            }
            analyzer.analyze_yield_curve = lambda: {
                "treasury_10y": 4.5,
                "treasury_2y": 4.0,
                "treasury_3m": 3.8,
                "spread_10y_2y": 0.5,
                "spread_10y_3m": 0.7,
                "regime": "Normal (Steep)",
            }
            analyzer.analyze_credit_markets = lambda: {"high_yield_oas": 2.7, "invest_grade_oas": 0.5, "chicago_fed_nfci": -0.5, "regime": "Complacent / Tight Spreads"}
            analyzer.analyze_market_sentiment = lambda: {"vix": 15.0, "dxy": 100.0, "sp500": 5000.0, "crude_oil": 80.0, "gold": 2000.0, "copper": 4.0, "vix_state": "Low Volatility"}
            analyzer.analyze_labor_and_inflation = lambda: {"unemployment_rate": 4.0, "cpi_yoy": 3.5, "housing_yoy": None, "breakeven_10y": 2.2, "sahm_rule_triggered": False}
            analyzer.news_analyzer.get_major_event_summary = lambda limit=12: []
            analyzer.valuation_engine.calculate_sector_valuations = lambda: []
            analyzer.valuation_engine.save_valuations_to_storage = lambda vals: None
            analyzer.ai_tracker.analyze_ecosystem_valuations = lambda: []
            analyzer.raw_engine.build_raw_payload = lambda: {}
            analyzer.llm_analyst.analyze_raw_payload = lambda payload: {
                "single_stock_lagging_opportunities": [
                    {"group": "Downstream Power & Grid", "ticker": "CEG", "action": "WATCHLIST / SELECTIVE REVIEW", "rationale": "Peer discount."}
                ]
            }
            analyzer.rec_engine.generate_recommendations = lambda *args, **kwargs: [
                {
                    "sector": "Downstream Power & Grid",
                    "action": "HOLD / CAUTION",
                    "conviction": "MODERATE",
                    "avg_forward_pe": 25.0,
                    "ev_ebitda": None,
                    "erp": None,
                    "rationale": "Rate/valuation headwind.",
                }
            ]

            analysis = analyzer.generate_full_snapshot()

        rec = analysis["recommendations"][0]
        self.assertEqual(rec["action"], "HOLD / CAUTION")
        self.assertEqual(rec["selective_stock_pick"], "None")

    def test_06_defensive_reporter_formatting(self):
        """Test reporter with empty/missing dict fields to guarantee no formatting crashes."""
        empty_analysis = {
            "summary": {
                "date": "2026-07-22",
                "overall_regime": "TEST REGIME",
                "liquidity_regime": "Neutral",
                "yield_curve_regime": "Normal",
                "credit_regime": "Normal"
            },
            "liquidity_details": {"net_liquidity": None, "fed_assets_billion": None, "tga_billion": None, "rrp_billion": None, "change_30d_billion": None},
            "yield_curve_details": {"treasury_10y": None, "treasury_2y": None, "spread_10y_2y": None, "spread_10y_3m": None, "regime": "Normal"},
            "credit_details": {"high_yield_oas": None, "invest_grade_oas": None, "chicago_fed_nfci": None, "regime": "Normal"},
            "market_details": {"vix": None, "dxy": None, "sp500": None, "crude_oil": None, "gold": None, "copper": None, "vix_state": "Normal"},
            "macro_details": {"unemployment_rate": None, "nonfarm_payrolls_k": None, "initial_claims": None, "breakeven_5y": None, "breakeven_10y": None},
            "news_events": [],
            "sector_valuations": [],
            "ai_ecosystem": [],
            "macro_situation": self.matrix_engine.classify_situation("CUTTING", 10.0, None, False, None),
            "lagging_stock_opportunities": [],
            "recommendations": []
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = MacroReporter(self.storage, self.analyzer, output_dir=Path(tmp_dir), verbose=False)

            # Should run without raising any exceptions or touching production output files.
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    reporter.print_terminal_dashboard(empty_analysis)
                report_path = reporter.generate_markdown_report(empty_analysis)
                self.assertTrue(os.path.exists(report_path))
                self.assertEqual(Path(report_path).parent, Path(tmp_dir))
                self.assertTrue((Path(tmp_dir) / "latest_report.md").exists())
            except Exception as e:
                self.fail(f"Reporter raised unexpected exception on None inputs: {e}")

    def test_06a_report_describes_lagging_stocks_as_historical_relative_discounts(self):
        """Lagging-stock section should explain relative valuation versus the stock's own sector history."""
        analysis = {
            "summary": {
                "date": "2026-07-22",
                "overall_regime": "TEST REGIME",
                "liquidity_regime": "Neutral",
                "yield_curve_regime": "Normal",
                "credit_regime": "Normal",
            },
            "liquidity_details": {"net_liquidity": None, "fed_assets_billion": None, "tga_billion": None, "rrp_billion": None, "change_30d_billion": None},
            "policy_details": {"policy_rate": None, "policy_rate_change_30d": None, "real_yield_10y": None, "source": None, "policy_stance": "UNKNOWN"},
            "yield_curve_details": {"treasury_10y": None, "treasury_2y": None, "spread_10y_2y": None, "spread_10y_3m": None, "regime": "Normal"},
            "credit_details": {"high_yield_oas": None, "invest_grade_oas": None, "chicago_fed_nfci": None, "regime": "Normal"},
            "market_details": {"vix": None, "dxy": None, "sp500": None, "crude_oil": None, "gold": None, "copper": None, "vix_state": "Normal"},
            "macro_details": {},
            "news_events": [],
            "sector_valuations": [],
            "ai_ecosystem": [],
            "macro_situation": {},
            "lagging_stock_opportunities": [
                {
                    "ticker": "MU",
                    "name": "Micron",
                    "group": "Tech",
                    "forward_pe": 12.0,
                    "peer_avg_fpe": 30.0,
                    "current_relative_fpe": 0.4,
                    "historical_relative_fpe": 0.7,
                    "relative_fpe_discount_pct": 42.9,
                    "action": "WATCHLIST / SELECTIVE REVIEW (Lagging Value)",
                    "rationale": "Discounted versus historical sector-relative norm.",
                }
            ],
            "recommendations": [],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = MacroReporter(self.storage, self.analyzer, output_dir=Path(tmp_dir), verbose=False)
            report_path = reporter.generate_markdown_report(analysis)
            content = Path(report_path).read_text(encoding="utf-8")

        self.assertIn("Historical Sector-Relative Valuation", content)
        self.assertIn("Current Relative Fwd P/E", content)
        self.assertIn("Historical Relative Norm", content)
        self.assertIn("42.9%", content)

    def test_06b_fetch_cnn_fear_greed_index_saves_daily_score(self):
        """CNN Fear & Greed should be fetched as a numeric market sentiment observation."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            fetcher = MacroFetcher(storage)

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return json.dumps({
                        "fear_and_greed": {
                            "score": 78.4,
                            "rating": "extreme greed",
                        }
                    }).encode("utf-8")

            original_urlopen = fetcher._urlopen
            fetcher._urlopen = lambda request, timeout=15: FakeResponse()
            try:
                count, err = fetcher.fetch_cnn_fear_greed_index()
            finally:
                fetcher._urlopen = original_urlopen

            latest = storage.get_latest_observation("cnn_fear_greed_index")

        self.assertIsNone(err)
        self.assertEqual(count, 1)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["date"], datetime.now().strftime("%Y-%m-%d"))
        self.assertAlmostEqual(latest["value"], 78.4)

    def test_06b2_fetch_shiller_pe_saves_current_multpl_value(self):
        """Shiller PE should be fetched as a numeric secondary valuation observation."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            fetcher = MacroFetcher(storage)

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return b"""
                    <html>
                      <head>
                        <meta name="description" content="Shiller PE Ratio chart, historic, and current data. Current Shiller PE Ratio is 40.46, a change of +0.04 from previous market close." />
                      </head>
                      <body>
                        <h1>Shiller PE Ratio</h1>
                        <div>4:00 PM EDT, Fri Jul 24</div>
                      </body>
                    </html>
                    """

            original_urlopen = fetcher._urlopen
            fetcher._urlopen = lambda request, timeout=15: FakeResponse()
            try:
                count, err = fetcher.fetch_shiller_pe_ratio()
            finally:
                fetcher._urlopen = original_urlopen

            latest = storage.get_latest_observation("shiller_pe")

        self.assertIsNone(err)
        self.assertEqual(count, 1)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["date"], datetime.now().strftime("%Y-%m-%d"))
        self.assertAlmostEqual(latest["value"], 40.46)

    def test_06c_analyzer_interprets_cnn_fear_greed_as_market_overlay(self):
        """Fear & Greed should enrich market sentiment without becoming a core quadrant input."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("cnn_fear_greed_index", pd.DataFrame([
                {"date": datetime.now().strftime("%Y-%m-%d"), "value": 81.0},
            ]))

            market = MacroAnalyzer(storage).analyze_market_sentiment()

        self.assertEqual(market["cnn_fear_greed_index"], 81.0)
        self.assertEqual(market["cnn_fear_greed_rating"], "Extreme Greed")
        self.assertIn("overlay", market["cnn_fear_greed_signal"].lower())

    def test_06c1_analyzer_interprets_shiller_pe_as_secondary_overlay(self):
        """Shiller PE should inform valuation context without becoming a core quadrant input."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("shiller_pe", pd.DataFrame([
                {"date": datetime.now().strftime("%Y-%m-%d"), "value": 40.46},
            ]))

            market = MacroAnalyzer(storage).analyze_market_sentiment()
            quadrant = MacroMatrixEngine().classify_situation("CUTTING", 50.0, 2.5, False, -0.50)

        self.assertEqual(market["shiller_pe"], 40.46)
        self.assertEqual(market["shiller_pe_rating"], "Very Expensive")
        self.assertIn("secondary valuation overlay", market["shiller_pe_signal"].lower())
        self.assertEqual(quadrant["situation_id"], 1)

    def test_06c2_analyzer_suppresses_stale_cnn_fear_greed_readings(self):
        """Old Fear & Greed observations should not be surfaced as current market sentiment."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("cnn_fear_greed_index", pd.DataFrame([
                {"date": "2020-01-01", "value": 90.0},
            ]))

            market = MacroAnalyzer(storage).analyze_market_sentiment()

        self.assertIsNone(market["cnn_fear_greed_index"])
        self.assertEqual(market["cnn_fear_greed_rating"], "Stale")
        self.assertIn("stale", market["cnn_fear_greed_signal"].lower())

    def test_06c3_analyzer_suppresses_stale_shiller_pe_readings(self):
        """Old Shiller PE observations should not be surfaced as current valuation context."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            storage = MacroStorage(tmp.name)
            storage.save_observations("shiller_pe", pd.DataFrame([
                {"date": "2020-01-01", "value": 40.0},
            ]))

            market = MacroAnalyzer(storage).analyze_market_sentiment()

        self.assertIsNone(market["shiller_pe"])
        self.assertEqual(market["shiller_pe_rating"], "Stale")
        self.assertIn("stale", market["shiller_pe_signal"].lower())

    def test_06d_report_includes_fresh_extreme_fear_greed_overlay(self):
        """Report should show CNN Fear & Greed and mention only extreme readings up top."""
        analysis = {
            "summary": {
                "date": "2026-07-22",
                "overall_regime": "TEST REGIME",
                "liquidity_regime": "Neutral",
                "yield_curve_regime": "Normal",
                "credit_regime": "Normal",
            },
            "liquidity_details": {"net_liquidity": None, "fed_assets_billion": None, "tga_billion": None, "rrp_billion": None, "change_30d_billion": None},
            "policy_details": {"policy_rate": None, "policy_rate_change_30d": None, "real_yield_10y": None, "source": None, "policy_stance": "UNKNOWN"},
            "yield_curve_details": {"treasury_10y": None, "treasury_2y": None, "spread_10y_2y": None, "spread_10y_3m": None, "regime": "Normal"},
            "credit_details": {"high_yield_oas": None, "invest_grade_oas": None, "chicago_fed_nfci": None, "regime": "Normal"},
            "market_details": {
                "vix": 15.0,
                "dxy": 101.0,
                "sp500": 6500.0,
                "crude_oil": 70.0,
                "gold": 2500.0,
                "copper": 4.5,
                "vix_state": "Normal",
                "cnn_fear_greed_index": 82.0,
                "cnn_fear_greed_rating": "Extreme Greed",
                "cnn_fear_greed_signal": "Extreme greed risk-appetite overlay: avoid chasing crowded risk without valuation support.",
            },
            "macro_details": {},
            "news_events": [],
            "sector_valuations": [],
            "ai_ecosystem": [],
            "macro_situation": {},
            "lagging_stock_opportunities": [],
            "recommendations": [],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = MacroReporter(self.storage, self.analyzer, output_dir=Path(tmp_dir), verbose=False)
            report_path = reporter.generate_markdown_report(analysis)
            content = Path(report_path).read_text(encoding="utf-8")

        self.assertIn("CNN Fear & Greed Index", content)
        self.assertIn("82.00", content)
        self.assertIn("Extreme Greed", content)
        self.assertIn("avoid chasing crowded risk", content)
        self.assertIn("**Sentiment:** CNN Fear & Greed Index is `82.00` (`Extreme Greed`)", content.split("## 1. Active Macro Situation")[0])

    def test_06e_report_includes_shiller_pe_as_secondary_overlay(self):
        """Report should show Shiller PE beside Fear & Greed as valuation context."""
        analysis = {
            "summary": {
                "date": "2026-07-22",
                "overall_regime": "TEST REGIME",
                "liquidity_regime": "Neutral",
                "yield_curve_regime": "Normal",
                "credit_regime": "Normal",
            },
            "liquidity_details": {"net_liquidity": None, "fed_assets_billion": None, "tga_billion": None, "rrp_billion": None, "change_30d_billion": None},
            "policy_details": {"policy_rate": None, "policy_rate_change_30d": None, "real_yield_10y": None, "source": None, "policy_stance": "UNKNOWN"},
            "yield_curve_details": {"treasury_10y": None, "treasury_2y": None, "spread_10y_2y": None, "spread_10y_3m": None, "regime": "Normal"},
            "credit_details": {"high_yield_oas": None, "invest_grade_oas": None, "chicago_fed_nfci": None, "regime": "Normal"},
            "market_details": {
                "vix": 15.0,
                "dxy": 101.0,
                "sp500": 6500.0,
                "crude_oil": 70.0,
                "gold": 2500.0,
                "copper": 4.5,
                "vix_state": "Normal",
                "cnn_fear_greed_index": 42.0,
                "cnn_fear_greed_rating": "Fear",
                "cnn_fear_greed_signal": "Fear risk-appetite overlay.",
                "shiller_pe": 40.46,
                "shiller_pe_rating": "Very Expensive",
                "shiller_pe_signal": "Very expensive secondary valuation overlay: broad equity valuations are stretched, so require stronger macro, credit, and earnings confirmation before adding index beta.",
            },
            "macro_details": {},
            "news_events": [],
            "sector_valuations": [],
            "ai_ecosystem": [],
            "macro_situation": {},
            "lagging_stock_opportunities": [],
            "recommendations": [],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = MacroReporter(self.storage, self.analyzer, output_dir=Path(tmp_dir), verbose=False)
            report_path = reporter.generate_markdown_report(analysis)
            content = Path(report_path).read_text(encoding="utf-8")

        self.assertIn("Shiller PE Ratio", content)
        self.assertIn("40.46", content)
        self.assertIn("Very Expensive", content)
        self.assertIn("secondary valuation overlay", content)

    def test_07_markdown_report_starts_with_notable_summary_only(self):
        """Daily report should open with a concise notable-events/news/decisions summary."""
        analysis = {
            "summary": {
                "date": "2026-07-22",
                "overall_regime": "RESERVE LIQUIDITY EXPANSION (Rates Cutting | Balance Sheet Expanding)",
                "liquidity_regime": "Expanding (+30d)",
                "yield_curve_regime": "Inverted",
                "credit_regime": "Normal",
            },
            "liquidity_details": {"net_liquidity": 6000.0, "fed_assets_billion": 7000.0, "tga_billion": 900.0, "rrp_billion": 100.0, "change_30d_billion": 75.0},
            "policy_details": {"policy_rate": 4.25, "policy_rate_change_30d": -0.25, "real_yield_10y": 1.8, "source": "Fed Funds", "policy_stance": "CUTTING"},
            "yield_curve_details": {"treasury_10y": 4.1, "treasury_2y": 4.3, "spread_10y_2y": -0.2, "spread_10y_3m": -0.5, "regime": "Inverted"},
            "credit_details": {"high_yield_oas": 3.5, "invest_grade_oas": 1.0, "chicago_fed_nfci": -0.2, "regime": "Normal"},
            "market_details": {"vix": 15.0, "dxy": 101.0, "sp500": 6500.0, "crude_oil": 70.0, "gold": 2500.0, "copper": 4.5, "vix_state": "Normal"},
            "macro_details": {},
            "news_events": [
                {"title": "Fed signals a major policy shift", "category": "Federal Reserve & Liquidity", "impact_score": 9, "sentiment": "Positive", "source": "Example News"},
                {"title": "Routine market color", "category": "Market Commentary", "impact_score": 3, "sentiment": "Neutral", "source": "Example News"},
            ],
            "sector_valuations": [],
            "ai_ecosystem": [],
            "macro_situation": {
                "name": "RESERVE LIQUIDITY EXPANSION",
                "rates_label": "Rates Cutting",
                "bs_label": "Balance Sheet Expanding",
                "description": "Liquidity tailwind with easier policy.",
                "favored_sectors": [],
                "favored_company_types": [],
                "disfavored_sectors": [],
            },
            "lagging_stock_opportunities": [],
            "recommendations": [
                {"sector_group": "Semiconductors", "action": "HOLD SECTOR / SELECTIVE BUY [MU]", "conviction": "HIGH", "avg_forward_pe": 18.0, "selective_stock_pick": "MU", "rationale": "Deep peer discount."},
                {"sector_group": "Utilities", "action": "HOLD", "conviction": "LOW", "avg_forward_pe": 16.0, "selective_stock_pick": "None", "rationale": "No material change."},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            reporter = MacroReporter(self.storage, self.analyzer, output_dir=Path(tmp_dir), verbose=False)
            report_path = reporter.generate_markdown_report(analysis)
            content = Path(report_path).read_text(encoding="utf-8")

        self.assertIn("## Notable Summary", content)
        self.assertLess(content.index("## Notable Summary"), content.index("## 1. Active Macro Situation"))
        self.assertIn("Fed signals a major policy shift", content)
        self.assertIn("HOLD SECTOR / SELECTIVE BUY [MU]", content)
        self.assertNotIn("Routine market color", content.split("## 1. Active Macro Situation")[0])
        self.assertNotIn("Utilities", content.split("## 1. Active Macro Situation")[0])

    def test_07a_notable_summary_compares_against_previous_report(self):
        """Daily report should flag changed, unchanged, new, and removed notable summary items."""
        previous_report = """# Daily 4-Quadrant Macro & Dynamic Sector Strategy Report (2026-07-22)
---
## Notable Summary

- **Decision:** Active quadrant is `RESERVE LIQUIDITY EXPANSION` (Rates Cutting; Balance Sheet Expanding). Liquidity tailwind with easier policy.
- **News:** Fed signals a major policy shift (Federal Reserve & Liquidity; impact 9; Positive).
- **Decision:** Semiconductors: **HOLD SECTOR / SELECTIVE BUY [MU]** (HIGH; pick `MU`).
- **Decision:** `AAPL`: **WATCHLIST**. Prior lagging-stock setup.
---
## 1. Active Macro Situation (2x2 Matrix Analysis)
"""
        analysis = {
            "summary": {"date": "2026-07-23"},
            "liquidity_details": {},
            "policy_details": {},
            "yield_curve_details": {},
            "credit_details": {},
            "market_details": {},
            "macro_details": {},
            "news_events": [
                {"title": "Fed signals a major policy shift", "category": "Federal Reserve & Liquidity", "impact_score": 9, "sentiment": "Positive"},
                {"title": "Credit spreads widen abruptly", "category": "Credit", "impact_score": 8, "sentiment": "Negative"},
            ],
            "sector_valuations": [],
            "ai_ecosystem": [],
            "macro_situation": {
                "name": "RESERVE LIQUIDITY EXPANSION",
                "rates_label": "Rates Cutting",
                "bs_label": "Balance Sheet Expanding",
                "description": "Liquidity tailwind is fading.",
                "favored_sectors": [],
                "favored_company_types": [],
                "disfavored_sectors": [],
            },
            "lagging_stock_opportunities": [],
            "recommendations": [
                {"sector_group": "Semiconductors", "action": "HOLD SECTOR / SELECTIVE BUY [MU]", "conviction": "HIGH", "avg_forward_pe": 18.0, "selective_stock_pick": "MU", "rationale": "Deep peer discount."},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "macro_report_2026-07-22.md").write_text(previous_report, encoding="utf-8")
            reporter = MacroReporter(self.storage, self.analyzer, output_dir=tmp_path, verbose=False)
            report_path = reporter.generate_markdown_report(analysis)
            summary = Path(report_path).read_text(encoding="utf-8").split("## 1. Active Macro Situation")[0]

        self.assertIn("**Changed:** **Decision:** Active quadrant", summary)
        self.assertIn("Previously: **Decision:** Active quadrant", summary)
        self.assertIn("**Unchanged:** **News:** Fed signals a major policy shift", summary)
        self.assertIn("**Unchanged:** **Decision:** Semiconductors", summary)
        self.assertIn("**New:** **News:** Credit spreads widen abruptly", summary)
        self.assertIn("**Removed:** **Decision:** `AAPL`: **WATCHLIST**", summary)


if __name__ == "__main__":
    unittest.main()
