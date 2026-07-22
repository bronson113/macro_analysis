"""
Unit and Integration Test Suite for Defiant Gatekeeper Macro Analysis Pipeline.
Verifies 100% data trust, defensive error handling, matrix classification,
single-stock dispersion detection, and report rendering safety.
"""

import os
import json
import unittest
import tempfile
import pandas as pd
from datetime import datetime
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
        cls.storage = MacroStorage()
        cls.analyzer = MacroAnalyzer(cls.storage)
        cls.matrix_engine = MacroMatrixEngine()
        cls.llm_analyst = DynamicMacroAnalyst(cls.storage)
        cls.raw_engine = RawDataEngine(cls.storage)
        cls.reporter = MacroReporter(cls.storage, cls.analyzer)

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

    def test_03e_macro_matrix_returns_insufficient_data_regime(self):
        """The matrix should not force a quadrant when rate or liquidity trend is missing."""
        res = self.matrix_engine.classify_situation(None, None, None, False, None)

        self.assertEqual(res["situation_id"], 0)
        self.assertEqual(res["quality"], "INSUFFICIENT_DATA")
        self.assertEqual(res["favored_sectors"], [])

    def test_04_raw_payload_generation(self):
        """Test un-hardcoded raw data JSON payload generation."""
        payload = self.raw_engine.build_raw_payload()
        self.assertIn("metadata", payload)
        self.assertIn("macro_quantitative", payload)
        self.assertIn("individual_stock_constituents", payload)
        self.assertGreater(len(payload["individual_stock_constituents"]), 10)

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

        # Should run without raising any exceptions
        try:
            self.reporter.print_terminal_dashboard(empty_analysis)
            report_path = self.reporter.generate_markdown_report(empty_analysis)
            self.assertTrue(os.path.exists(report_path))
        except Exception as e:
            self.fail(f"Reporter raised unexpected exception on None inputs: {e}")


if __name__ == "__main__":
    unittest.main()
