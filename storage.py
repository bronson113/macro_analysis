"""
Storage module for Macro Analysis Data Capture System.
Manages data insertion, time series queries, daily snapshots, and news events using CSV files via pandas.
"""

import os
import threading
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from config import (
    FRED_SERIES, YAHOO_TICKERS, MARKET_SENTIMENT_INDICATORS,
    INDICATORS_CSV, OBSERVATIONS_CSV, SNAPSHOTS_CSV, NEWS_CSV, RUN_LOGS_CSV,
    SIGNALS_CSV,
)
from outcome_evaluation import SignalRecord


NEWS_COLUMNS = [
    'id', 'date', 'title', 'summary', 'source', 'link', 'category',
    'topic_tags', 'interpretation_status', 'published_at', 'retrieved_at',
    'impact_score', 'sentiment', 'created_at',
]

SIGNAL_COLUMNS = [
    "signal_date", "sector_group", "instrument", "benchmark", "posture", "score",
    "coverage_pct", "uncertainty_json", "factor_snapshot_json", "created_at",
]


class MacroStorage:
    def __init__(
        self,
        indicators_csv=INDICATORS_CSV,
        observations_csv=OBSERVATIONS_CSV,
        snapshots_csv=SNAPSHOTS_CSV,
        news_csv=NEWS_CSV,
        run_logs_csv=RUN_LOGS_CSV,
        signals_csv=None,
    ):
        self._lock = threading.Lock()
        self.indicators_csv = str(indicators_csv)
        self.observations_csv = str(observations_csv)
        self.snapshots_csv = str(snapshots_csv)
        self.news_csv = str(news_csv)
        self.run_logs_csv = str(run_logs_csv)
        self.signals_csv = str(
            signals_csv
            if signals_csv is not None
            else Path(self.snapshots_csv).parent / Path(SIGNALS_CSV).name
        )
        
        self._init_csvs()

    def _safe_concat(self, dfs: List[pd.DataFrame]) -> pd.DataFrame:
        non_empty = [df for df in dfs if df is not None and not df.empty and not df.dropna(how='all').empty]
        if not non_empty:
            return pd.DataFrame()
        if len(non_empty) == 1:
            return non_empty[0].copy()
        return pd.concat(non_empty)

    def _init_csvs(self):
        """Initialize CSV files with headers if they do not exist."""
        # Indicators
        if not os.path.exists(self.indicators_csv):
            pd.DataFrame(columns=['key', 'name', 'source', 'category', 'frequency', 'unit', 'last_updated']).to_csv(self.indicators_csv, index=False)
        
        # Observations
        if not os.path.exists(self.observations_csv):
            pd.DataFrame(columns=['indicator_key', 'date', 'value', 'updated_at']).to_csv(self.observations_csv, index=False)
        
        # Snapshots
        if not os.path.exists(self.snapshots_csv):
            pd.DataFrame(columns=[
                'date', 'net_liquidity', 'fed_assets', 'tga', 'rrp', 'treasury_10y', 'treasury_2y',
                'spread_10y_2y', 'high_yield_oas', 'vix', 'dxy', 'sp500', 'unemployment_rate',
                'cpi_yoy', 'housing_yoy', 'breakeven_10y', 'm2_yoy', 'policy_rate', 'policy_rate_change_30d',
                'real_yield_10y', 'cnn_fear_greed_index', 'shiller_pe', 'liquidity_regime',
                'yield_curve_regime', 'credit_regime', 'overall_regime', 'created_at'
            ]).to_csv(self.snapshots_csv, index=False)
            
        # News
        if not os.path.exists(self.news_csv):
            pd.DataFrame(columns=NEWS_COLUMNS).to_csv(self.news_csv, index=False)
            
        # Run logs
        if not os.path.exists(self.run_logs_csv):
            pd.DataFrame(columns=['id', 'run_time', 'status', 'records_updated', 'message']).to_csv(self.run_logs_csv, index=False)

        # Prospective evidence postures are a separate, point-in-time ledger.
        if not os.path.exists(self.signals_csv):
            pd.DataFrame(columns=SIGNAL_COLUMNS).to_csv(self.signals_csv, index=False)

        self._seed_indicator_metadata()

    def _seed_indicator_metadata(self):
        """Seed metadata for known FRED series and Yahoo tickers."""
        now = datetime.now().isoformat()
        
        records = []
        for key, info in FRED_SERIES.items():
            records.append({
                'key': key, 'name': info['name'], 'source': 'FRED',
                'category': self._categorize_key(key), 'frequency': info.get('frequency', 'daily'),
                'last_updated': now
            })
            
        for key, ticker in YAHOO_TICKERS.items():
            records.append({
                'key': key, 'name': f"{key.upper()} ({ticker})", 'source': 'YAHOO',
                'category': 'Market Prices', 'frequency': 'daily',
                'last_updated': now
            })

        for key, info in MARKET_SENTIMENT_INDICATORS.items():
            records.append({
                'key': key, 'name': info['name'], 'source': info['source'],
                'category': info.get('category', 'Market Sentiment'), 'frequency': info.get('frequency', 'daily'),
                'last_updated': now
            })
            
        df_new = pd.DataFrame(records)
        if os.path.exists(self.indicators_csv):
            df_existing = pd.read_csv(self.indicators_csv)
            # combine and drop duplicates keeping the newer ones
            df_combined = self._safe_concat([df_existing, df_new]).drop_duplicates(subset=['key'], keep='last')
        else:
            df_combined = df_new
            
        df_combined.to_csv(self.indicators_csv, index=False)

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
        elif any(k in key for k in ['fear_greed', 'sentiment']):
            return "Market Sentiment"
        else:
            return "Economic Growth"

    def save_observations(self, indicator_key: str, df_obs: pd.DataFrame) -> int:
        if df_obs.empty:
            return 0

        with self._lock:
            df_to_save = df_obs.copy()
            df_to_save['indicator_key'] = indicator_key
            df_to_save['updated_at'] = datetime.now().isoformat()
            df_to_save = df_to_save[['indicator_key', 'date', 'value', 'updated_at']]

            df_existing = pd.read_csv(self.observations_csv)
            df_combined = self._safe_concat([df_existing, df_to_save])
            df_combined = df_combined.drop_duplicates(subset=['indicator_key', 'date'], keep='last')
            df_combined.to_csv(self.observations_csv, index=False)
            
            # update indicators last_updated
            df_ind = pd.read_csv(self.indicators_csv)
            df_ind.loc[df_ind['key'] == indicator_key, 'last_updated'] = datetime.now().isoformat()
            df_ind.to_csv(self.indicators_csv, index=False)
            
            return len(df_to_save)

    def save_news_events(self, news_items: List[Dict[str, Any]]) -> int:
        """Save a list of news event dictionaries into macro_news table."""
        if not news_items:
            return 0
            
        df_existing = pd.read_csv(self.news_csv)
        max_id = df_existing['id'].max() if not df_existing.empty and pd.notna(df_existing['id'].max()) else 0

        new_rows = []
        for item in news_items:
            new_rows.append({
                'date': item.get("date", datetime.now().strftime("%Y-%m-%d")),
                'title': item["title"],
                'summary': item.get("summary", ""),
                'source': item.get("source", "News"),
                'link': item.get("link", ""),
                'category': item.get("category", "General Macro"),
                'topic_tags': self._serialize_topic_tags(item.get("topic_tags", [])),
                'interpretation_status': item.get("interpretation_status", "uninterpreted"),
                'published_at': item.get("published_at"),
                'retrieved_at': item.get("retrieved_at"),
                'impact_score': item.get("impact_score"),
                'sentiment': item.get("sentiment"),
                'created_at': datetime.now().isoformat()
            })
            
        df_new = pd.DataFrame(new_rows)
        # Deduplicate
        df_combined = self._safe_concat([df_existing, df_new]).drop_duplicates(subset=['title', 'date'], keep='first')
        
        # add ids to new ones if missing
        mask = df_combined['id'].isna()
        if mask.any():
            num_missing = mask.sum()
            df_combined.loc[mask, 'id'] = range(int(max_id) + 1, int(max_id) + 1 + num_missing)
            
        df_combined.to_csv(self.news_csv, index=False)
        return len(df_new) - (len(df_existing) + len(df_new) - len(df_combined))

    def get_recent_news(self, limit: int = 15) -> List[Dict[str, Any]]:
        df = pd.read_csv(self.news_csv)
        if df.empty:
            return []
        for column in ('topic_tags', 'interpretation_status', 'published_at', 'retrieved_at'):
            if column not in df.columns:
                df[column] = None
        df = df.sort_values(by=['date', 'id'], ascending=[False, False]).head(limit)
        records = df.to_dict('records')
        for record in records:
            record['topic_tags'] = self._deserialize_topic_tags(record.get('topic_tags'))
            if self._is_missing(record.get('interpretation_status')):
                record['interpretation_status'] = 'legacy_uninterpreted'
            for field in ('impact_score', 'sentiment', 'published_at', 'retrieved_at'):
                if self._is_missing(record.get(field)):
                    record[field] = None
        return records

    @staticmethod
    def _serialize_topic_tags(tags: Any) -> str:
        """Store tags as deterministic JSON instead of a Python representation."""
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = []
        if not isinstance(tags, (list, tuple, set)):
            tags = []
        normalized = sorted({str(tag) for tag in tags if tag is not None and str(tag)})
        return json.dumps(normalized, ensure_ascii=False, separators=(',', ':'))

    @staticmethod
    def _deserialize_topic_tags(value: Any) -> List[str]:
        if isinstance(value, (list, tuple, set)):
            return sorted({str(tag) for tag in value if tag is not None and str(tag)})
        if MacroStorage._is_missing(value):
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return sorted({str(tag) for tag in parsed if tag is not None and str(tag)})

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or (not isinstance(value, (list, tuple, set, dict)) and pd.isna(value))

    def get_latest_observation(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            df = pd.read_csv(self.observations_csv)
            df_filtered = df[df['indicator_key'] == indicator_key]
            if df_filtered.empty:
                return None
            df_sorted = df_filtered.sort_values(by='date', ascending=False)
            return df_sorted.iloc[0].to_dict()

    def get_indicator_series(self, indicator_key: str, limit: int = 365) -> pd.DataFrame:
        with self._lock:
            df = pd.read_csv(self.observations_csv)
            df_filtered = df[df['indicator_key'] == indicator_key]
            if df_filtered.empty:
                return pd.DataFrame(columns=['date', 'value'])
            df_sorted = df_filtered.sort_values(by='date', ascending=False).head(limit)
            df_sorted['date'] = pd.to_datetime(df_sorted['date'])
            return df_sorted.sort_values('date').reset_index(drop=True)[['date', 'value']]

    def save_daily_snapshot(self, snapshot_data: Dict[str, Any]):
        df_existing = pd.read_csv(self.snapshots_csv)
        df_new = pd.DataFrame([snapshot_data])
        if 'created_at' not in df_new.columns:
            df_new['created_at'] = datetime.now().isoformat()
            
        df_combined = self._safe_concat([df_existing, df_new])
        df_combined = df_combined.drop_duplicates(subset=['date'], keep='last')
        df_combined.to_csv(self.snapshots_csv, index=False)

    def get_recent_snapshots(self, limit: int = 30) -> pd.DataFrame:
        df = pd.read_csv(self.snapshots_csv)
        if df.empty:
            return df
        return df.sort_values(by='date', ascending=False).head(limit).reset_index(drop=True)

    def save_signal_assessments(
        self, assessments: List[Dict[str, Any]], signal_date: Optional[str] = None
    ) -> int:
        """Append current evidence assessments to the prospective signal ledger.

        The first captured assessment for a sector/date is immutable; later same-day
        reruns cannot replace the evidence available at that prospective signal time.
        Factor and uncertainty payloads use stable JSON so CSV diffs remain auditable.
        """
        if not assessments:
            return 0

        rows = []
        for assessment in assessments:
            candidate = dict(assessment)
            if signal_date is not None:
                candidate["signal_date"] = signal_date
            try:
                record = SignalRecord.from_mapping(candidate)
            except (TypeError, ValueError):
                continue
            values = record.to_mapping()
            rows.append({
                "signal_date": values["signal_date"],
                "sector_group": values["sector_group"],
                "instrument": values["instrument"],
                "benchmark": values["benchmark"],
                "posture": values["posture"],
                "score": values["score"],
                "coverage_pct": values["coverage_pct"],
                "uncertainty_json": self._stable_json(values["score_range"]),
                "factor_snapshot_json": self._stable_json(values["factor_snapshot"]),
                "created_at": datetime.now().isoformat(),
            })
        if not rows:
            return 0

        ledger_key = ["signal_date", "sector_group", "instrument", "benchmark"]
        with self._lock:
            df_existing = self._read_signal_ledger().drop_duplicates(
                subset=ledger_key, keep="first"
            )
            existing_keys = {
                tuple(row[column] for column in ledger_key)
                for row in df_existing.to_dict("records")
            }
            new_rows = []
            for row in rows:
                record_key = tuple(row[column] for column in ledger_key)
                if record_key not in existing_keys:
                    new_rows.append(row)
                    existing_keys.add(record_key)
            df_new = pd.DataFrame(new_rows, columns=SIGNAL_COLUMNS)
            df_combined = self._safe_concat([df_existing, df_new])
            df_combined.to_csv(self.signals_csv, index=False)
        return len(new_rows)

    def get_signal_assessments(self) -> List[Dict[str, Any]]:
        """Load prospective records with JSON fields restored to their public shapes."""
        with self._lock:
            df = self._read_signal_ledger()
        if df.empty:
            return []
        records = []
        for row in df.sort_values(["signal_date", "sector_group", "instrument"]).to_dict("records"):
            try:
                record = SignalRecord.from_mapping({
                    "signal_date": row.get("signal_date"),
                    "sector_group": row.get("sector_group"),
                    "instrument": row.get("instrument"),
                    "benchmark": row.get("benchmark"),
                    "posture": row.get("posture"),
                    "score": row.get("score"),
                    "coverage_pct": row.get("coverage_pct"),
                    "uncertainty": self._load_json(row.get("uncertainty_json"), []),
                    "factor_snapshot": self._load_json(row.get("factor_snapshot_json"), {}),
                })
            except (TypeError, ValueError):
                continue
            records.append(record.to_mapping())
        return records

    def _read_signal_ledger(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.signals_csv)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return pd.DataFrame(columns=SIGNAL_COLUMNS)
        for column in SIGNAL_COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df[SIGNAL_COLUMNS]

    @staticmethod
    def _stable_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _load_json(value: Any, fallback: Any) -> Any:
        if MacroStorage._is_missing(value):
            return fallback
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return fallback

    def log_run(self, status: str, records_updated: int, message: str):
        df_existing = pd.read_csv(self.run_logs_csv)
        max_id = df_existing['id'].max() if not df_existing.empty and pd.notna(df_existing['id'].max()) else 0
        new_row = {
            'id': int(max_id) + 1,
            'run_time': datetime.now().isoformat(),
            'status': status,
            'records_updated': records_updated,
            'message': message
        }
        df_new = pd.DataFrame([new_row])
        df_combined = self._safe_concat([df_existing, df_new])
        df_combined.to_csv(self.run_logs_csv, index=False)
