"""
Valuation module for Macro Analysis Engine.
Calculates and tracks Macro & Sector level P/E (Trailing & Forward) and EV/EBITDA multiples.
Defiant Gatekeeper Valuation Framework.
"""

import logging
import yfinance as yf
import pandas as pd
from typing import Dict, List, Any, Optional
from storage import MacroStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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

# Historical Valuation Multiple Norms (Defiant Gatekeeper Benchmarks)
HISTORICAL_NORMS = {
    "S&P 500 (SPY)": {"fair_pe": 18.0, "fair_ev_ebitda": 13.0},
    "Technology (XLK)": {"fair_pe": 24.0, "fair_ev_ebitda": 18.0},
    "Financials (XLF)": {"fair_pe": 13.0, "fair_ev_ebitda": 10.0},
    "Healthcare (XLV)": {"fair_pe": 18.0, "fair_ev_ebitda": 14.0},
    "Energy (XLE)": {"fair_pe": 12.0, "fair_ev_ebitda": 6.5},
    "Industrials (XLI)": {"fair_pe": 19.0, "fair_ev_ebitda": 13.0},
    "Consumer Discretionary (XLY)": {"fair_pe": 22.0, "fair_ev_ebitda": 16.0},
    "Consumer Staples (XLP)": {"fair_pe": 20.0, "fair_ev_ebitda": 14.0}
}


class SectorValuationEngine:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()

    def calculate_sector_valuations(self) -> List[Dict[str, Any]]:
        """
        Calculates trailing P/E, forward P/E, and EV/EBITDA multiples for broad market & sectors.
        Classifies valuation posture relative to historical norms.
        """
        sector_results = []

        for sector, tickers in SECTOR_CONSTITUENTS.items():
            pes, fpes, eves = [], [], []

            for t in tickers:
                try:
                    info = yf.Ticker(t).info
                    pe = info.get("trailingPE")
                    fpe = info.get("forwardPE")
                    eve = info.get("enterpriseToEbitda")

                    if pe and 0 < pe < 200:
                        pes.append(pe)
                    if fpe and 0 < fpe < 200:
                        fpes.append(fpe)
                    if eve and 0 < eve < 200:
                        eves.append(eve)
                except Exception as e:
                    logging.debug(f"Error fetching info for {t}: {e}")

            avg_pe = sum(pes) / len(pes) if pes else None
            avg_fpe = sum(fpes) / len(fpes) if fpes else None
            avg_eve = sum(eves) / len(eves) if eves else None

            # Valuation Assessment
            norms = HISTORICAL_NORMS.get(sector, {"fair_pe": 18.0, "fair_ev_ebitda": 13.0})
            assessment = "Fair Value"
            
            if avg_fpe:
                if avg_fpe > norms["fair_pe"] * 1.25:
                    assessment = "Overvalued / Rich Multiple"
                elif avg_fpe < norms["fair_pe"] * 0.85:
                    assessment = "Undervalued / Discount Multiple"
                else:
                    assessment = "Fairly Valued"

            res = {
                "sector": sector,
                "trailing_pe": round(avg_pe, 2) if avg_pe else None,
                "forward_pe": round(avg_fpe, 2) if avg_fpe else None,
                "ev_ebitda": round(avg_eve, 2) if avg_eve else None,
                "fair_pe_norm": norms["fair_pe"],
                "fair_ev_ebitda_norm": norms["fair_ev_ebitda"],
                "valuation_status": assessment
            }
            sector_results.append(res)

        return sector_results

    def save_valuations_to_storage(self, sector_results: List[Dict[str, Any]]):
        """Save valuation observations to SQLite storage."""
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
        for res in sector_results:
            key_pe = f"val_pe_{res['sector'].split()[0].lower()}"
            key_eve = f"val_eve_{res['sector'].split()[0].lower()}"
            
            if res["forward_pe"]:
                df_pe = pd.DataFrame([{"date": today_str, "value": res["forward_pe"]}])
                self.storage.save_observations(key_pe, df_pe)
            if res["ev_ebitda"]:
                df_eve = pd.DataFrame([{"date": today_str, "value": res["ev_ebitda"]}])
                self.storage.save_observations(key_eve, df_eve)
