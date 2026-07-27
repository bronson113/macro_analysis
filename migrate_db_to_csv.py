import sqlite3
import pandas as pd
from pathlib import Path
from config import DB_PATH, DATA_DIR

def migrate():
    db_file = Path(DB_PATH)
    if not db_file.exists():
        print(f"No database found at {db_file}. Skipping migration.")
        return

    print(f"Connecting to {db_file}...")
    conn = sqlite3.connect(db_file)
    
    tables = ["indicators", "macro_observations", "daily_snapshots", "macro_news", "run_logs"]
    
    for table in tables:
        try:
            print(f"Exporting table '{table}'...")
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            csv_path = DATA_DIR / f"{table}.csv"
            df.to_csv(csv_path, index=False)
            print(f"Successfully exported {len(df)} rows to {csv_path}")
        except Exception as e:
            print(f"Error exporting table {table}: {e}")
            
    conn.close()
    print("Migration complete. You can safely remove macro_data.db once confirmed.")

if __name__ == "__main__":
    migrate()
