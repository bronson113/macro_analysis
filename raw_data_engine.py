"""Build provider-neutral raw quantitative inputs for macro research."""

import json
import logging
import math
import statistics
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from storage import MacroStorage
from config import OUTPUT_DIR, configure_yfinance_cache
from peer_cohorts import PEER_COHORTS
from stock_relative_valuation import relative_multiple_key, safe_ratio
from stock_data import get_ticker_info

configure_yfinance_cache(yf)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class RawDataEngine:
    def __init__(self, storage: Optional[MacroStorage] = None, output_dir: Optional[Path] = None, verbose: bool = True):
        self.storage = storage or MacroStorage()
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def _download_30d_histories(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        unique_tickers = list(dict.fromkeys(tickers))
        if not unique_tickers:
            return {}

        try:
            data = yf.download(
                unique_tickers,
                period="1mo",
                group_by="ticker",
                progress=False,
                threads=True,
                auto_adjust=False,
            )
        except Exception as e:
            logging.debug(f"Error fetching batched 30-day histories: {e}")
            return {}

        if data is None or data.empty:
            return {}

        if len(unique_tickers) == 1:
            return {unique_tickers[0]: data.dropna(how="all")}

        histories = {}
        if isinstance(data.columns, pd.MultiIndex):
            level_zero = set(data.columns.get_level_values(0))
            level_one = set(data.columns.get_level_values(1))
            for ticker in unique_tickers:
                try:
                    if ticker in level_zero:
                        ticker_frame = data[ticker]
                    elif ticker in level_one:
                        ticker_frame = data.xs(ticker, axis=1, level=1)
                    else:
                        continue
                    histories[ticker] = ticker_frame.dropna(how="all")
                except Exception:
                    continue

        return histories

    def fetch_individual_stock_metrics(self) -> List[Dict[str, Any]]:
        """Fetch constituent metrics with their business-model peer cohort."""
        stock_metrics = []
        all_tickers = [
            ticker
            for tickers in PEER_COHORTS.values()
            for ticker in tickers
        ]
        histories_30d = self._download_30d_histories(all_tickers)

        for cohort_name, tickers in PEER_COHORTS.items():
            group_stocks = []
            for t in tickers:
                try:
                    info = get_ticker_info(t)
                    
                    price = info.get("currentPrice") or info.get("regularMarketPrice")
                    pe = info.get("trailingPE")
                    fpe = info.get("forwardPE")
                    eve = info.get("enterpriseToEbitda")
                    pb = info.get("priceToBook")
                    high_52 = info.get("fiftyTwoWeekHigh")

                    # Calculate distance from 52-week high %
                    dist_52h = None
                    if price and high_52:
                        dist_52h = round(((price - high_52) / high_52) * 100.0, 2)

                    # Fetch 30-day performance
                    hist_30d = histories_30d.get(t, pd.DataFrame())
                    perf_30d = None
                    if not hist_30d.empty and len(hist_30d) >= 2:
                        p_start = hist_30d["Close"].iloc[0]
                        p_end = hist_30d["Close"].iloc[-1]
                        perf_30d = round(((p_end - p_start) / p_start) * 100.0, 2)

                    group_stocks.append({
                        "ticker": t,
                        "name": info.get("shortName", t),
                        "group": cohort_name,
                        "peer_cohort": cohort_name,
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

    def save_relative_multiple_observations(self, stock_metrics: List[Dict[str, Any]], today_str: str) -> int:
        """Persist current stock multiples as ratios to their cohort median."""
        grouped = {}
        for stock in stock_metrics:
            grouped.setdefault(stock.get("peer_cohort") or stock.get("group", "Other"), []).append(stock)

        saved = 0
        for group_name, group_stocks in grouped.items():
            for stock in group_stocks:
                ticker = stock.get("ticker")
                if not ticker:
                    continue

                peers = [peer for peer in group_stocks if peer.get("ticker") != ticker]
                valid_fpes = [
                    peer.get("forward_pe")
                    for peer in peers
                    if peer.get("forward_pe") and 0 < peer.get("forward_pe", 0) < 150
                ]
                valid_eves = [
                    peer.get("ev_ebitda")
                    for peer in peers
                    if peer.get("ev_ebitda") and 0 < peer.get("ev_ebitda", 0) < 150
                ]
                median_fpe = statistics.median(valid_fpes) if len(valid_fpes) >= 3 else None
                median_eve = statistics.median(valid_eves) if len(valid_eves) >= 3 else None

                rel_fpe = safe_ratio(stock.get("forward_pe"), median_fpe)
                if rel_fpe is not None and 0 < rel_fpe < 5:
                    saved += self.storage.save_observations(
                        relative_multiple_key(group_name, ticker, "fpe"),
                        pd.DataFrame([{"date": today_str, "value": rel_fpe}]),
                    )

                rel_eve = safe_ratio(stock.get("ev_ebitda"), median_eve)
                if rel_eve is not None and 0 < rel_eve < 5:
                    saved += self.storage.save_observations(
                        relative_multiple_key(group_name, ticker, "eve"),
                        pd.DataFrame([{"date": today_str, "value": rel_eve}]),
                    )

        return saved

    @staticmethod
    def _clean_for_json(obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        if obj is pd.NaT or obj is pd.NA:
            return None
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, (int, str, bool)) or obj is None:
            return obj
        if isinstance(obj, dict):
            return {key: RawDataEngine._clean_for_json(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [RawDataEngine._clean_for_json(value) for value in obj]
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        return obj

    def _write_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Persist the current raw payload and its latest dashboard source."""
        payload = self._clean_for_json(payload)
        metadata = payload.get("metadata") if isinstance(payload, dict) else {}
        today_str = metadata.get("date") if isinstance(metadata, dict) else None
        today_str = today_str or datetime.now().strftime("%Y-%m-%d")
        payload_path = self.output_dir / f"raw_macro_payload_{today_str}.json"
        latest_path = self.output_dir / "latest_raw_payload.json"

        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return payload

    def publish_constituent_assessments(
        self, payload: Dict[str, Any], constituent_assessments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge mechanical relative-value results into the stock rows consumed by the web app."""
        assessments = [
            dict(assessment)
            for assessment in constituent_assessments
            if isinstance(assessment, dict) and assessment.get("ticker")
        ]
        assessments_by_ticker = {
            assessment["ticker"]: assessment for assessment in assessments
        }
        stocks = payload.get("individual_stock_constituents") or []
        enriched_stocks = []
        for stock in stocks:
            if not isinstance(stock, dict):
                enriched_stocks.append(stock)
                continue
            enriched = dict(stock)
            assessment = assessments_by_ticker.get(enriched.get("ticker"))
            if assessment:
                enriched["relative_valuation_status"] = assessment.get(
                    "relative_valuation_status", "Not yet assessed"
                )
                enriched["relative_posture"] = assessment.get("posture", "NEUTRAL")
            enriched_stocks.append(enriched)

        payload["individual_stock_constituents"] = enriched_stocks
        payload["constituent_assessments"] = assessments
        return self._write_payload(payload)

    def build_raw_payload(
        self,
        evidence_assessments: Optional[List[Dict[str, Any]]] = None,
        macro_regime: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Builds the complete raw data JSON payload containing quantitative macro series,
        news events, sector evidence assessments, and granular stock-level constituents.
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
        self.save_relative_multiple_observations(stock_constituents, today_str)

        payload = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "date": today_str,
                "engine_version": "3.0-EvidenceRawPayload"
            },
            "macro_quantitative": indicators,
            "macro_regime": macro_regime or {},
            "recent_news_events": news_events,
            "evidence_assessments": evidence_assessments or [],
            "individual_stock_constituents": stock_constituents
        }

        payload = self._write_payload(payload)

        if self.verbose:
            payload_path = self.output_dir / f"raw_macro_payload_{today_str}.json"
            logging.info(f"Raw data payload generated: {payload_path}")
            print(f"--> Raw Data Payload generated: {payload_path} ({len(stock_constituents)} stock constituents included)")

        return payload
