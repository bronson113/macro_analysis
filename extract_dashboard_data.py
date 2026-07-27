import json
import logging
import math
import pandas as pd
import os
from config import DASHBOARD_HISTORY_DAYS, SNAPSHOTS_CSV, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _sanitize(val):
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val

def extract_history():
    """Extract historical daily snapshots for dashboard timeline charts."""
    if not os.path.exists(SNAPSHOTS_CSV):
        logging.warning("No snapshots CSV found.")
        return

    try:
        df = pd.read_csv(SNAPSHOTS_CSV)
        if df.empty:
            logging.info("Snapshots CSV is empty.")
            return

        # Fetch up to the last ten years of data, ordered chronologically.
        df_sorted = df.sort_values(by='date', ascending=False).head(DASHBOARD_HISTORY_DAYS)
        
        # Keep only required columns, if they exist
        required_cols = [
            'date', 'net_liquidity', 'fed_assets', 'tga', 'rrp', 
            'treasury_10y', 'treasury_2y', 'spread_10y_2y', 'high_yield_oas', 
            'sp500', 'vix', 'dxy', 'cpi_yoy', 'policy_rate', 'real_yield_10y'
        ]
        available_cols = [c for c in required_cols if c in df_sorted.columns]
        df_sorted = df_sorted[available_cols]

        # Reverse to have chronological order for graphs (oldest to newest)
        history = df_sorted.sort_values(by='date', ascending=True).to_dict('records')
        history = [{k: _sanitize(v) for k, v in record.items()} for record in history]
        
        history_path = OUTPUT_DIR / "history.json"
        
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            
        logging.info(f"Successfully extracted {len(history)} historical records to {history_path}")
        
    except Exception as e:
        logging.error(f"Failed to extract history: {e}")

if __name__ == "__main__":
    extract_history()
