"""Deterministic comparable-cohort analysis for raw macro payloads."""

from math import isfinite
from statistics import median
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from peer_cohorts import ticker_to_cohort
from stock_relative_valuation import relative_multiple_key, safe_ratio
from storage import MacroStorage


MIN_VALID_COMPARABLES = 3
MIN_RELATIVE_HISTORY_POINTS = 60
MIN_RELATIVE_HISTORY_SPAN_DAYS = 180
RELATIVE_DISCOUNT_THRESHOLD_PCT = 20.0


class MechanicalMacroAnalyst:
    """Produce evidence-backed relative-valuation research postures."""

    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()
        self._ticker_cohorts = ticker_to_cohort()

    @staticmethod
    def _valid_multiple(value: Any) -> Optional[float]:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(numeric_value) or not 0 < numeric_value < 150:
            return None
        return numeric_value

    def _historical_relative_median(
        self, cohort: str, ticker: str, multiple: str
    ) -> tuple[Optional[float], Optional[str]]:
        series = self.storage.get_indicator_series(
            relative_multiple_key(cohort, ticker, multiple), limit=756
        )
        if series.empty:
            return None, "No historical relative observations are available."

        valid_rows = series.copy()
        valid_rows["value"] = valid_rows["value"].map(self._valid_multiple)
        valid_rows["date"] = pd.to_datetime(valid_rows["date"], errors="coerce")
        valid_rows = valid_rows.dropna(subset=["value"])
        valid_rows = valid_rows.dropna(subset=["date"])
        observation_count = len(valid_rows)
        if observation_count < MIN_RELATIVE_HISTORY_POINTS:
            return (
                None,
                f"Only {observation_count} valid historical relative observations are available; "
                f"{MIN_RELATIVE_HISTORY_POINTS} are required.",
            )

        span_days = int((valid_rows["date"].max() - valid_rows["date"].min()).days)
        if span_days < MIN_RELATIVE_HISTORY_SPAN_DAYS:
            return (
                None,
                f"Historical relative evidence spans only {span_days} days; "
                f"{MIN_RELATIVE_HISTORY_SPAN_DAYS} days are required.",
            )

        return median(valid_rows["value"].tolist()), None

    def _relative_multiple_assessment(
        self,
        cohort: str,
        ticker: str,
        multiple: str,
        current_multiple: Any,
        comparable_constituents: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        current_value = self._valid_multiple(current_multiple)
        multiple_field = {"fpe": "forward_pe", "eve": "ev_ebitda"}[multiple]
        valid_comparables = [
            value
            for value in (
                self._valid_multiple(item.get(multiple_field))
                for item in comparable_constituents
                if item.get("ticker") != ticker
            )
            if value is not None
        ]
        result: Dict[str, Any] = {
            "current_relative": None,
            "historical_relative_median": None,
            "relative_discount_pct": None,
            "watch": False,
            "evidence": [],
            "missing_evidence": [],
        }

        if current_value is None:
            result["missing_evidence"].append(
                f"No valid current {multiple.upper()} multiple is available."
            )
            return result
        if len(valid_comparables) < MIN_VALID_COMPARABLES:
            result["missing_evidence"].append(
                f"Fewer than {MIN_VALID_COMPARABLES} valid comparable peers are available for {multiple.upper()}."
            )
            return result

        current_relative = safe_ratio(current_value, median(valid_comparables))
        if current_relative is None:
            result["missing_evidence"].append(
                f"Unable to calculate the current {multiple.upper()} cohort-relative ratio."
            )
            return result
        result["current_relative"] = round(current_relative, 3)

        historical_median, history_reason = self._historical_relative_median(
            cohort, ticker, multiple
        )
        if historical_median is None:
            result["missing_evidence"].append(history_reason)
            return result

        discount_pct = (1.0 - current_relative / historical_median) * 100.0
        result["historical_relative_median"] = round(historical_median, 3)
        result["relative_discount_pct"] = round(discount_pct, 1)
        result["watch"] = discount_pct >= RELATIVE_DISCOUNT_THRESHOLD_PCT
        comparison = "below" if discount_pct >= 0 else "above"
        result["evidence"].append(
            f"Current {multiple.upper()} cohort-relative ratio ({current_relative:.2f}x) is "
            f"{abs(discount_pct):.1f}% {comparison} its historical median "
            f"({historical_median:.2f}x) across {MIN_RELATIVE_HISTORY_POINTS}+ observations."
        )
        if result["watch"]:
            result["evidence"].append(
                f"The {abs(discount_pct):.1f}% relative discount meets the "
                f"{RELATIVE_DISCOUNT_THRESHOLD_PCT:.1f}% WATCH threshold."
            )
        else:
            result["evidence"].append(
                f"The {abs(discount_pct):.1f}% relative discount does not meet the "
                f"{RELATIVE_DISCOUNT_THRESHOLD_PCT:.1f}% WATCH threshold; posture remains NEUTRAL."
            )
        return result

    @staticmethod
    def _unique(items: Iterable[str]) -> List[str]:
        return list(dict.fromkeys(item for item in items if item))

    def analyze_raw_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Assess each constituent only against its focused business-model cohort."""

        payload = payload or {}
        stocks = payload.get("individual_stock_constituents") or []
        cohorts: Dict[str, List[Dict[str, Any]]] = {}
        for stock in stocks:
            if not isinstance(stock, dict):
                continue
            ticker = stock.get("ticker")
            cohort = self._ticker_cohorts.get(ticker) if ticker else None
            if cohort is None:
                cohort = stock.get("peer_cohort")
            if cohort is None:
                continue
            cohorts.setdefault(cohort, []).append(stock)

        assessments = []
        for cohort, constituents in cohorts.items():
            for constituent in constituents:
                ticker = constituent.get("ticker", "N/A")
                fpe = self._relative_multiple_assessment(
                    cohort,
                    ticker,
                    "fpe",
                    constituent.get("forward_pe"),
                    constituents,
                )
                eve = self._relative_multiple_assessment(
                    cohort,
                    ticker,
                    "eve",
                    constituent.get("ev_ebitda"),
                    constituents,
                )
                metric_results = (fpe, eve)
                missing_evidence = self._unique(
                    reason
                    for result in metric_results
                    for reason in result["missing_evidence"]
                )
                evidence = self._unique(
                    detail
                    for result in metric_results
                    for detail in result["evidence"]
                )

                has_comparable_peer_shortfall = any(
                    "Fewer than" in reason for reason in missing_evidence
                )
                has_historical_evidence = any(
                    result["historical_relative_median"] is not None
                    for result in metric_results
                )
                is_watch = any(result["watch"] for result in metric_results)
                if has_comparable_peer_shortfall and not has_historical_evidence:
                    relative_status = "Insufficient Comparable Peers"
                elif not has_historical_evidence:
                    relative_status = "Insufficient Relative History"
                elif is_watch:
                    relative_status = "Discounted vs Historical Cohort Relationship"
                else:
                    relative_status = "Fair vs Historical Cohort Relationship"

                assessments.append(
                    {
                        "group": cohort,
                        "ticker": ticker,
                        "relative_valuation_status": relative_status,
                        "posture": "WATCH" if is_watch else "NEUTRAL",
                        "evidence": evidence,
                        "missing_evidence": missing_evidence,
                        "forward_pe_relative": fpe["current_relative"],
                        "historical_forward_pe_relative": fpe["historical_relative_median"],
                        "relative_fpe_discount_pct": fpe["relative_discount_pct"],
                        "ev_ebitda_relative": eve["current_relative"],
                        "historical_ev_ebitda_relative": eve["historical_relative_median"],
                        "relative_ev_ebitda_discount_pct": eve["relative_discount_pct"],
                    }
                )

        return {"constituent_assessments": sorted(assessments, key=lambda item: (item["group"], item["ticker"]))}
