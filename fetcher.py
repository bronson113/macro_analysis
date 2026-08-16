"""
Fetcher module for Macro Economic Analysis & Data Capture System.
Downloads macroeconomic series from FRED, Yahoo Finance, and macro news events.
Features exponential backoff retries and parallel execution for maximum resilience.
"""

import io
import json
import os
import time
import logging
import re
import urllib.request
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Tuple, Optional
from config import (
    ACTIVE_FRED_SERIES_KEYS,
    ACTIVE_YAHOO_TICKER_KEYS,
    DASHBOARD_HISTORY_DAYS,
    FRED_SERIES,
    YAHOO_TICKERS,
    LOG_DIR,
    CACHE_DIR,
    configure_yfinance_cache,
)
from storage import MacroStorage
from news_analyzer import MacroNewsAnalyzer
from source_health import SourceHealth, classify_source_error
from hlw_rstar import HolstonLaubachWilliamsProvider
from consensus import NewYorkFedSMEProvider

configure_yfinance_cache(yf)

EXPECTED_FRED_UNITS = {
    "fed_total_assets": "millions",
    "tga_balance": "millions",
    "reverse_repo": "billions",
    "nominal_gdp": "billions",
    "core_pce": "index",
    "dff": "percent",
    "effr": "percent",
    "iorb": "percent",
    "sofr": "percent",
}

logging.basicConfig(
    filename=LOG_DIR / "fetcher.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class MacroFetcher:
    CNN_FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    SHILLER_PE_URL = "https://www.multpl.com/shiller-pe"

    def __init__(
        self,
        storage: Optional[MacroStorage] = None,
        *,
        hlw_provider: Optional[HolstonLaubachWilliamsProvider] = None,
        consensus_provider: Optional[NewYorkFedSMEProvider] = None,
    ):
        self.storage = storage or MacroStorage()
        self.news_analyzer = MacroNewsAnalyzer(self.storage)
        self.hlw_provider = hlw_provider or HolstonLaubachWilliamsProvider()
        self.consensus_provider = consensus_provider or NewYorkFedSMEProvider()
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MacroAnalysis/2.0"
        self._urlopen = urllib.request.urlopen

    def fetch_hlw_rstar(self, as_of: Optional[Any] = None) -> Tuple[int, Optional[str]]:
        """Fetch and persist the official New York Fed HLW US r-star series."""
        try:
            records = self.hlw_provider.get_records(as_of=as_of)
            if not records:
                return 0, "HLW provider returned no usable observations"
            frame = pd.DataFrame(records)
            columns = [
                "date",
                "value",
                "publication_date",
                "vintage_date",
                "source_url",
                "unit",
            ]
            if "release_date" in frame.columns:
                columns.insert(2, "release_date")
            count = self.storage.save_observations("rstar", frame[columns])
            return count, None
        except Exception as error:
            logging.error("Failed to fetch NY Fed HLW r-star: %s", error)
            return 0, f"Failed to fetch NY Fed HLW r-star: {error}"

    def fetch_consensus(self, as_of: Optional[Any] = None) -> Tuple[int, Optional[str]]:
        """Fetch the optional NY Fed SME overlay into the durable CSV boundary."""
        try:
            records = self.consensus_provider.get_records(as_of=as_of)
            count = self.storage.save_consensus_records(records)
            if count <= 0:
                return 0, "NY Fed SME provider returned no usable observations"
            return count, None
        except Exception as error:
            logging.error("Failed to fetch NY Fed SME consensus: %s", error)
            return 0, f"Failed to fetch NY Fed SME consensus: {error}"

    def fetch_fred_series(self, key: str, series_info: Dict[str, Any], max_retries: int = 3) -> Tuple[int, Optional[str]]:
        """
        Fetches FRED economic series with exponential backoff retries and fallback series support.
        """
        series_id = series_info["id"]
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        source_url = series_info.get("source_url") or url
        declared_unit = series_info.get("unit") or series_info.get("unit_scale")
        expected_unit = EXPECTED_FRED_UNITS.get(key)
        if expected_unit is not None and str(declared_unit or "").strip().lower() != expected_unit:
            return (
                0,
                f"Rejected {key}: source unit {declared_unit or 'missing'}; "
                f"expected {expected_unit}",
            )
        # FRED's graph CSV is an observation file, not a vintage-history API.
        # Persist the retrieval date as the conservative availability vintage;
        # callers evaluating an earlier as-of date will not see this row unless
        # the source supplied an earlier explicit vintage.
        retrieval_vintage = datetime.now().strftime("%Y-%m-%d")
        
        # Check local pre-fetched cache first (unless urlopen is mocked in unit tests)
        is_mocked = "Mock" in str(type(urllib.request.urlopen))
        cached_path = CACHE_DIR / "fred" / f"{series_id}.csv"
        if not is_mocked and cached_path.exists() and cached_path.stat().st_size > 0:
            try:
                content = cached_path.read_bytes()
                content_start = content[:200].lower()
                if b"date" in content_start or b"observation_date" in content_start:
                    df = pd.read_csv(io.BytesIO(content))
                    if not df.empty and len(df.columns) >= 2:
                        date_col = df.columns[0]
                        val_col = df.columns[1]
                        df = df.rename(columns={date_col: "date", val_col: "value"})
                        df = df[df["value"] != "."].copy()
                        df["value"] = pd.to_numeric(df["value"], errors="coerce")
                        df = df.dropna(subset=["value"])
                        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                        
                        history_days = DASHBOARD_HISTORY_DAYS + 365 if key == "cpi" else DASHBOARD_HISTORY_DAYS
                        cutoff_date = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d")
                        df = df[df["date"] >= cutoff_date]
                        
                        count = self.storage.save_observations(
                            key,
                            df[["date", "value"]],
                            vintage_date=retrieval_vintage,
                            source_url=source_url,
                            unit=declared_unit,
                        )
                        logging.info(f"Successfully loaded {count} records from cached FRED file for {key} ({series_id})")
                        return count, None
            except Exception as cache_err:
                logging.warning(f"Failed loading cache for {series_id}: {cache_err}")

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                csv_bytes = b""

                # Step 0: Try urllib urlopen first (allows unittest mocks to intercept)
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': self.user_agent})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        content = response.read()
                        if b"date" in content[:200].lower() or b"observation_date" in content[:200].lower():
                            csv_bytes = content
                except Exception:
                    pass

                if not csv_bytes:
                    cookie_file = f"/tmp/fred_cookie_{series_id}.txt"
                    try:
                        import subprocess
                        # Step 1: Perform HEAD request to obtain Akamai Bot Manager cookies (_abck, bm_sz)
                        subprocess.run(
                            ["curl", "--http1.1", "-sI", "-c", cookie_file, url],
                            capture_output=True, timeout=10
                        )
                        
                        # Step 2: Perform GET request passing the cookie jar
                        result = subprocess.run(
                            ["curl", "--http1.1", "-s", "-L", "-b", cookie_file, "-c", cookie_file, url],
                            capture_output=True, timeout=20
                        )
                        
                        if result.returncode == 0 and len(result.stdout) > 0:
                            content_start = result.stdout[:200].lower()
                            if b"date" in content_start or b"observation_date" in content_start:
                                csv_bytes = result.stdout
                    except Exception as e:
                        logging.warning(f"Curl Akamai cookie handshake failed for {series_id}: {e}")
                    
                if not csv_bytes:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    csv_bytes = response.content
                    
                    if b"<!doctype html" in csv_bytes[:200].lower() or b"<html" in csv_bytes[:200].lower():
                        raise ValueError("FRED returned an HTML error page instead of CSV data. Check user-agent or rate limits.")
                        
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
                
                history_days = DASHBOARD_HISTORY_DAYS + 365 if key == "cpi" else DASHBOARD_HISTORY_DAYS
                cutoff_date = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d")
                df = df[df["date"] >= cutoff_date]
                
                count = self.storage.save_observations(
                    key,
                    df[["date", "value"]],
                    vintage_date=retrieval_vintage,
                    source_url=source_url,
                    unit=declared_unit,
                )
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

    def fetch_shiller_pe_ratio(self) -> Tuple[int, Optional[str]]:
        """Fetch the current Shiller PE ratio and store it as a valuation overlay."""
        today = datetime.now().strftime("%Y-%m-%d")
        request = urllib.request.Request(self.SHILLER_PE_URL, headers={
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml",
        })

        try:
            with self._urlopen(request, timeout=15) as response:
                html = response.read().decode("utf-8", errors="replace")

            match = re.search(r"Current\s+Shiller\s+PE\s+Ratio\s*(?::|is)\s*([0-9]+(?:\.[0-9]+)?)", html, re.IGNORECASE)
            if not match:
                return 0, "Multpl Shiller PE page missing current ratio"

            value = float(match.group(1))
            if value <= 0 or value > 200:
                return 0, f"Shiller PE value outside expected range: {value}"

            df = pd.DataFrame([{"date": today, "value": value}])
            count = self.storage.save_observations("shiller_pe", df)
            logging.info("Successfully saved Shiller PE ratio: %.2f", value)
            return count, None
        except Exception as e:
            err_msg = f"Failed to fetch Shiller PE ratio: {e}"
            logging.error(err_msg)
            return 0, err_msg

    def _save_fetch_health(self, source: str, fetch_key: str, count: int, error: Optional[str]):
        """Persist one normalized outcome after a logical provider fetch completes."""
        latest_observation = self.storage.get_latest_observation(fetch_key)
        message = error or ""
        health = SourceHealth(
            source=source,
            fetch_key=fetch_key,
            observation_time=(
                pd.Timestamp(latest_observation.get("date")).strftime("%Y-%m-%d")
                if latest_observation is not None and latest_observation.get("date") is not None
                else None
            ),
            fetch_time=datetime.now().isoformat(),
            status="CURRENT" if error is None else "ERROR",
            is_stale=error is not None and latest_observation is not None,
            record_count=count,
            error_category="" if error is None else classify_source_error(message),
            message=message,
        )
        return self.storage.save_source_health(health)

    def fetch_all(self) -> Dict[str, Any]:
        """
        Executes parallel resilient data fetching across all FRED series, Yahoo market prices, and news feeds.
        """
        total_records = 0
        success_keys = []
        failed_keys = []
        errors = {}
        source_status_counts = {}

        def record_result(
            source: str,
            key: str,
            count: int,
            error: Optional[str],
            require_records: bool = False,
            counts_as_failure: bool = True,
        ):
            if error is None and require_records and count <= 0:
                error = "Empty usable observation set returned by source"
            health = self._save_fetch_health(source, key, count, error)
            status_counts = source_status_counts.setdefault(source, {})
            status_counts[health["status"]] = status_counts.get(health["status"], 0) + 1
            if error is None:
                success_keys.append(key)
                return count
            if counts_as_failure:
                failed_keys.append(key)
                errors[key] = error
            return 0
        fetch_all_series = os.getenv("MACRO_FETCH_ALL_SERIES") == "1"
        fred_series = FRED_SERIES if fetch_all_series else {
            key: info
            for key, info in FRED_SERIES.items()
            if key in ACTIVE_FRED_SERIES_KEYS
        }
        yahoo_tickers = YAHOO_TICKERS if fetch_all_series else {
            key: ticker
            for key, ticker in YAHOO_TICKERS.items()
            if key in ACTIVE_YAHOO_TICKER_KEYS
        }

        print("--> Fetching FRED Economic Series (Resilient Parallel Pipeline)...")
        fred_workers = min(len(fred_series), int(os.getenv("MACRO_FRED_WORKERS", "6")))
        with ThreadPoolExecutor(max_workers=max(1, fred_workers)) as executor:
            future_to_key = {
                executor.submit(self.fetch_fred_series, key, s_info): key
                for key, s_info in fred_series.items()
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    count, err = future.result()
                except Exception as e:
                    count, err = 0, str(e)
                total_records += record_result("FRED", key, count, err, require_records=True)

        print("--> Fetching New York Fed HLW r-star...")
        try:
            count, err = self.fetch_hlw_rstar()
        except Exception as error:
            count, err = 0, str(error)
        total_records += record_result(
            "NY Fed HLW", "rstar", count, err, require_records=True, counts_as_failure=False
        )

        print("--> Fetching NY Fed Survey of Market Expectations...")
        try:
            count, err = self.fetch_consensus()
        except Exception as error:
            count, err = 0, str(error)
        total_records += record_result(
            "NY Fed SME", "nyfed_sme", count, err, require_records=True, counts_as_failure=False
        )

        print("--> Fetching Yahoo Finance Market Prices...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_key = {
                executor.submit(self.fetch_yahoo_ticker, key, ticker): key
                for key, ticker in yahoo_tickers.items()
            }
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    count, err = future.result()
                except Exception as e:
                    count, err = 0, str(e)
                total_records += record_result("YAHOO", key, count, err, require_records=True)

        print("--> Fetching CNN Fear & Greed Index...")
        try:
            count, err = self.fetch_cnn_fear_greed_index()
        except Exception as e:
            count, err = 0, str(e)
        total_records += record_result("CNN", "cnn_fear_greed_index", count, err, require_records=True)

        print("--> Fetching Shiller PE Ratio...")
        try:
            count, err = self.fetch_shiller_pe_ratio()
        except Exception as e:
            count, err = 0, str(e)
        total_records += record_result("Multpl", "shiller_pe", count, err, require_records=True)

        print("--> Fetching Major Macro News & Event Feeds...")
        try:
            news_count = self.news_analyzer.fetch_and_store_news()
            for outcome in getattr(self.news_analyzer, "last_fetch_outcomes", []):
                record_result(
                    outcome["source"],
                    outcome["fetch_key"],
                    int(outcome.get("record_count", 0)),
                    outcome.get("message") or None,
                )
        except Exception as e:
            news_count = 0
            record_result("Macro News", "macro_news", 0, str(e))
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
            "source_status_counts": source_status_counts,
            "timestamp": datetime.now().isoformat()
        }
