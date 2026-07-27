"""
Pre-fetches FRED CSV series data using a 2-step curl Akamai cookie handshake
to bypass bot protections before running the main analysis pipeline.
"""
import time
import logging
import subprocess
from pathlib import Path
from config import FRED_SERIES, CACHE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def prefetch_all():
    fred_cache = CACHE_DIR / "fred"
    fred_cache.mkdir(parents=True, exist_ok=True)
    
    cookie_file = "/tmp/fred_prefetch_cookies.txt"
    
    for key, series_info in FRED_SERIES.items():
        series_id = series_info["id"]
        out_file = fred_cache / f"{series_id}.csv"
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        
        logging.info(f"Pre-fetching {key} ({series_id})...")
        
        # Step 1: HEAD request to obtain Akamai Bot Manager cookies
        subprocess.run(
            ["curl", "--http1.1", "-sI", "-c", cookie_file, url],
            capture_output=True, timeout=10
        )
        
        # Step 2: GET request using cookies to download CSV
        res = subprocess.run(
            ["curl", "--http1.1", "-s", "-L", "-b", cookie_file, "-c", cookie_file, url],
            capture_output=True, timeout=20
        )
        
        if res.returncode == 0 and len(res.stdout) > 0:
            start = res.stdout[:200].lower()
            if b"date" in start or b"observation_date" in start:
                out_file.write_bytes(res.stdout)
                logging.info(f"Successfully cached {series_id}.csv ({len(res.stdout)} bytes)")
            else:
                logging.warning(f"Invalid content for {series_id}: {start[:100]}")
        else:
            logging.warning(f"Failed curl prefetch for {series_id}: returncode={res.returncode}, stderr={res.stderr.decode()}")
            
        time.sleep(0.1)

if __name__ == "__main__":
    prefetch_all()
