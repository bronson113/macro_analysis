"""
Pre-fetches FRED CSV series data using a 2-step curl Akamai cookie handshake
to bypass bot protections before running the main analysis pipeline.
"""
import os
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from config import ACTIVE_FRED_SERIES_KEYS, FRED_SERIES, CACHE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _download_one(key, series_info, fred_cache, cookie_file):
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
            return True
        logging.warning(f"Invalid content for {series_id}: {start[:100]}")
    else:
        logging.warning(f"Failed curl prefetch for {series_id}: returncode={res.returncode}, stderr={res.stderr.decode()}")

    return False


def prefetch_all(cache_dir=CACHE_DIR, max_workers=None):
    fred_cache = Path(cache_dir) / "fred"
    fred_cache.mkdir(parents=True, exist_ok=True)
    
    fetch_all_series = os.getenv("MACRO_FETCH_ALL_SERIES") == "1"
    fred_series = FRED_SERIES if fetch_all_series else {
        key: info
        for key, info in FRED_SERIES.items()
        if key in ACTIVE_FRED_SERIES_KEYS
    }

    worker_count = max_workers
    if worker_count is None:
        worker_count = int(os.getenv("MACRO_FRED_PREFETCH_WORKERS", "6"))
    worker_count = max(1, min(len(fred_series), worker_count))

    successes = 0
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_key = {}
        for key, series_info in fred_series.items():
            cookie_file = f"/tmp/fred_prefetch_cookies_{series_info['id']}.txt"
            future = executor.submit(_download_one, key, series_info, fred_cache, cookie_file)
            future_to_key[future] = key

        for future in as_completed(future_to_key):
            try:
                if future.result():
                    successes += 1
            except Exception as e:
                logging.warning(f"FRED prefetch failed for {future_to_key[future]}: {e}")

    logging.info(f"FRED prefetch complete: {successes}/{len(fred_series)} series cached")
    return successes

if __name__ == "__main__":
    prefetch_all()
