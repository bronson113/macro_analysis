import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd

from weekly_digest import WeeklyDigestGenerator, fmt_val, fmt_delta
from report_manifest import build_weekly_digest_manifest, build_report_manifest


class TestWeeklyDigest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.output_dir = self.root / "output"
        self.output_dir.mkdir(parents=True)
        self.web_public_dir = self.root / "web" / "public"
        self.web_public_dir.mkdir(parents=True)

        # Create dummy snapshots CSV with 2 weeks of data
        self.snapshots_csv = self.root / "daily_snapshots.csv"
        rows = [
            # Week 1: 2026-08-10 (Mon) to 2026-08-14 (Fri)
            {"date": "2026-08-10", "net_liquidity": 5818.26, "fed_assets": 6748.56, "tga": 929.32, "rrp": 0.97, "treasury_10y": 4.72, "treasury_2y": 4.25, "spread_10y_2y": 0.47, "high_yield_oas": 2.70, "sp500": 7753.10, "vix": 15.46, "dxy": 99.81, "situation_id": 3.0, "policy_state": "RESTRICTIVE", "liquidity_state": "SCARCE"},
            {"date": "2026-08-14", "net_liquidity": 5800.30, "fed_assets": 6759.95, "tga": 959.40, "rrp": 0.25, "treasury_10y": 4.68, "treasury_2y": 4.17, "spread_10y_2y": 0.51, "high_yield_oas": 2.67, "sp500": 7785.75, "vix": 14.25, "dxy": 99.67, "situation_id": 3.0, "policy_state": "RESTRICTIVE", "liquidity_state": "SCARCE"},
            # Week 2: 2026-08-17 (Mon) to 2026-08-21 (Fri)
            {"date": "2026-08-17", "net_liquidity": 5800.30, "fed_assets": 6759.95, "tga": 959.40, "rrp": 0.25, "treasury_10y": 4.72, "treasury_2y": 4.19, "spread_10y_2y": 0.53, "high_yield_oas": 2.70, "sp500": 7745.06, "vix": 15.19, "dxy": 99.64, "situation_id": 2.0, "policy_state": "ACCOMMODATIVE", "liquidity_state": "SCARCE"},
            {"date": "2026-08-21", "net_liquidity": 5809.07, "fed_assets": 6745.70, "tga": 936.41, "rrp": 0.23, "treasury_10y": 4.65, "treasury_2y": 4.19, "spread_10y_2y": 0.50, "high_yield_oas": 2.73, "sp500": 7641.16, "vix": 15.69, "dxy": 98.62, "situation_id": 2.0, "policy_state": "ACCOMMODATIVE", "liquidity_state": "SCARCE"},
        ]
        pd.DataFrame(rows).to_csv(self.snapshots_csv, index=False)

        # Create dummy observations CSV
        self.observations_csv = self.root / "macro_observations.csv"
        obs_rows = [
            {"date": "2026-08-17", "indicator_key": "crude_oil", "value": 84.50},
            {"date": "2026-08-21", "indicator_key": "crude_oil", "value": 86.91},
            {"date": "2026-08-17", "indicator_key": "gold", "value": 4417.80},
            {"date": "2026-08-21", "indicator_key": "gold", "value": 4647.40},
        ]
        pd.DataFrame(obs_rows).to_csv(self.observations_csv, index=False)

        # Create dummy news CSV
        self.news_csv = self.root / "macro_news.csv"
        news_rows = [
            {"date": "2026-08-21", "title": "Fed minutes discuss rate paths", "summary": "Fed talks policy options", "category": "Central Banks", "source": "Reuters", "impact_score": 5},
            {"date": "2026-08-18", "title": "Oil surges on supply concerns", "summary": "Crude oil gains", "category": "Energy", "source": "Bloomberg", "impact_score": 4},
        ]
        pd.DataFrame(news_rows).to_csv(self.news_csv, index=False)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_formatting_helpers(self):
        self.assertEqual(fmt_val(1234.56, ":,.1f"), "1,234.6")
        self.assertEqual(fmt_val(None), "N/A")
        self.assertEqual(fmt_delta(5.25, ":+.1f", suffix="%"), "+5.2%")
        self.assertEqual(fmt_delta(-3.1, ":+.2f"), "-3.10")
        self.assertEqual(fmt_delta(None), "N/A")

    def test_get_available_weeks(self):
        generator = WeeklyDigestGenerator(
            snapshots_path=self.snapshots_csv,
            observations_path=self.observations_csv,
            news_path=self.news_csv,
            output_dir=self.output_dir,
        )
        weeks = generator.get_available_weeks(min_date="2026-08-01")
        self.assertEqual(len(weeks), 2)
        # Newest first
        self.assertEqual(weeks[0]["end_date"], "2026-08-21")
        self.assertEqual(weeks[0]["start_date"], "2026-08-17")
        self.assertEqual(weeks[1]["end_date"], "2026-08-14")
        self.assertEqual(weeks[1]["start_date"], "2026-08-10")

    def test_compute_weekly_deltas(self):
        generator = WeeklyDigestGenerator(
            snapshots_path=self.snapshots_csv,
            observations_path=self.observations_csv,
            news_path=self.news_csv,
            output_dir=self.output_dir,
        )
        deltas = generator.compute_weekly_deltas("2026-08-17", "2026-08-21")
        liq = deltas["liquidity"]
        rates = deltas["rates"]
        market = deltas["market"]

        # Net liquidity delta: 5809.07 - 5800.30 = +8.77
        self.assertAlmostEqual(liq["net_liquidity"]["delta"], 8.77, places=2)
        # 10Y yield: 4.65 - 4.72 = -0.07 (-7.0 bps)
        self.assertAlmostEqual(rates["treasury_10y"]["delta_bps"], -7.0, places=1)
        # S&P 500: (7641.16 - 7745.06) / 7745.06 = -1.34%
        self.assertAlmostEqual(market["sp500"]["pct"], -1.34, places=1)
        # Crude oil from observations: 86.91 - 84.50 = +2.41
        self.assertAlmostEqual(market["crude_oil"]["delta"], 2.41, places=2)

    def test_weekly_regime_trajectory(self):
        generator = WeeklyDigestGenerator(
            snapshots_path=self.snapshots_csv,
            observations_path=self.observations_csv,
            news_path=self.news_csv,
            output_dir=self.output_dir,
        )
        regime = generator.get_weekly_regime_trajectory("2026-08-17", "2026-08-21")
        self.assertEqual(regime["end_situation_id"], 2)
        self.assertTrue(regime["is_stable"])
        self.assertEqual(regime["end_policy"], "ACCOMMODATIVE")

    def test_generate_and_save_weekly_digest(self):
        generator = WeeklyDigestGenerator(
            snapshots_path=self.snapshots_csv,
            observations_path=self.observations_csv,
            news_path=self.news_csv,
            output_dir=self.output_dir,
        )
        results = generator.build_all_weekly_digests(min_date="2026-08-01")
        self.assertEqual(len(results), 2)

        # Check output files
        file_21 = self.output_dir / "weekly_digest_2026-08-21.md"
        file_14 = self.output_dir / "weekly_digest_2026-08-14.md"
        latest_file = self.output_dir / "latest_weekly_digest.md"
        index_file = self.output_dir / "weekly_digests_index.json"

        self.assertTrue(file_21.exists())
        self.assertTrue(file_14.exists())
        self.assertTrue(latest_file.exists())
        self.assertTrue(index_file.exists())

        content_21 = file_21.read_text(encoding="utf-8")
        self.assertIn("Weekly Macro Digest", content_21)
        self.assertIn("## 1. Active Macro Situation", content_21)
        self.assertIn("## 2. Weekly Indicator Movements", content_21)
        self.assertIn("Reserve Liquidity Proxy", content_21)

        # Latest should match the newest digest
        self.assertEqual(latest_file.read_text(encoding="utf-8"), content_21)

    def test_build_weekly_digest_manifest(self):
        generator = WeeklyDigestGenerator(
            snapshots_path=self.snapshots_csv,
            observations_path=self.observations_csv,
            news_path=self.news_csv,
            output_dir=self.output_dir,
        )
        generator.build_all_weekly_digests(min_date="2026-08-01")

        # Now test build_weekly_digest_manifest
        digests = build_weekly_digest_manifest(output_dir=self.output_dir, public_dir=self.web_public_dir)
        self.assertEqual(len(digests), 2)
        self.assertTrue((self.web_public_dir / "digests" / "index.json").exists())
        self.assertTrue((self.web_public_dir / "digests" / "weekly_digest_2026-08-21.md").exists())
        self.assertTrue((self.web_public_dir / "latest_weekly_digest.md").exists())


if __name__ == "__main__":
    unittest.main()
