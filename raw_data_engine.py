"""
Raw Data Engine module for Macro & Sector Analysis System.
Gathers comprehensive, un-hardcoded raw quantitative macroeconomic metrics,
sector multiples, and granular individual stock-level valuation/lag metrics across 35+ sector constituents.
Outputs structured JSON payload for Gemini LLM analysis.
"""

import json
import logging
import math
import yfinance as yf
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from storage import MacroStorage
from config import OUTPUT_DIR, configure_yfinance_cache

configure_yfinance_cache(yf)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Key Constituent Tickers by Sector / Supply Chain Group
CONSTITUENT_GROUPS = {
    "Technology & Semiconductors": ["MU", "NVDA", "AMD", "AVGO", "TSM", "AAPL", "MSFT", "ORCL", "QCOM"],
    "Financials & Banking": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "SCHW"],
    "Healthcare & Pharma": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "PFE", "ABT"],
    "Energy & Oil/Gas": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO"],
    "Industrials & Machinery": ["GE", "CAT", "RTX", "HON", "UNP", "BA", "DE", "LMT"],
    "Consumer Discretionary & Retail": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG"],
    "Consumer Staples": ["PG", "COST", "KO", "PEP", "WMT", "PM", "MDLZ", "CL"],
    "Physical AI & Robotics": ["TSLA", "SYM", "TER", "ROK", "ISRG"],
    "Downstream Power & Grid": ["CEG", "VST", "ETN", "GEV"],
    "Datacenter Liquid Cooling": ["VRT", "MOD", "SMCI"],
    "Semiconductor Equipment": ["ASML", "AMAT", "LRCX", "KLAC"],
    "Critical Minerals & Magnets": ["FCX", "MP"]
}


class RawDataEngine:
    def __init__(self, storage: Optional[MacroStorage] = None, output_dir: Optional[Path] = None, verbose: bool = True):
        self.storage = storage or MacroStorage()
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def fetch_individual_stock_metrics(self) -> List[Dict[str, Any]]:
        """
        Fetches granular stock-level valuation and performance lag metrics for individual constituents.
        Allows Gemini to identify specific stocks lagging peers or trading at deep discounts.
        """
        stock_metrics = []

        for group_name, tickers in CONSTITUENT_GROUPS.items():
            group_stocks = []
            for t in tickers:
                try:
                    ticker_obj = yf.Ticker(t)
                    info = ticker_obj.info
                    
                    price = info.get("currentPrice") or info.get("regularMarketPrice")
                    pe = info.get("trailingPE")
                    fpe = info.get("forwardPE")
                    eve = info.get("enterpriseToEbitda")
                    pb = info.get("priceToBook")
                    high_52 = info.get("fiftyTwoWeekHigh")
                    low_52 = info.get("fiftyTwoWeekLow")

                    # Calculate distance from 52-week high %
                    dist_52h = None
                    if price and high_52:
                        dist_52h = round(((price - high_52) / high_52) * 100.0, 2)

                    # Fetch 30-day performance
                    hist_30d = ticker_obj.history(period="1mo")
                    perf_30d = None
                    if not hist_30d.empty and len(hist_30d) >= 2:
                        p_start = hist_30d["Close"].iloc[0]
                        p_end = hist_30d["Close"].iloc[-1]
                        perf_30d = round(((p_end - p_start) / p_start) * 100.0, 2)

                    group_stocks.append({
                        "ticker": t,
                        "name": info.get("shortName", t),
                        "group": group_name,
                        "price": round(price, 2) if price else None,
                        "trailing_pe": round(pe, 2) if pe else None,
                        "forward_pe": round(fpe, 2) if fpe else None,
                        "ev_ebitda": round(eve, 2) if eve else None,
                        "price_to_book": round(pb, 2) if pb else None,
                        "dist_from_52w_high_pct": dist_52h,
                        "return_30d_pct": perf_30d
                    })
                except Exception as e:
                    logging.debug(f"Error fetching stock metrics for {t}: {e}")

            stock_metrics.extend(group_stocks)

        return stock_metrics

    def build_raw_payload(self) -> Dict[str, Any]:
        """
        Builds the complete raw data JSON payload containing quantitative macro series,
        news events, sector valuations, and granular stock-level constituent lag metrics.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Macro Indicators
        indicators = {}
        for key in ["fed_total_assets", "tga_balance", "reverse_repo", "treasury_10y", "treasury_2y", "spread_10y_2y", "high_yield_oas", "invest_grade_oas", "chicago_fed_nfci", "vix", "dxy", "sp500", "crude_oil", "gold", "copper", "unemployment_rate", "cpi", "breakeven_5y", "cnn_fear_greed_index", "shiller_pe"]:
            obs = self.storage.get_latest_observation(key)
            indicators[key] = obs if obs else None

        # 2. News Events
        news_events = self.storage.get_recent_news(limit=25)

        # 3. Individual Stock Level Granular Metrics
        stock_constituents = self.fetch_individual_stock_metrics()

        payload = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "date": today_str,
                "engine_version": "2.0-GeminiRawPayload"
            },
            "macro_quantitative": indicators,
            "recent_news_events": news_events,
            "individual_stock_constituents": stock_constituents
        }

        def _clean_for_json(obj):
            if isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            elif isinstance(obj, dict):
                return {k: _clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_clean_for_json(v) for v in obj]
            return obj

        payload = _clean_for_json(payload)

        # Save to output files
        payload_path = self.output_dir / f"raw_macro_payload_{today_str}.json"
        latest_path = self.output_dir / "latest_raw_payload.json"

        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        if self.verbose:
            logging.info(f"Raw data payload generated: {payload_path}")
            print(f"--> Raw Data Payload generated: {payload_path} ({len(stock_constituents)} stock constituents included)")

        return payload
