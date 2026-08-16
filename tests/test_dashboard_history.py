import json
import tempfile
import unittest
import os
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

import backfill_snapshots
import extract_dashboard_data
import config


class TestDashboardHistory(unittest.TestCase):
    def test_export_dashboard_payload_merges_evidence_health_and_unmatured_outcomes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_dir = root / "output"
            data_dir = root / "data"
            output_dir.mkdir()
            data_dir.mkdir()
            (output_dir / "latest_raw_payload.json").write_text(
                json.dumps({"metadata": {"date": "2026-08-01"}, "evidence_assessments": [{"sector_group": "Technology"}]}),
                encoding="utf-8",
            )
            (data_dir / "source_health.csv").write_text(
                "source,fetch_key,observation_time,fetch_time,status,is_stale,record_count,error_category,message\n"
                "FRED,treasury_10y,2026-08-01,2026-08-01T08:00:00,CURRENT,false,1,,Available\n",
                encoding="utf-8",
            )

            old_output_dir = extract_dashboard_data.OUTPUT_DIR
            old_source_health_csv = extract_dashboard_data.SOURCE_HEALTH_CSV
            try:
                extract_dashboard_data.OUTPUT_DIR = output_dir
                extract_dashboard_data.SOURCE_HEALTH_CSV = data_dir / "source_health.csv"
                payload = extract_dashboard_data.export_dashboard_payload()
            finally:
                extract_dashboard_data.OUTPUT_DIR = old_output_dir
                extract_dashboard_data.SOURCE_HEALTH_CSV = old_source_health_csv

            exported = json.loads((output_dir / "dashboard_data.json").read_text(encoding="utf-8"))
            self.assertEqual(exported, payload)
            self.assertEqual(exported["evidence_assessments"], [{"sector_group": "Technology"}])
            self.assertEqual(exported["source_health"][0]["fetch_key"], "treasury_10y")
            self.assertIsNone(exported["outcome_evaluation"])

    def test_export_dashboard_payload_exposes_ordered_regime_groups(self):
        """Dashboard exports preserve the five structured regime groups in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output_dir = root / "output"
            data_dir = root / "data"
            output_dir.mkdir()
            data_dir.mkdir()
            (output_dir / "latest_raw_payload.json").write_text(
                json.dumps({
                    "macro_regime": {
                        "current_state": {"situation_id": 4},
                        "momentum": {"liquidity_30d": "DETERIORATING"},
                        "consensus": {"quality": "UNAVAILABLE"},
                        "quadrant": {"description": "Liquidity remains abundant."},
                        "data_quality": {"quality": "PARTIAL"},
                    }
                }),
                encoding="utf-8",
            )

            old_output_dir = extract_dashboard_data.OUTPUT_DIR
            old_source_health_csv = extract_dashboard_data.SOURCE_HEALTH_CSV
            try:
                extract_dashboard_data.OUTPUT_DIR = output_dir
                extract_dashboard_data.SOURCE_HEALTH_CSV = data_dir / "source_health.csv"
                payload = extract_dashboard_data.export_dashboard_payload()
            finally:
                extract_dashboard_data.OUTPUT_DIR = old_output_dir
                extract_dashboard_data.SOURCE_HEALTH_CSV = old_source_health_csv

        self.assertEqual(
            [section["name"] for section in payload["macro_regime_sections"]],
            ["Current State", "Momentum", "Consensus", "Interpretation", "Data Quality"],
        )
        self.assertEqual(payload["macro_regime_sections"][0]["data"]["situation_id"], 4)

    def test_extract_history_exports_ten_year_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            snapshots_csv = tmp_path / "daily_snapshots.csv"
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            base_date = datetime.now() - timedelta(days=3650)
            rows = [
                {"date": (base_date + timedelta(days=offset)).strftime("%Y-%m-%d"), 
                 "net_liquidity": float(offset), "fed_assets": float(offset), "tga": float(offset), 
                 "rrp": float(offset), "treasury_10y": float(offset), "treasury_2y": float(offset), 
                 "spread_10y_2y": float(offset), "high_yield_oas": float(offset), "sp500": float(offset), 
                 "vix": float(offset), "dxy": float(offset), "cpi_yoy": float(offset), 
                 "policy_rate": float(offset), "real_yield_10y": float(offset)}
                for offset in range(3660)
            ]
            pd.DataFrame(rows).to_csv(snapshots_csv, index=False)

            old_snapshots_csv = extract_dashboard_data.SNAPSHOTS_CSV
            old_output_dir = extract_dashboard_data.OUTPUT_DIR
            try:
                extract_dashboard_data.SNAPSHOTS_CSV = str(snapshots_csv)
                extract_dashboard_data.OUTPUT_DIR = output_dir
                extract_dashboard_data.extract_history()
            finally:
                extract_dashboard_data.SNAPSHOTS_CSV = old_snapshots_csv
                extract_dashboard_data.OUTPUT_DIR = old_output_dir

            history = json.loads((output_dir / "history.json").read_text())
            self.assertEqual(len(history), 3650)
            self.assertEqual(history[0]["date"], rows[-3650]["date"])
            self.assertEqual(history[-1]["date"], rows[-1]["date"])

    def test_backfill_builds_snapshots_for_dates_inside_ten_year_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            obs_csv = tmp_path / "macro_observations.csv"
            snapshots_csv = tmp_path / "daily_snapshots.csv"

            old_date = (datetime.now() - timedelta(days=365 * 8)).strftime("%Y-%m-%d")
            recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            obs = pd.DataFrame([
                {"indicator_key": "treasury_10y", "date": old_date, "value": 2.0},
                {"indicator_key": "treasury_10y", "date": recent_date, "value": 4.5},
            ])
            obs.to_csv(obs_csv, index=False)
            
            # create empty snapshots
            pd.DataFrame(columns=['date', 'treasury_10y']).to_csv(snapshots_csv, index=False)

            import storage
            old_obs_csv = backfill_snapshots.OBSERVATIONS_CSV
            old_snapshots_csv_config = config.SNAPSHOTS_CSV
            old_snapshots_csv_storage = storage.SNAPSHOTS_CSV
            try:
                backfill_snapshots.OBSERVATIONS_CSV = str(obs_csv)
                config.SNAPSHOTS_CSV = str(snapshots_csv)
                storage.SNAPSHOTS_CSV = str(snapshots_csv)
                backfill_snapshots.backfill()
            finally:
                backfill_snapshots.OBSERVATIONS_CSV = old_obs_csv
                config.SNAPSHOTS_CSV = old_snapshots_csv_config
                storage.SNAPSHOTS_CSV = old_snapshots_csv_storage

            df_snapshots = pd.read_csv(snapshots_csv)
            dates = set(df_snapshots['date'])

            self.assertIn(old_date, dates)
            self.assertIn(recent_date, dates)


if __name__ == "__main__":
    unittest.main()
