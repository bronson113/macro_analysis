"""
Storage module for Macro Analysis Data Capture System.
Manages data insertion, time series queries, daily snapshots, and news events using CSV files via pandas.
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import (
    FRED_SERIES, YAHOO_TICKERS, MARKET_SENTIMENT_INDICATORS,
    INDICATORS_CSV, OBSERVATIONS_CSV, SNAPSHOTS_CSV, NEWS_CSV, RUN_LOGS_CSV
)


class MacroStorage:
    def __init__(
        self,
        indicators_csv=INDICATORS_CSV,
        observations_csv=OBSERVATIONS_CSV,
        snapshots_csv=SNAPSHOTS_CSV,
        news_csv=NEWS_CSV,
        run_logs_csv=RUN_LOGS_CSV
    ):
        self.indicators_csv = str(indicators_csv)
        self.observations_csv = str(observations_csv)
        self.snapshots_csv = str(snapshots_csv)
        self.news_csv = str(news_csv)
        self.run_logs_csv = str(run_logs_csv)
        
        self._init_csvs()

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
            pd.DataFrame(columns=['id', 'date', 'title', 'summary', 'source', 'link', 'category', 'impact_score', 'sentiment', 'created_at']).to_csv(self.news_csv, index=False)
            
        # Run logs
        if not os.path.exists(self.run_logs_csv):
            pd.DataFrame(columns=['id', 'run_time', 'status', 'records_updated', 'message']).to_csv(self.run_logs_csv, index=False)

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
            df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=['key'], keep='last')
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

        df_to_save = df_obs.copy()
        df_to_save['indicator_key'] = indicator_key
        df_to_save['updated_at'] = datetime.now().isoformat()
        df_to_save = df_to_save[['indicator_key', 'date', 'value', 'updated_at']]

        df_existing = pd.read_csv(self.observations_csv)
        df_combined = pd.concat([df_existing, df_to_save])
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
                'impact_score': item.get("impact_score", 0.0),
                'sentiment': item.get("sentiment", "Neutral"),
                'created_at': datetime.now().isoformat()
            })
            
        df_new = pd.DataFrame(new_rows)
        # Deduplicate
        df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=['title', 'date'], keep='first')
        
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
        df = df.sort_values(by=['date', 'id'], ascending=[False, False]).head(limit)
        return df.to_dict('records')

    def get_latest_observation(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        df = pd.read_csv(self.observations_csv)
        df_filtered = df[df['indicator_key'] == indicator_key]
        if df_filtered.empty:
            return None
        df_sorted = df_filtered.sort_values(by='date', ascending=False)
        return df_sorted.iloc[0].to_dict()

    def get_indicator_series(self, indicator_key: str, limit: int = 365) -> pd.DataFrame:
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
            
        df_combined = pd.concat([df_existing, df_new])
        df_combined = df_combined.drop_duplicates(subset=['date'], keep='last')
        df_combined.to_csv(self.snapshots_csv, index=False)

    def get_recent_snapshots(self, limit: int = 30) -> pd.DataFrame:
        df = pd.read_csv(self.snapshots_csv)
        if df.empty:
            return df
        return df.sort_values(by='date', ascending=False).head(limit).reset_index(drop=True)

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
        df_combined = pd.concat([df_existing, df_new])
        df_combined.to_csv(self.run_logs_csv, index=False)
