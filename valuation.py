"""
Valuation module for Macro Analysis Engine.
Calculates and tracks Macro & Sector level P/E (Trailing & Forward) and EV/EBITDA multiples.
Defiant Gatekeeper Valuation Framework.
"""

import math
import pandas as pd
from typing import Dict, List, Any, Optional
from storage import MacroStorage
from stock_data import get_many_ticker_info

# Sector Constituent Leaders for Macro & Sector Valuation Estimation
SECTOR_CONSTITUENTS = {
    "S&P 500 (SPY)": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "JPM", "UNH", "XOM"],
    "Technology (XLK)": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "QCOM", "ADBE"],
    "Financials (XLF)": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "SCHW"],
    "Healthcare (XLV)": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "PFE", "ABT"],
    "Energy (XLE)": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO"],
    "Industrials (XLI)": ["GE", "CAT", "RTX", "HON", "UNP", "BA", "DE", "LMT"],
    "Consumer Discretionary (XLY)": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG"],
    "Consumer Staples (XLP)": ["PG", "COST", "KO", "PEP", "WMT", "PM", "MDLZ", "CL"]
}

MULTIPLE_STORAGE_PREFIXES = {
    # V2 keys contain aggregate-fundamental values only; earlier keys stored
    # simple averages and cannot support comparable percentile histories.
    "trailing_pe": "val_v2_trailing_pe",
    "forward_pe": "val_v2_forward_pe",
    "ev_ebitda": "val_v2_ev_ebitda",
}


def _positive_finite(value: Any) -> Optional[float]:
    """Return a usable positive numeric value, or ``None`` for unavailable inputs."""
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    return numeric_value if math.isfinite(numeric_value) and numeric_value > 0 else None


def aggregate_sector_fundamentals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate quoted multiples through their implied earnings or EBITDA.

    A simple average gives a small constituent the same influence as a large
    constituent.  This instead sums each eligible numerator and its implied
    denominator, then derives the sector multiple from those totals.
    """
    metric_definitions = (
        ("trailing_pe", "marketCap", "trailingPE"),
        ("forward_pe", "marketCap", "forwardPE"),
        ("ev_ebitda", "enterpriseValue", "enterpriseToEbitda"),
    )
    result: Dict[str, Any] = {"coverage": {}}

    for metric, numerator_key, ratio_key in metric_definitions:
        total_numerator = 0.0
        eligible_numerator = 0.0
        implied_denominator = 0.0
        eligible_tickers = []
        excluded_tickers = []

        for row in rows:
            numerator = _positive_finite(row.get(numerator_key))
            ratio = _positive_finite(row.get(ratio_key))
            ticker = row.get("ticker")

            if numerator is not None:
                total_numerator += numerator

            if numerator is not None and ratio is not None:
                eligible_numerator += numerator
                implied_denominator += numerator / ratio
                eligible_tickers.append(ticker)
            else:
                excluded_tickers.append(ticker)

        result[metric] = (
            round(eligible_numerator / implied_denominator, 2)
            if implied_denominator > 0
            else None
        )
        result["coverage"][f"{metric}_pct"] = (
            round((eligible_numerator / total_numerator) * 100.0, 2)
            if total_numerator > 0
            else 0.0
        )
        result["coverage"][f"eligible_{metric}"] = eligible_tickers
        result["coverage"][f"excluded_{metric}"] = excluded_tickers

    return result


class SectorValuationEngine:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()

    @staticmethod
    def _storage_key(sector: str, multiple: str) -> str:
        """Return the durable observation key for a sector valuation multiple."""
        try:
            prefix = MULTIPLE_STORAGE_PREFIXES[multiple]
        except KeyError as exc:
            raise ValueError(f"unsupported valuation multiple: {multiple}") from exc
        opening_paren = sector.rfind("(")
        closing_paren = sector.rfind(")")
        identifier = (
            sector[opening_paren + 1:closing_paren]
            if opening_paren >= 0 and closing_paren > opening_paren
            else sector
        )
        normalized_identifier = "".join(
            character for character in identifier.lower() if character.isalnum()
        )
        return f"{prefix}_{normalized_identifier}"

    def classify_history(self, sector: str, multiple: str, value: Any) -> Dict[str, Any]:
        """Classify a current multiple against up to three years of stored history."""
        history = self.storage.get_indicator_series(
            self._storage_key(sector, multiple), limit=756
        ).copy()
        if not {"date", "value"}.issubset(history.columns):
            history = pd.DataFrame(columns=["date", "value"])

        history["date"] = pd.to_datetime(history["date"], errors="coerce")
        history["value"] = pd.to_numeric(history["value"], errors="coerce")
        history = history.dropna(subset=["date", "value"])
        history = history[history["value"].map(_positive_finite).notna()]

        sample_size = len(history)
        span_days = (
            int((history["date"].max() - history["date"].min()).days)
            if sample_size
            else 0
        )
        if sample_size < 60 or span_days < 180:
            return {
                "status": "Insufficient History",
                "percentile": None,
                "sample_size": sample_size,
                "span_days": span_days,
            }

        current_value = _positive_finite(value)
        if current_value is None:
            return {
                "status": "Unavailable Current Value",
                "percentile": None,
                "sample_size": sample_size,
                "span_days": span_days,
            }

        percentile = float((history["value"] <= current_value).sum() / sample_size * 100.0)
        if percentile <= 25.0:
            status = "Discounted Historical Range"
        elif percentile >= 75.0:
            status = "Rich Historical Range"
        else:
            status = "Typical Historical Range"
        return {
            "status": status,
            "percentile": percentile,
            "sample_size": sample_size,
            "span_days": span_days,
        }

    def calculate_sector_valuations(self) -> List[Dict[str, Any]]:
        """Calculate aggregate multiples and classify forward P/E against its history."""
        sector_results = []
        ticker_info = get_many_ticker_info([
            ticker
            for tickers in SECTOR_CONSTITUENTS.values()
            for ticker in tickers
        ])

        for sector, tickers in SECTOR_CONSTITUENTS.items():
            rows = []
            for ticker in tickers:
                info = ticker_info.get(ticker) or {}
                rows.append({**info, "ticker": ticker})

            aggregate = aggregate_sector_fundamentals(rows)
            history = self.classify_history(sector, "forward_pe", aggregate["forward_pe"])
            sector_results.append({
                "sector": sector,
                **aggregate,
                "history": history,
                "valuation_status": history["status"],
            })

        return sector_results

    def save_valuations_to_storage(self, sector_results: List[Dict[str, Any]]):
        """Save each positive aggregate multiple as a dated CSV observation."""
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
        for res in sector_results:
            for multiple in MULTIPLE_STORAGE_PREFIXES:
                value = _positive_finite(res.get(multiple))
                if value is not None:
                    observation = pd.DataFrame([{"date": today_str, "value": value}])
                    self.storage.save_observations(
                        self._storage_key(res["sector"], multiple), observation
                    )
