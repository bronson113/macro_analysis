"""Focused, business-model comparable cohorts for constituent valuation analysis."""

from typing import Dict, Tuple


PEER_COHORTS: Dict[str, Tuple[str, ...]] = {
    "Memory": ("MU", "WDC", "STX"),
    "Fabless Accelerators": ("NVDA", "AMD", "AVGO", "QCOM"),
    "Foundries": ("TSM", "INTC", "GFS"),
    "Semiconductor Equipment": ("ASML", "AMAT", "LRCX", "KLAC", "TER"),
    "Software & Cloud": ("MSFT", "ORCL", "CRM", "ADBE"),
    "Consumer Hardware & Platforms": ("AAPL", "GOOGL", "META"),
    "Banks": ("JPM", "BAC", "WFC", "C", "SCHW"),
    "Capital Markets": ("GS", "MS", "BLK", "AXP"),
    "Managed Care": ("UNH", "HUM", "ELV", "CI", "CVS"),
    "Pharmaceuticals": ("JNJ", "LLY", "ABBV", "MRK", "PFE"),
    "Energy Producers": ("XOM", "CVX", "COP", "EOG"),
    "Refiners": ("MPC", "PSX", "VLO"),
    "Industrial Machinery": ("GE", "CAT", "HON", "DE", "ROK"),
    "Retail & Consumer": ("AMZN", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG"),
    "Physical AI & Robotics": ("TSLA", "SYM", "ISRG"),
    "Downstream Power & Grid": ("CEG", "VST", "ETN", "GEV"),
    "Datacenter Cooling": ("VRT", "MOD", "SMCI"),
    "Critical Minerals": ("FCX", "MP"),
}


def ticker_to_cohort() -> Dict[str, str]:
    """Return the one permitted primary cohort for every tracked ticker."""

    mapping: Dict[str, str] = {}
    for cohort, tickers in PEER_COHORTS.items():
        for ticker in tickers:
            if ticker in mapping:
                raise ValueError(
                    f"Ticker {ticker} belongs to both {mapping[ticker]} and {cohort}."
                )
            mapping[ticker] = cohort
    return mapping
