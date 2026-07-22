"""
AI & Physical AI (Robotics) Ecosystem Tracker Module.
Monitors valuations across 7 AI supply chain sub-groups:
1. AI Compute & Accelerators (NVDA, AMD, AVGO, TSM)
2. High-Bandwidth Memory (MU, WDC)
3. Physical AI & Robotics (TSLA, SYM, TER, ROK, ISRG)
4. Downstream Power & Grid Infrastructure (CEG, VST, ETN, GEV)
5. Datacenter Liquid Cooling (VRT, MOD, SMCI)
6. Semiconductor EUV Equipment (ASML, AMAT, LRCX, KLAC)
7. Critical Materials & Magnets (FCX, MP)
Includes ZeroDivisionError guards and robust fallback logic.
"""

import logging
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Any, Optional
from storage import MacroStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

AI_ECOSYSTEM_GROUPS = [
    {
        "group": "1. AI Compute & Accelerators",
        "tickers": ["NVDA", "AMD", "AVGO", "TSM"],
        "fair_fpe_norm": 28.0,
        "description": "Foundry wafer capacity & GPU/ASIC acceleration."
    },
    {
        "group": "2. High-Bandwidth Memory (HBM)",
        "tickers": ["MU", "WDC"],
        "fair_fpe_norm": 16.0,
        "description": "HBM3e/HBM4 packaging yields and DRAM pricing cycle."
    },
    {
        "group": "3. Physical AI & Robotics",
        "tickers": ["TSLA", "SYM", "TER", "ROK", "ISRG"],
        "fair_fpe_norm": 30.0,
        "description": "Humanoid robotics, warehouse automation, and precision motion control."
    },
    {
        "group": "4. Downstream Power & Grid",
        "tickers": ["CEG", "VST", "ETN", "GEV"],
        "fair_fpe_norm": 22.0,
        "description": "Nuclear power contracts, transformers, and datacenter grid connection."
    },
    {
        "group": "5. Downstream Datacenter Cooling",
        "tickers": ["VRT", "MOD", "SMCI"],
        "fair_fpe_norm": 25.0,
        "description": "Liquid cooling racks and direct-to-chip thermal management."
    },
    {
        "group": "6. Semiconductor EUV Equipment",
        "tickers": ["ASML", "AMAT", "LRCX", "KLAC"],
        "fair_fpe_norm": 26.0,
        "description": "Advanced EUV lithography equipment and fab expansion."
    },
    {
        "group": "7. Critical Materials & Magnets",
        "tickers": ["FCX", "MP"],
        "fair_fpe_norm": 18.0,
        "description": "Copper wiring and Neodymium rare-earth magnets for robotic actuators."
    }
]


class AIRoboticsEcosystemTracker:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()

    def analyze_ecosystem_valuations(self) -> List[Dict[str, Any]]:
        """Calculates group valuation averages with ZeroDivisionError guards."""
        results = []

        for group_info in AI_ECOSYSTEM_GROUPS:
            grp_name = group_info["group"]
            tickers = group_info["tickers"]
            fair_norm = group_info["fair_fpe_norm"]

            company_data = []
            valid_fpes = []
            valid_eves = []

            for ticker in tickers:
                try:
                    t = yf.Ticker(ticker)
                    info = t.info
                    
                    price = info.get("currentPrice") or info.get("regularMarketPrice")
                    fpe = info.get("forwardPE")
                    eve = info.get("enterpriseToEbitda")

                    if fpe and 0 < fpe < 150:
                        valid_fpes.append(fpe)
                    if eve and 0 < eve < 150:
                        valid_eves.append(eve)

                    company_data.append({
                        "ticker": ticker,
                        "name": info.get("shortName", ticker),
                        "price": round(price, 2) if price else None,
                        "forward_pe": round(fpe, 2) if fpe else None,
                        "ev_ebitda": round(eve, 2) if eve else None
                    })
                except Exception as e:
                    logging.debug(f"Error fetching ticker {ticker} for AI group {grp_name}: {e}")

            avg_fpe = sum(valid_fpes) / len(valid_fpes) if len(valid_fpes) > 0 else None
            avg_eve = sum(valid_eves) / len(valid_eves) if len(valid_eves) > 0 else None

            valuation_status = "Fairly Valued"
            if avg_fpe:
                if avg_fpe > fair_norm * 1.25:
                    valuation_status = "Rich Multiple / Growth Premium"
                elif avg_fpe < fair_norm * 0.8:
                    valuation_status = "Undervalued / Discounted Super-Cycle"

            results.append({
                "group": grp_name,
                "fair_fpe_norm": fair_norm,
                "avg_forward_pe": round(avg_fpe, 2) if avg_fpe else None,
                "avg_ev_ebitda": round(avg_eve, 2) if avg_eve else None,
                "valuation_status": valuation_status,
                "description": group_info["description"],
                "companies": company_data
            })

        return results
