"""Pure interpretation of market-consensus survey observations.

The survey is an optional forward-looking overlay.  It describes the
expected policy rate and Fed balance-sheet path, but it never determines
whether the current macro quadrant is actionable.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Optional

import pandas as pd


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


def _empty_result(as_of: pd.Timestamp) -> dict[str, Any]:
    return {
        "as_of": as_of,
        "quality": "UNAVAILABLE",
        "reasons": [],
        "blocks_quadrant": False,
        "survey_date": None,
        "selected_survey_date": None,
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
        survey_date = _timestamp(raw_record.get("survey_date"))
        horizon = _horizon_months(raw_record.get("horizon_months"))
        if survey_date is None:
            reasons.append("Consensus record has an invalid survey date")
            continue
        if horizon is None or not (
            CONSENSUS_MIN_HORIZON_MONTHS <= horizon <= CONSENSUS_MAX_HORIZON_MONTHS
        ):
            continue
        saw_horizon = True
        if survey_date > analysis_date:
            saw_future = True
            continue
        candidates.append(
            {
                "survey_date": survey_date,
                "horizon_months": int(horizon),
                "expected_dff": _finite_float(raw_record.get("expected_dff")),
                "expected_fed_assets": _finite_float(raw_record.get("expected_fed_assets")),
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
            # If a source repeats one horizon, prefer the newest vintage only
            # after the required horizon-distance and lower-horizon tie-breaks.
            -candidate["survey_date"].value,
        ),
    )

    survey_date = selected["survey_date"]
    horizon = selected["horizon_months"]
    result.update(
        {
            "survey_date": survey_date,
            "selected_survey_date": survey_date,
            "target_date": survey_date + pd.DateOffset(months=horizon),
            "selected_target_date": survey_date + pd.DateOffset(months=horizon),
            "horizon_months": horizon,
            "selected_horizon_months": horizon,
            "expected_dff": selected["expected_dff"],
            "expected_fed_assets": selected["expected_fed_assets"],
            "current_dff": _finite_float(current_dff),
            "current_fed_assets": _finite_float(current_fed_assets),
        }
    )

    age_days = int((analysis_date.normalize() - survey_date.normalize()).days)
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


__all__ = [
    "CONSENSUS_BALANCE_SHEET_THRESHOLD_PCT",
    "CONSENSUS_MAX_AGE_DAYS",
    "CONSENSUS_MAX_HORIZON_MONTHS",
    "CONSENSUS_MIN_HORIZON_MONTHS",
    "CONSENSUS_POLICY_THRESHOLD_PP",
    "CONSENSUS_TARGET_HORIZON_MONTHS",
    "interpret_consensus",
]
