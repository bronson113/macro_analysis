import sqlite3
import json
import logging
from pathlib import Path
from config import DB_PATH, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def extract_history():
    """Extract historical daily snapshots for dashboard timeline charts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Fetch up to the last 365 days of data, ordered chronologically
        cursor.execute("""
            SELECT 
                date, 
                net_liquidity, 
                fed_assets, 
                tga, 
                rrp, 
                treasury_10y, 
                treasury_2y, 
                spread_10y_2y, 
                high_yield_oas, 
                sp500,
                vix,
                dxy,
                cpi_yoy,
                policy_rate,
                real_yield_10y
            FROM daily_snapshots 
            ORDER BY date DESC
            LIMIT 365
        """)
        
        rows = cursor.fetchall()
        
        # Reverse to have chronological order for graphs (oldest to newest)
        history = [dict(row) for row in rows][::-1]
        
        history_path = OUTPUT_DIR / "history.json"
        
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            
        logging.info(f"Successfully extracted {len(history)} historical records to {history_path}")
        
    except Exception as e:
        logging.error(f"Failed to extract history: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    extract_history()
