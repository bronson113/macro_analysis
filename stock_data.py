"""Shared yfinance helpers for stock-level valuation enrichment."""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any, Dict, List, Optional

import yfinance as yf

from config import configure_yfinance_cache

configure_yfinance_cache(yf)


@lru_cache(maxsize=256)
def get_ticker_info(ticker: str) -> Dict[str, Any]:
    """Return cached yfinance info for a ticker during a pipeline run."""
    return dict(yf.Ticker(ticker).info or {})


def clear_ticker_info_cache() -> None:
    """Clear the in-process ticker info cache."""
    get_ticker_info.cache_clear()


def get_many_ticker_info(tickers: List[str], max_workers: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """Warm and return cached ticker info for multiple symbols concurrently."""
    unique_tickers = list(dict.fromkeys(tickers))
    if not unique_tickers:
        return {}

    worker_count = max_workers
    if worker_count is None:
        worker_count = int(os.getenv("MACRO_STOCK_INFO_WORKERS", "8"))
    worker_count = max(1, min(len(unique_tickers), worker_count))

    results: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_ticker = {
            executor.submit(get_ticker_info, ticker): ticker
            for ticker in unique_tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                results[ticker] = future.result()
            except Exception:
                results[ticker] = {}

    return results
