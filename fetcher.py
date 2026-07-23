"""
Fetcher module for Macro Economic Analysis & Data Capture System.
Downloads macroeconomic series from FRED, Yahoo Finance, and macro news events.
Features exponential backoff retries and parallel execution for maximum resilience.
"""

import io
import json
import time
import logging
import urllib.request
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Tuple, Optional
from config import FRED_SERIES, YAHOO_TICKERS, LOG_DIR, configure_yfinance_cache
from storage import MacroStorage
from news_analyzer import MacroNewsAnalyzer

configure_yfinance_cache(yf)

logging.basicConfig(
    filename=LOG_DIR / "fetcher.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class MacroFetcher:
    CNN_FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()
        self.news_analyzer = MacroNewsAnalyzer(self.storage)
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MacroAnalysis/2.0"
        self._urlopen = urllib.request.urlopen

    def fetch_fred_series(self, key: str, series_info: Dict[str, Any], max_retries: int = 3) -> Tuple[int, Optional[str]]:
        """
        Fetches FRED economic series with exponential backoff retries and fallback series support.
        """
        series_id = series_info["id"]
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                with urllib.request.urlopen(url, timeout=25) as response:
                    csv_bytes = response.read()
                    df = pd.read_csv(io.BytesIO(csv_bytes))
                    
                if df.empty or len(df.columns) < 2:
                    fallback = series_info.get("fallback")
                    if fallback:
                        logging.info(f"Primary series {series_id} empty for {key}. Trying fallback {fallback}...")
                        series_info_fallback = dict(series_info, id=fallback)
                        series_info_fallback.pop("fallback", None)
                        return self.fetch_fred_series(key, series_info_fallback, max_retries=max_retries)
                    return 0, f"Empty CSV returned for {series_id}"

                date_col = df.columns[0]
                val_col = df.columns[1]
                
                df = df.rename(columns={date_col: "date", val_col: "value"})
                df = df[df["value"] != "."].copy()
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna(subset=["value"])
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                
                cutoff_date = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%d")
                df = df[df["date"] >= cutoff_date]
                
                count = self.storage.save_observations(key, df[["date", "value"]])
                logging.info(f"Successfully saved {count} records for FRED key: {key} ({series_id})")
                return count, None

            except Exception as e:
                last_exception = str(e)
                if attempt < max_retries:
                    sleep_time = 2 ** attempt
                    logging.warning(f"FRED fetch attempt {attempt} failed for {key} ({series_id}): {last_exception}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)

        err_msg = f"Failed to fetch FRED series {key} ({series_id}) after {max_retries} attempts: {last_exception}"
        logging.error(err_msg)
        return 0, err_msg

    def fetch_yahoo_ticker(self, key: str, ticker: str, max_retries: int = 2) -> Tuple[int, Optional[str]]:
        """
        Fetches Yahoo Finance market prices with retry logic.
        """
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                t = yf.Ticker(ticker)
                df = t.history(period="1y")
                if df.empty:
                    return 0, f"Empty history returned for ticker {ticker}"
                
                df = df.reset_index()
                date_col = "Date" if "Date" in df.columns else ("Datetime" if "Datetime" in df.columns else df.columns[0])
                df["date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
                df["value"] = df["Close"]
                
                df = df.dropna(subset=["value"])[["date", "value"]]
                count = self.storage.save_observations(key, df)
                logging.info(f"Successfully saved {count} records for Yahoo ticker: {key} ({ticker})")
                return count, None

            except Exception as e:
                last_exception = str(e)
                if attempt < max_retries:
                    time.sleep(1.5)

        err_msg = f"Failed to fetch Yahoo ticker {key} ({ticker}): {last_exception}"
        logging.error(err_msg)
        return 0, err_msg

    def fetch_cnn_fear_greed_index(self) -> Tuple[int, Optional[str]]:
        """Fetch CNN Fear & Greed Index and store the current 0-100 score."""
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.CNN_FEAR_GREED_URL}/{today}"
        request = urllib.request.Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Referer": "https://www.cnn.com/markets/fear-and-greed",
        })

        try:
            with self._urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))

            fg = payload.get("fear_and_greed") or {}
            score = fg.get("score")
            if score is None:
                return 0, "CNN Fear & Greed payload missing score"

            score = float(score)
            if score < 0 or score > 100:
                return 0, f"CNN Fear & Greed score outside 0-100 range: {score}"

            obs_date = today
            timestamp = fg.get("timestamp")
            if timestamp:
                try:
                    obs_date = pd.to_datetime(timestamp).strftime("%Y-%m-%d")
                except Exception:
                    obs_date = today

            df = pd.DataFrame([{"date": obs_date, "value": score}])
            count = self.storage.save_observations("cnn_fear_greed_index", df)
            logging.info("Successfully saved CNN Fear & Greed Index score: %.2f", score)
            return count, None
        except Exception as e:
            err_msg = f"Failed to fetch CNN Fear & Greed Index: {e}"
            logging.error(err_msg)
            return 0, err_msg

    def fetch_all(self) -> Dict[str, Any]:
        """
        Executes parallel resilient data fetching across all FRED series, Yahoo market prices, and news feeds.
        """
        total_records = 0
        success_keys = []
        failed_keys = []
        errors = {}

        print("--> Fetching FRED Economic Series (Resilient Parallel Pipeline)...")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future_to_key = {
                executor.submit(self.fetch_fred_series, key, s_info): key
                for key, s_info in FRED_SERIES.items()
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    count, err = future.result()
                    if err is None:
                        success_keys.append(key)
                        total_records += count
                    else:
                        failed_keys.append(key)
                        errors[key] = err
                except Exception as e:
                    failed_keys.append(key)
                    errors[key] = str(e)

        print("--> Fetching Yahoo Finance Market Prices...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_key = {
                executor.submit(self.fetch_yahoo_ticker, key, ticker): key
                for key, ticker in YAHOO_TICKERS.items()
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    count, err = future.result()
                    if err is None:
                        success_keys.append(key)
                        total_records += count
                    else:
                        failed_keys.append(key)
                        errors[key] = err
                except Exception as e:
                    failed_keys.append(key)
                    errors[key] = str(e)

        print("--> Fetching CNN Fear & Greed Index...")
        count, err = self.fetch_cnn_fear_greed_index()
        if err is None:
            success_keys.append("cnn_fear_greed_index")
            total_records += count
        else:
            failed_keys.append("cnn_fear_greed_index")
            errors["cnn_fear_greed_index"] = err

        print("--> Fetching Major Macro News & Event Feeds...")
        news_count = self.news_analyzer.fetch_and_store_news()
        print(f"--> Macro News Fetch Complete: {news_count} news events updated.")

        status = "SUCCESS" if len(failed_keys) == 0 else ("PARTIAL" if len(success_keys) > 0 else "FAILED")
        print(f"--> Fetch complete. Success: {len(success_keys)}, Failed: {len(failed_keys)}, Total Records: {total_records}, News Events: {news_count}")

        return {
            "status": status,
            "total_records": total_records,
            "news_events": news_count,
            "success_keys": success_keys,
            "failed_keys": failed_keys,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
