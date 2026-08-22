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

    def _download_price_histories(
        self, tickers: List[str], period: str = "1y"
    ) -> Dict[str, pd.DataFrame]:
        unique_tickers = list(dict.fromkeys(tickers))
        if not unique_tickers:
            return {}

        try:
            data = yf.download(
                unique_tickers,
                period=period,
                group_by="ticker",
                progress=False,
                threads=True,
                auto_adjust=False,
            )
        except Exception as e:
            logging.debug(f"Error fetching batched price histories ({period}): {e}")
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

    def _download_30d_histories(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """Download historical prices in one request to calculate performance and relative history."""
        return self._download_price_histories(tickers, period="1y")

    def fetch_individual_stock_metrics(self) -> List[Dict[str, Any]]:
        """Fetch constituent metrics with their business-model peer cohort."""
        stock_metrics = []
        all_tickers = [
            ticker
            for tickers in PEER_COHORTS.values()
            for ticker in tickers
        ]
        histories_1y = self._download_30d_histories(all_tickers)
        self._last_price_histories = histories_1y

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
                    hist = histories_1y.get(t, pd.DataFrame())
                    perf_30d = None
                    if not hist.empty and len(hist) >= 2:
                        cutoff_30d = hist.index.max() - pd.Timedelta(days=30)
                        sub_30d = hist[hist.index >= cutoff_30d]
                        if not sub_30d.empty and len(sub_30d) >= 2:
                            p_start = sub_30d["Close"].iloc[0]
                            p_end = sub_30d["Close"].iloc[-1]
                        else:
                            p_start = hist["Close"].iloc[0]
                            p_end = hist["Close"].iloc[-1]
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

    def save_relative_multiple_observations(
        self,
        stock_metrics: List[Dict[str, Any]],
        today_str: str,
        price_histories: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> int:
        """Persist current and historical stock multiples as ratios to their cohort median."""
        grouped = {}
        for stock in stock_metrics:
            grouped.setdefault(stock.get("peer_cohort") or stock.get("group", "Other"), []).append(stock)

        saved = 0
        price_histories = price_histories or {}

        # If price histories are supplied, calculate historical relative ratios across all dates
        if price_histories:
            for group_name, group_stocks in grouped.items():
                tickers = [s.get("ticker") for s in group_stocks if s.get("ticker")]
                cohort_histories = {
                    t: price_histories.get(t)
                    for t in tickers
                    if t in price_histories and price_histories[t] is not None and not price_histories[t].empty
                }

                all_dates = set()
                for df in cohort_histories.values():
                    if "Close" in df.columns:
                        all_dates.update(df.index)
                sorted_dates = sorted(all_dates)

                ticker_fpe_records: Dict[str, List[Dict[str, Any]]] = {t: [] for t in tickers}
                ticker_eve_records: Dict[str, List[Dict[str, Any]]] = {t: [] for t in tickers}

                stock_by_ticker = {s.get("ticker"): s for s in group_stocks}

                for dt in sorted_dates:
                    date_str = dt.strftime("%Y-%m-%d")
                    fpes: Dict[str, float] = {}
                    eves: Dict[str, float] = {}

                    for t in tickers:
                        stock = stock_by_ticker.get(t, {})
                        curr_p = stock.get("price")
                        curr_fpe = stock.get("forward_pe")
                        curr_eve = stock.get("ev_ebitda")

                        df = cohort_histories.get(t)
                        if df is None or dt not in df.index or not curr_p or curr_p <= 0:
                            continue

                        hist_p = df.loc[dt, "Close"]
                        if isinstance(hist_p, pd.Series):
                            hist_p = hist_p.iloc[0]
                        if pd.isna(hist_p) or hist_p <= 0:
                            continue

                        ratio = float(hist_p) / float(curr_p)
                        if curr_fpe and 0 < curr_fpe < 150:
                            hist_fpe = curr_fpe * ratio
                            if 0 < hist_fpe < 150:
                                fpes[t] = hist_fpe

                        if curr_eve and 0 < curr_eve < 150:
                            hist_eve = curr_eve * ratio
                            if 0 < hist_eve < 150:
                                eves[t] = hist_eve

                    for t in tickers:
                        peers_fpe = [v for k, v in fpes.items() if k != t]
                        peers_eve = [v for k, v in eves.items() if k != t]

                        median_fpe = statistics.median(peers_fpe) if len(peers_fpe) >= 3 else None
                        median_eve = statistics.median(peers_eve) if len(peers_eve) >= 3 else None

                        if t in fpes and median_fpe is not None:
                            rel_fpe = safe_ratio(fpes[t], median_fpe)
                            if rel_fpe is not None and 0 < rel_fpe < 5:
                                ticker_fpe_records[t].append({"date": date_str, "value": rel_fpe})

                        if t in eves and median_eve is not None:
                            rel_eve = safe_ratio(eves[t], median_eve)
                            if rel_eve is not None and 0 < rel_eve < 5:
                                ticker_eve_records[t].append({"date": date_str, "value": rel_eve})

                for t in tickers:
                    if ticker_fpe_records[t]:
                        res_fpe = self.storage.save_observations(
                            relative_multiple_key(group_name, t, "fpe"),
                            pd.DataFrame(ticker_fpe_records[t]),
                        )
                        saved += res_fpe if res_fpe is not None else len(ticker_fpe_records[t])
                    if ticker_eve_records[t]:
                        res_eve = self.storage.save_observations(
                            relative_multiple_key(group_name, t, "eve"),
                            pd.DataFrame(ticker_eve_records[t]),
                        )
                        saved += res_eve if res_eve is not None else len(ticker_eve_records[t])

        # Always save today's observation
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
                    res_fpe = self.storage.save_observations(
                        relative_multiple_key(group_name, ticker, "fpe"),
                        pd.DataFrame([{"date": today_str, "value": rel_fpe}]),
                    )
                    saved += res_fpe if res_fpe is not None else 1

                rel_eve = safe_ratio(stock.get("ev_ebitda"), median_eve)
                if rel_eve is not None and 0 < rel_eve < 5:
                    res_eve = self.storage.save_observations(
                        relative_multiple_key(group_name, ticker, "eve"),
                        pd.DataFrame([{"date": today_str, "value": rel_eve}]),
                    )
                    saved += res_eve if res_eve is not None else 1

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
        price_histories = getattr(self, "_last_price_histories", None)
        self.save_relative_multiple_observations(
            stock_constituents, today_str, price_histories=price_histories
        )

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
