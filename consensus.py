"""Pure interpretation of market-consensus survey observations.

The survey is an optional forward-looking overlay.  It describes the
expected policy rate and Fed balance-sheet path, but it never determines
whether the current macro quadrant is actionable.
"""

from __future__ import annotations

import math
import re
import io
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import urljoin

import pandas as pd
import requests

from config import NYFED_SME_SOURCE


CONSENSUS_MIN_HORIZON_MONTHS = 3
CONSENSUS_MAX_HORIZON_MONTHS = 9
CONSENSUS_TARGET_HORIZON_MONTHS = 6
CONSENSUS_MAX_AGE_DAYS = 120
CONSENSUS_POLICY_THRESHOLD_PP = 0.10
CONSENSUS_BALANCE_SHEET_THRESHOLD_PCT = 0.5


def _timestamp(value: Any) -> Optional[pd.Timestamp]:
    """Parse a date as a timezone-naive timestamp, or return ``None``."""

    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if pd.isna(parsed):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert(None)
    return parsed


def _finite_float(value: Any) -> Optional[float]:
    """Return a finite numeric value without accepting missing values."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _horizon_months(value: Any) -> Optional[float]:
    """Normalize a survey horizon while retaining support for numeric strings."""

    numeric = _finite_float(value)
    if numeric is None:
        return None
    if not float(numeric).is_integer():
        return None
    return float(int(numeric))


def _row_horizon_months(
    row: Mapping[str, Any],
    survey_date: pd.Timestamp,
    target_date: Optional[pd.Timestamp],
    horizon_column: Any,
) -> Optional[float]:
    """Normalize canonical, textual, and official-workbook horizons."""
    direct = _horizon_months(row.get(horizon_column)) if horizon_column is not None else None
    if direct is not None:
        return direct
    raw = str(row.get(horizon_column) or "") if horizon_column is not None else ""
    match = re.search(r"(\d+(?:\.\d+)?)\s*months?", raw, flags=re.IGNORECASE)
    if match:
        return float(round(float(match.group(1))))
    if target_date is None or target_date < survey_date:
        return None
    months = (target_date - survey_date).days / 30.4375
    return float(round(months))


def _empty_result(as_of: pd.Timestamp) -> dict[str, Any]:
    return {
        "as_of": as_of,
        "quality": "UNAVAILABLE",
        "reasons": [],
        "blocks_quadrant": False,
        "survey_date": None,
        "selected_survey_date": None,
        "reference_date": None,
        "survey_reference_date": None,
        "publication_date": None,
        "target_date": None,
        "selected_target_date": None,
        "horizon_months": None,
        "selected_horizon_months": None,
        "survey_age_days": None,
        "expected_dff": None,
        "expected_fed_assets": None,
        "current_dff": None,
        "current_fed_assets": None,
        "policy_change_pp": None,
        "balance_sheet_change_pct": None,
        "policy_direction": None,
        "balance_sheet_direction": None,
        "metric": None,
        "unit": None,
        "source_url": None,
        "parsing_status": None,
        "provider": None,
        "metrics": [],
    }


def _direction_from_policy_delta(delta: float) -> str:
    threshold = CONSENSUS_POLICY_THRESHOLD_PP
    if delta < -threshold or math.isclose(delta, -threshold, rel_tol=0.0, abs_tol=1e-12):
        return "EASING"
    if delta > threshold or math.isclose(delta, threshold, rel_tol=0.0, abs_tol=1e-12):
        return "TIGHTENING"
    return "STABLE"


def _direction_from_balance_sheet_delta(delta_pct: float) -> str:
    threshold = CONSENSUS_BALANCE_SHEET_THRESHOLD_PCT
    if delta_pct < -threshold or math.isclose(
        delta_pct, -threshold, rel_tol=0.0, abs_tol=1e-12
    ):
        return "CONTRACTING"
    if delta_pct > threshold or math.isclose(
        delta_pct, threshold, rel_tol=0.0, abs_tol=1e-12
    ):
        return "EXPANDING"
    return "STABLE"


def _records_as_dicts(records: Optional[Iterable[Mapping[str, Any]]]) -> list[Mapping[str, Any]]:
    if records is None:
        return []
    if isinstance(records, pd.DataFrame):
        return records.to_dict("records")
    try:
        return [record for record in records if isinstance(record, Mapping)]
    except TypeError:
        return []


def interpret_consensus(
    records: Optional[Iterable[Mapping[str, Any]]],
    current_dff: Any,
    current_fed_assets: Any,
    as_of: Any,
) -> dict[str, Any]:
    """Interpret the most relevant fresh survey horizon.

    Only horizons from three through nine months are eligible.  The horizon
    closest to six months is selected; a lower horizon wins an exact distance
    tie.  Consensus is explicitly optional, so ``blocks_quadrant`` is always
    ``False``.
    """

    analysis_date = _timestamp(as_of)
    if analysis_date is None:
        # ``as_of`` is part of the public point-in-time interface.  Keep the
        # result machine-readable even when a caller supplies a malformed date.
        analysis_date = pd.NaT
    result = _empty_result(analysis_date)
    reasons: list[str] = []

    if pd.isna(analysis_date):
        result["reasons"] = ["Invalid analysis date"]
        return result

    candidates: list[dict[str, Any]] = []
    saw_horizon = False
    saw_future = False
    for raw_record in _records_as_dicts(records):
        survey_date = _timestamp(
            raw_record.get("survey_date")
            or raw_record.get("reference_date")
            or raw_record.get("survey_reference_date")
        )
        publication_date = _timestamp(
            raw_record.get("publication_date")
            or raw_record.get("release_date")
            or survey_date
        )
        horizon = _horizon_months(raw_record.get("horizon_months"))
        if survey_date is None or publication_date is None:
            continue
        if horizon is None or not (
            CONSENSUS_MIN_HORIZON_MONTHS <= horizon <= CONSENSUS_MAX_HORIZON_MONTHS
        ):
            continue
        saw_horizon = True
        if publication_date > analysis_date:
            saw_future = True
            continue
        candidates.append(
            {
                "survey_date": survey_date,
                "publication_date": publication_date,
                "target_date": _timestamp(raw_record.get("target_date")),
                "horizon_months": int(horizon),
                "expected_dff": _finite_float(raw_record.get("expected_dff")),
                "expected_fed_assets": _finite_float(raw_record.get("expected_fed_assets")),
                "metric": raw_record.get("metric"),
                "unit": raw_record.get("unit"),
                "source_url": raw_record.get("source_url"),
                "parsing_status": raw_record.get("parsing_status") or "OK",
                "provider": raw_record.get("provider"),
                "metrics": raw_record.get("metrics") or [],
            }
        )

    if not candidates:
        if saw_future and not saw_horizon:
            reasons.append("No supported consensus horizon on or before as_of")
        elif saw_future:
            reasons.append("Consensus observations are dated after as_of")
        elif saw_horizon:
            reasons.append("No consensus observation on or before as_of")
        else:
            reasons.append(
                "No consensus observation with a supported three-to-nine-month horizon"
            )
        result["reasons"] = reasons
        return result

    selected = min(
        candidates,
        key=lambda candidate: (
            abs(candidate["horizon_months"] - CONSENSUS_TARGET_HORIZON_MONTHS),
            candidate["horizon_months"],
            # If a source repeats one horizon, prefer the newest publication
            # vintage only after horizon distance and lower-horizon tie-breaks.
            -candidate["publication_date"].value,
            -candidate["survey_date"].value,
        ),
    )

    survey_date = selected["survey_date"]
    horizon = selected["horizon_months"]
    result.update(
        {
            "survey_date": survey_date,
            "selected_survey_date": survey_date,
            "reference_date": survey_date,
            "survey_reference_date": survey_date,
            "publication_date": selected["publication_date"],
            "target_date": selected["target_date"] or survey_date + pd.DateOffset(months=horizon),
            "selected_target_date": selected["target_date"] or survey_date + pd.DateOffset(months=horizon),
            "horizon_months": horizon,
            "selected_horizon_months": horizon,
            "expected_dff": selected["expected_dff"],
            "expected_fed_assets": selected["expected_fed_assets"],
            "current_dff": _finite_float(current_dff),
            "current_fed_assets": _finite_float(current_fed_assets),
            "metric": selected.get("metric"),
            "unit": selected.get("unit"),
            "source_url": selected.get("source_url"),
            "parsing_status": selected.get("parsing_status"),
            "provider": selected.get("provider"),
            "metrics": selected.get("metrics") or [],
        }
    )

    age_days = int((analysis_date.normalize() - selected["publication_date"].normalize()).days)
    result["survey_age_days"] = age_days

    expected_dff = selected["expected_dff"]
    current_rate = result["current_dff"]
    expected_assets = selected["expected_fed_assets"]
    current_assets = result["current_fed_assets"]
    if expected_dff is None:
        reasons.append("Consensus survey omits expected DFF")
    if expected_assets is None:
        reasons.append("Consensus survey omits expected Fed assets")
    if current_rate is None:
        reasons.append("Current DFF is unavailable")
    if current_assets is None:
        reasons.append("Current Fed assets are unavailable")
    if current_assets is not None and current_assets <= 0:
        reasons.append("Current Fed assets must be positive for percentage comparison")

    if not reasons:
        policy_delta = expected_dff - current_rate
        balance_sheet_delta_pct = 100.0 * (expected_assets - current_assets) / current_assets
        result["policy_change_pp"] = round(policy_delta, 3)
        result["balance_sheet_change_pct"] = round(balance_sheet_delta_pct, 3)
        result["policy_direction"] = _direction_from_policy_delta(policy_delta)
        result["balance_sheet_direction"] = _direction_from_balance_sheet_delta(
            balance_sheet_delta_pct
        )

    if reasons:
        result["quality"] = "UNAVAILABLE"
    elif age_days > CONSENSUS_MAX_AGE_DAYS:
        result["quality"] = "STALE"
        reasons.append(
            f"Consensus survey is stale ({age_days} days old; maximum {CONSENSUS_MAX_AGE_DAYS})"
        )
    else:
        result["quality"] = "OK"
    result["reasons"] = reasons
    return result


def _column_lookup(frame: pd.DataFrame) -> dict[str, Any]:
    """Map normalized column names to their original labels."""
    lookup: dict[str, Any] = {}
    for column in frame.columns:
        name = str(column).strip().lower().replace("-", "_").replace(" ", "_")
        lookup[name] = column
    return lookup


def parse_sme_frame(
    frame: pd.DataFrame,
    *,
    source_url: str,
    provider: str = "NY Fed Survey of Market Expectations",
) -> list[dict[str, Any]]:
    """Normalize an SME fixture or workbook sheet at the storage boundary.

    The New York Fed has published several machine-readable layouts over time.
    This parser accepts the stable semantic fields used by fixtures and also
    combines one metric-per-row files into one candidate per survey horizon.
    Unsupported rows are isolated as parse failures rather than poisoning a
    valid candidate selected by :func:`interpret_consensus`.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("SME data contains no rows")
    lookup = _column_lookup(frame)

    def column(*names: str) -> Any:
        for name in names:
            if name in lookup:
                return lookup[name]
        return None

    survey_col = column(
        "survey_date",
        "survey_release_date",
        "reference_date",
        "survey_reference_date",
        "date",
    )
    publication_col = column(
        "publication_date",
        "release_date",
        "published_date",
        "survey_release_date",
    )
    target_col = column("target_date", "horizon_date")
    horizon_col = column("horizon_months", "horizon", "months_ahead")
    metric_col = column("metric", "measure", "series")
    median_col = column(
        "median_value",
        "median",
        "value",
        "expected_value",
        "aggregation_value",
    )
    unit_col = column("unit", "units")
    dff_col = column("expected_dff", "expected_fed_funds_rate", "expected_policy_rate")
    assets_col = column("expected_fed_assets", "expected_balance_sheet_assets")
    subject_col = column("subject", "subject_group", "theme")
    aggregation_col = column("aggregation", "statistic")
    panel_col = column("panel_type", "panel")
    if survey_col is None or horizon_col is None:
        raise ValueError("SME data is missing survey reference date or horizon")

    grouped: dict[tuple[Any, Any, Any, Any], dict[str, Any]] = {}
    for _, row in frame.iterrows():
        survey_date = _timestamp(row.get(survey_col))
        publication_date = _timestamp(row.get(publication_col)) if publication_col else survey_date
        target_date = _timestamp(row.get(target_col)) if target_col else None
        if survey_date is None or publication_date is None:
            continue
        horizon = _row_horizon_months(row, survey_date, target_date, horizon_col)
        if horizon is None:
            continue
        if target_date is None:
            target_date = survey_date + pd.DateOffset(months=int(horizon))
        metric = str(row.get(metric_col) or "").strip().upper()
        metric = metric.replace(" ", "_").replace("-", "_")
        subject = str(row.get(subject_col) or "").strip().lower() if subject_col else ""
        aggregation = str(row.get(aggregation_col) or "").strip().lower() if aggregation_col else ""
        panel = str(row.get(panel_col) or "").strip().lower() if panel_col else ""
        if panel and panel != "combined":
            continue
        median_value = _finite_float(row.get(median_col)) if median_col else None
        expected_dff = _finite_float(row.get(dff_col)) if dff_col else None
        expected_assets = _finite_float(row.get(assets_col)) if assets_col else None
        if expected_dff is None and "FED_FUNDS" in metric and median_value is not None:
            expected_dff = median_value
        if expected_assets is None and ("BALANCE" in metric or "ASSETS" in metric) and median_value is not None:
            expected_assets = median_value
        if aggregation and aggregation not in {"pctl50", "median"}:
            continue
        if expected_dff is None and subject in {"fed_funds_target_range", "fed_funds"} and median_value is not None:
            # The official workbook stores percentage rates as decimal Excel
            # fractions (e.g. 0.0363 for 3.63 percent).
            expected_dff = median_value * 100.0 if abs(median_value) <= 1.0 else median_value
            metric = "FED_FUNDS_RATE"
        if expected_assets is None and subject in {"fed_assets_total_assets", "fed_assets"} and median_value is not None:
            expected_assets = median_value
            metric = "FED_BALANCE_SHEET_ASSETS"
        if expected_dff is None and expected_assets is None:
            continue
        key = (survey_date, publication_date, int(horizon))
        candidate = grouped.setdefault(
            key,
            {
                "survey_date": survey_date,
                "survey_reference_date": survey_date,
                "publication_date": publication_date,
                "target_date": target_date,
                "horizon_months": int(horizon),
                "expected_dff": None,
                "expected_fed_assets": None,
                "metric": "FED_FUNDS_RATE_AND_FED_BALANCE_SHEET_ASSETS",
                "unit": "percent_and_billions_usd",
                "source_url": source_url,
                "parsing_status": "OK",
                "provider": provider,
                "metrics": [],
            },
        )
        if expected_dff is not None:
            candidate["expected_dff"] = expected_dff
        if expected_assets is not None:
            candidate["expected_fed_assets"] = expected_assets
        candidate["metrics"].append(
            {
                "metric": metric or ("FED_FUNDS_RATE" if expected_dff is not None else "FED_BALANCE_SHEET_ASSETS"),
                "value": median_value if median_value is not None else (expected_dff or expected_assets),
                "unit": row.get(unit_col) if unit_col else None,
                "target_date": target_date,
                "horizon_months": int(horizon),
                "source_url": source_url,
                "parsing_status": "OK",
            }
        )
    if not grouped:
        raise ValueError("SME data contains no supported policy or balance-sheet metrics")
    # The official workbook uses separate target dates for the policy path
    # (the December FOMC meeting) and total-assets path (the quarter-end
    # forecast).  Select the nearest six-month horizon independently for each
    # metric, then carry both into one consensus candidate.
    by_vintage: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for candidate in grouped.values():
        key = (candidate["survey_date"], candidate["publication_date"])
        by_vintage.setdefault(key, []).append(candidate)
    combined: list[dict[str, Any]] = []
    for candidates in by_vintage.values():
        policy_candidates = [candidate for candidate in candidates if candidate["expected_dff"] is not None]
        asset_candidates = [candidate for candidate in candidates if candidate["expected_fed_assets"] is not None]
        selected_policy = min(
            policy_candidates,
            key=lambda candidate: (abs(candidate["horizon_months"] - CONSENSUS_TARGET_HORIZON_MONTHS), candidate["horizon_months"]),
        ) if policy_candidates else None
        selected_assets = min(
            asset_candidates,
            key=lambda candidate: (abs(candidate["horizon_months"] - CONSENSUS_TARGET_HORIZON_MONTHS), candidate["horizon_months"]),
        ) if asset_candidates else None
        selected = selected_policy or selected_assets
        if selected is None:
            continue
        record = dict(selected)
        record["expected_dff"] = selected_policy["expected_dff"] if selected_policy else None
        record["expected_fed_assets"] = selected_assets["expected_fed_assets"] if selected_assets else None
        selected_metric_candidates = [selected_policy]
        if selected_assets is not None and selected_assets is not selected_policy:
            selected_metric_candidates.append(selected_assets)
        record["metrics"] = [
            metric
            for candidate in selected_metric_candidates
            if candidate is not None
            for metric in candidate.get("metrics", [])
        ]
        combined.append(record)
    return combined


class NewYorkFedSMEProvider:
    """Fetch the official NY Fed SME data file behind its landing page."""

    def __init__(
        self,
        *,
        source: Optional[Mapping[str, Any]] = None,
        data_url: Optional[str] = None,
        fetch_bytes: Optional[Any] = None,
        read_excel: Optional[Any] = None,
        timeout: int = 20,
    ):
        self.source = dict(source or NYFED_SME_SOURCE)
        self.data_url = data_url
        self.fetch_bytes = fetch_bytes or self._fetch_bytes
        self.read_excel = read_excel or pd.read_excel
        self.timeout = timeout

    def _fetch_bytes(self, url: str) -> bytes:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _discover_data_url(landing_url: str, content: bytes) -> Optional[str]:
        text = content.decode("utf-8", errors="ignore")
        match = re.search(r"href=[\"']([^\"']+(?:data|Data)\.xlsx)[\"']", text)
        return urljoin(landing_url, match.group(1)) if match else None

    def get_records(self, as_of: Any = None) -> list[dict[str, Any]]:
        landing_url = str(self.source["url"])
        data_url = self.data_url
        if data_url is None:
            landing = self.fetch_bytes(landing_url)
            data_url = self._discover_data_url(landing_url, landing)
            if data_url is None:
                raise ValueError("NY Fed SME landing page did not expose a supported data file")
        content = self.fetch_bytes(data_url)
        frame = self.read_excel(io.BytesIO(content), sheet_name=0, header=0)
        records = parse_sme_frame(
            frame,
            source_url=data_url,
        )
        if as_of is None:
            return records
        analysis_date = _timestamp(as_of)
        if analysis_date is None:
            return []
        return [record for record in records if record["publication_date"] <= analysis_date]


__all__ = [
    "CONSENSUS_BALANCE_SHEET_THRESHOLD_PCT",
    "CONSENSUS_MAX_AGE_DAYS",
    "CONSENSUS_MAX_HORIZON_MONTHS",
    "CONSENSUS_MIN_HORIZON_MONTHS",
    "CONSENSUS_POLICY_THRESHOLD_PP",
    "CONSENSUS_TARGET_HORIZON_MONTHS",
    "NewYorkFedSMEProvider",
    "interpret_consensus",
    "parse_sme_frame",
]
