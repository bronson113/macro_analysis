import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

import backfill_snapshots
import extract_dashboard_data


class TestDashboardHistory(unittest.TestCase):
    def test_extract_history_exports_ten_year_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "macro.db"
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            conn = sqlite3.connect(db_path)
            try:
                conn.execute("""
                    CREATE TABLE daily_snapshots (
                        date TEXT PRIMARY KEY,
                        net_liquidity REAL,
                        fed_assets REAL,
                        tga REAL,
                        rrp REAL,
                        treasury_10y REAL,
                        treasury_2y REAL,
                        spread_10y_2y REAL,
                        high_yield_oas REAL,
                        sp500 REAL,
                        vix REAL,
                        dxy REAL,
                        cpi_yoy REAL,
                        policy_rate REAL,
                        real_yield_10y REAL
                    )
                """)
                base_date = datetime.now() - timedelta(days=3650)
                rows = [
                    ((base_date + timedelta(days=offset)).strftime("%Y-%m-%d"), float(offset))
                    for offset in range(3660)
                ]
                conn.executemany("""
                    INSERT INTO daily_snapshots (
                        date, net_liquidity, fed_assets, tga, rrp,
                        treasury_10y, treasury_2y, spread_10y_2y,
                        high_yield_oas, sp500, vix, dxy, cpi_yoy,
                        policy_rate, real_yield_10y
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [(date, value, value, value, value, value, value, value, value, value, value, value, value, value, value) for date, value in rows])
                conn.commit()
            finally:
                conn.close()

            old_db_path = extract_dashboard_data.DB_PATH
            old_output_dir = extract_dashboard_data.OUTPUT_DIR
            try:
                extract_dashboard_data.DB_PATH = db_path
                extract_dashboard_data.OUTPUT_DIR = output_dir
                extract_dashboard_data.extract_history()
            finally:
                extract_dashboard_data.DB_PATH = old_db_path
                extract_dashboard_data.OUTPUT_DIR = old_output_dir

            history = json.loads((output_dir / "history.json").read_text())
            self.assertEqual(len(history), 3650)
            self.assertEqual(history[0]["date"], rows[-3650][0])
            self.assertEqual(history[-1]["date"], rows[-1][0])

    def test_backfill_builds_snapshots_for_dates_inside_ten_year_window(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            conn = sqlite3.connect(tmp.name)
            try:
                conn.execute("""
                    CREATE TABLE macro_observations (
                        indicator_key TEXT NOT NULL,
                        date TEXT NOT NULL,
                        value REAL NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (indicator_key, date)
                    )
                """)
                conn.execute("""
                    CREATE TABLE daily_snapshots (
                        date TEXT PRIMARY KEY,
                        net_liquidity REAL,
                        fed_assets REAL,
                        tga REAL,
                        rrp REAL,
                        treasury_10y REAL,
                        treasury_2y REAL,
                        spread_10y_2y REAL,
                        high_yield_oas REAL,
                        vix REAL,
                        dxy REAL,
                        sp500 REAL,
                        unemployment_rate REAL,
                        cpi_yoy REAL,
                        breakeven_10y REAL,
                        m2_yoy REAL,
                        policy_rate REAL,
                        policy_rate_change_30d REAL,
                        real_yield_10y REAL
                    )
                """)

                old_date = (datetime.now() - timedelta(days=365 * 8)).strftime("%Y-%m-%d")
                recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                obs = pd.DataFrame([
                    {"indicator_key": "treasury_10y", "date": old_date, "value": 2.0},
                    {"indicator_key": "treasury_10y", "date": recent_date, "value": 4.5},
                ])
                obs.to_sql("macro_observations", conn, if_exists="append", index=False)
                conn.commit()
            finally:
                conn.close()

            old_db_path = backfill_snapshots.DB_PATH
            try:
                backfill_snapshots.DB_PATH = tmp.name
                backfill_snapshots.backfill()
            finally:
                backfill_snapshots.DB_PATH = old_db_path

            conn = sqlite3.connect(tmp.name)
            try:
                dates = {
                    row[0]
                    for row in conn.execute("SELECT date FROM daily_snapshots")
                }
            finally:
                conn.close()

            self.assertIn(old_date, dates)
            self.assertIn(recent_date, dates)


if __name__ == "__main__":
    unittest.main()
