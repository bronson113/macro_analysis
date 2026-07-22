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
from datetime import datetime
from pathlib import Path
from storage import MacroStorage
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


if __name__ == "__main__":
    unittest.main()
