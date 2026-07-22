"""
Storage module for Macro Analysis Data Capture System.
Manages SQLite database schema, data insertion, time series queries, daily snapshots, and news events.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import closing
from config import DB_PATH, FRED_SERIES, YAHOO_TICKERS


class MacroStorage:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize SQLite tables."""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            
            # Indicators Metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT,
                    frequency TEXT,
                    unit TEXT,
                    last_updated TIMESTAMP
                )
            """)

            # Raw Observations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS macro_observations (
                    indicator_key TEXT NOT NULL,
                    date TEXT NOT NULL,
                    value REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (indicator_key, date),
                    FOREIGN KEY (indicator_key) REFERENCES indicators (key)
                )
            """)

            # Daily Snapshots
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_snapshots (
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
                    housing_yoy REAL,
                    breakeven_10y REAL,
                    m2_yoy REAL,
                    policy_rate REAL,
                    policy_rate_change_30d REAL,
                    real_yield_10y REAL,
                    liquidity_regime TEXT,
                    yield_curve_regime TEXT,
                    credit_regime TEXT,
                    overall_regime TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # News & Major Events Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS macro_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    source TEXT,
                    link TEXT,
                    category TEXT,
                    impact_score REAL,
                    sentiment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Run Audit Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    records_updated INTEGER,
                    message TEXT
                )
            """)

            conn.commit()
            self._ensure_daily_snapshot_columns(conn)
            self._seed_indicator_metadata(conn)

    def _ensure_daily_snapshot_columns(self, conn):
        """Add newer snapshot columns when opening an older local database."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(daily_snapshots)")
        existing = {row[1] for row in cursor.fetchall()}
        for column_name, column_type in {
            "housing_yoy": "REAL",
            "breakeven_10y": "REAL",
            "m2_yoy": "REAL",
            "policy_rate": "REAL",
            "policy_rate_change_30d": "REAL",
            "real_yield_10y": "REAL",
        }.items():
            if column_name not in existing:
                cursor.execute(f"ALTER TABLE daily_snapshots ADD COLUMN {column_name} {column_type}")
        conn.commit()

    def _seed_indicator_metadata(self, conn):
        """Seed metadata for known FRED series and Yahoo tickers."""
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        for key, info in FRED_SERIES.items():
            cursor.execute("""
                INSERT OR REPLACE INTO indicators (key, name, source, category, frequency, last_updated)
                VALUES (?, ?, 'FRED', ?, ?, ?)
            """, (key, info['name'], self._categorize_key(key), info.get('frequency', 'daily'), now))
            
        for key, ticker in YAHOO_TICKERS.items():
            cursor.execute("""
                INSERT OR REPLACE INTO indicators (key, name, source, category, frequency, last_updated)
                VALUES (?, ?, 'YAHOO', 'Market Prices', 'daily', ?)
            """, (key, f"{key.upper()} ({ticker})", now))
            
        conn.commit()

    def _categorize_key(self, key: str) -> str:
        if any(k in key for k in ['fed', 'repo', 'tga', 'm2', 'deposits', 'effr', 'dff']):
            return "Federal Reserve & Liquidity"
        elif any(k in key for k in ['treasury', 'spread']):
            return "Rates & Yield Curve"
        elif any(k in key for k in ['oas', 'yield', 'chicago_fed']):
            return "Credit & Financial Conditions"
        elif any(k in key for k in ['payrolls', 'unemployment', 'claims', 'wage', 'openings']):
            return "Labor Market"
        elif any(k in key for k in ['cpi', 'pce', 'breakeven']):
            return "Inflation"
        else:
            return "Economic Growth"

    def save_observations(self, indicator_key: str, df_obs: pd.DataFrame) -> int:
        if df_obs.empty:
            return 0

        df_to_save = df_obs.copy()
        df_to_save['indicator_key'] = indicator_key
        df_to_save['updated_at'] = datetime.now().isoformat()

        records = df_to_save[['indicator_key', 'date', 'value', 'updated_at']].to_dict('records')
        
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO macro_observations (indicator_key, date, value, updated_at)
                VALUES (:indicator_key, :date, :value, :updated_at)
            """, records)
            
            cursor.execute("""
                UPDATE indicators SET last_updated = ? WHERE key = ?
            """, (datetime.now().isoformat(), indicator_key))
            
            conn.commit()
            return len(records)

    def save_news_events(self, news_items: List[Dict[str, Any]]) -> int:
        """Save a list of news event dictionaries into macro_news table."""
        if not news_items:
            return 0

        count = 0
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            for item in news_items:
                # Deduplicate by title & date
                cursor.execute("""
                    SELECT id FROM macro_news WHERE title = ? AND date = ?
                """, (item["title"], item["date"]))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO macro_news (date, title, summary, source, link, category, impact_score, sentiment)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.get("date", datetime.now().strftime("%Y-%m-%d")),
                        item["title"],
                        item.get("summary", ""),
                        item.get("source", "News"),
                        item.get("link", ""),
                        item.get("category", "General Macro"),
                        item.get("impact_score", 0.0),
                        item.get("sentiment", "Neutral")
                    ))
                    count += 1
            conn.commit()
        return count

    def get_recent_news(self, limit: int = 15) -> List[Dict[str, Any]]:
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM macro_news ORDER BY date DESC, id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_latest_observation(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, value, updated_at 
                FROM macro_observations 
                WHERE indicator_key = ? 
                ORDER BY date DESC LIMIT 1
            """, (indicator_key,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_indicator_series(self, indicator_key: str, limit: int = 365) -> pd.DataFrame:
        with closing(self.get_connection()) as conn:
            query = """
                SELECT date, value 
                FROM macro_observations 
                WHERE indicator_key = ? 
                ORDER BY date DESC LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(indicator_key, limit))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
            return df

    def save_daily_snapshot(self, snapshot_data: Dict[str, Any]):
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            columns = list(snapshot_data.keys())
            placeholders = ", ".join([":" + col for col in columns])
            col_names = ", ".join(columns)
            
            query = f"""
                INSERT OR REPLACE INTO daily_snapshots ({col_names})
                VALUES ({placeholders})
            """
            cursor.execute(query, snapshot_data)
            conn.commit()

    def get_recent_snapshots(self, limit: int = 30) -> pd.DataFrame:
        with closing(self.get_connection()) as conn:
            df = pd.read_sql_query("""
                SELECT * FROM daily_snapshots ORDER BY date DESC LIMIT ?
            """, conn, params=(limit,))
            return df

    def log_run(self, status: str, records_updated: int, message: str):
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO run_logs (status, records_updated, message)
                VALUES (?, ?, ?)
            """, (status, records_updated, message))
            conn.commit()
