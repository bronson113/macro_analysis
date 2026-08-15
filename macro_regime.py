"""Pure macro-regime calculations.

This module deliberately has no storage or network dependencies.  Callers
provide dated observations and an explicit point-in-time date, which keeps
the calculations usable both in the daily analyzer and in reproducible
historical tests.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Optional

import pandas as pd


POLICY_GAP_THRESHOLD_PP = 0.50
POLICY_MOMENTUM_THRESHOLD_PP = 0.10

DFF_MAX_AGE_DAYS = 7
CORE_PCE_MAX_AGE_DAYS = 75
RSTAR_MAX_AGE_DAYS = 180

HISTORICAL_WINDOW_YEARS = 10
MIN_HISTORICAL_YEARS = 5


def classify_delta(
    delta: Optional[float],
    positive_label: str,
    negative_label: str,
    stable_label: str,
    threshold: float,
) -> Optional[str]:
    """Classify a signed change using strict, symmetric boundaries.

    A value exactly on either threshold is stable.  ``None`` and non-finite
    values represent unavailable changes and therefore return ``None``.
    """

    if delta is None or pd.isna(delta):
        return None
    try:
        numeric_delta = float(delta)
        numeric_threshold = abs(float(threshold))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric_delta) or not math.isfinite(numeric_threshold):
        return None
    epsilon = 1e-12
    if (
        abs(numeric_delta - numeric_threshold) <= epsilon
        or abs(numeric_delta + numeric_threshold) <= epsilon
    ):
        return stable_label
    if numeric_delta > numeric_threshold:
        return positive_label
    if numeric_delta < -numeric_threshold:
        return negative_label
    return stable_label


def classify_policy_gap(real_policy_rate: Optional[float], rstar: Optional[float]) -> Optional[str]:
    """Classify policy from the real-rate gap to neutral real rate."""

    if real_policy_rate is None or rstar is None:
        return None
    try:
        gap = float(real_policy_rate) - float(rstar)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(gap):
        return None
    if gap > POLICY_GAP_THRESHOLD_PP:
        return "RESTRICTIVE"
    if gap < -POLICY_GAP_THRESHOLD_PP:
        return "ACCOMMODATIVE"
    return "NEUTRAL"


def _timestamp(value: Any) -> pd.Timestamp:
    """Return a timezone-naive timestamp suitable for point-in-time joins."""

    result = pd.Timestamp(value)
    if result.tzinfo is not None:
        result = result.tz_convert(None)
    return result


def _prepare_series(frame: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Normalize a source frame without mutating the caller's object."""

    if frame is None or not isinstance(frame, pd.DataFrame):
        result = pd.DataFrame(columns=["date", "value"])
        result.attrs["nonfinite_dates"] = []
        return result
    if "date" not in frame.columns or "value" not in frame.columns:
        result = pd.DataFrame(columns=["date", "value"])
        result.attrs["nonfinite_dates"] = []
        return result

    result = frame.loc[:, ["date", "value"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce", utc=True).dt.tz_convert(None)
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    finite_values = result["value"].map(
        lambda value: bool(pd.notna(value)) and math.isfinite(float(value))
    )
    invalid_mask = result["date"].notna() & ~finite_values
    nonfinite_dates = result.loc[invalid_mask, "date"].tolist()
    result = result.loc[~invalid_mask].dropna(subset=["date", "value"])
    result = result.sort_values("date").drop_duplicates("date", keep="last")
    result = result.reset_index(drop=True)
    result.attrs["nonfinite_dates"] = nonfinite_dates
    return result


def _has_nonfinite_on_or_before(frame: pd.DataFrame, as_of: pd.Timestamp) -> bool:
    return any(pd.Timestamp(date) <= as_of for date in frame.attrs.get("nonfinite_dates", []))


def _latest_on_or_before(frame: pd.DataFrame, as_of: pd.Timestamp) -> Optional[pd.Series]:
    if frame.empty:
        return None
    eligible = frame.loc[frame["date"] <= as_of]
    if eligible.empty:
        return None
    return eligible.iloc[-1]


def _age_days(observation_date: Optional[pd.Timestamp], as_of: pd.Timestamp) -> Optional[int]:
    if observation_date is None:
        return None
    return int((as_of.normalize() - observation_date.normalize()).days)


def _round(value: Optional[float], digits: int = 3) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    return round(numeric_value, digits) if math.isfinite(numeric_value) else None


def _row_details(row: Optional[pd.Series], as_of: pd.Timestamp) -> Dict[str, Any]:
    if row is None:
        return {"date": None, "age_days": None, "value": None}
    date = pd.Timestamp(row["date"])
    return {
        "date": date,
        "age_days": _age_days(date, as_of),
        "value": _round(float(row["value"])),
    }


def _value_row_at_or_before(frame: pd.DataFrame, target: pd.Timestamp) -> Optional[pd.Series]:
    return _latest_on_or_before(frame, target)


def _core_pce_measurement(
    core_pce: pd.DataFrame,
    target: pd.Timestamp,
) -> Optional[Dict[str, Any]]:
    """Return a point-in-time trailing-year PCE inflation measurement."""

    latest = _value_row_at_or_before(core_pce, target)
    if latest is None:
        return None

    latest_date = pd.Timestamp(latest["date"])
    year_ago_target = (latest_date - pd.DateOffset(years=1)).normalize()
    same_period = core_pce.loc[core_pce["date"].dt.normalize() == year_ago_target]
    prior = same_period.iloc[-1] if not same_period.empty else None
    if prior is None or float(prior["value"]) == 0:
        return {
            "date": latest_date,
            "value": float(latest["value"]),
            "prior_date": None,
            "prior_value": None,
            "yoy": None,
        }

    yoy = (float(latest["value"]) / float(prior["value"]) - 1.0) * 100.0
    return {
        "date": latest_date,
        "value": float(latest["value"]),
        "prior_date": pd.Timestamp(prior["date"]),
        "prior_value": float(prior["value"]),
        "yoy": yoy,
    }


def _policy_measurement_at(
    dff: pd.DataFrame,
    core_pce: pd.DataFrame,
    rstar: pd.DataFrame,
    target: pd.Timestamp,
) -> Optional[Dict[str, Any]]:
    """Build a historical policy measurement without applying freshness rules."""

    dff_row = _value_row_at_or_before(dff, target)
    rstar_row = _value_row_at_or_before(rstar, target)
    pce = _core_pce_measurement(core_pce, target)
    if dff_row is None or rstar_row is None or pce is None or pce["yoy"] is None:
        return None

    real_rate = float(dff_row["value"]) - float(pce["yoy"])
    gap = real_rate - float(rstar_row["value"])
    return {
        "date": pd.Timestamp(dff_row["date"]),
        "real_policy_rate": real_rate,
        "policy_gap": gap,
        "dff": dff_row,
        "pce": pce,
        "rstar": rstar_row,
    }


def _real_policy_measurement_at(
    dff: pd.DataFrame,
    core_pce: pd.DataFrame,
    target: pd.Timestamp,
) -> Optional[Dict[str, Any]]:
    """Build a historical real-policy-rate measurement.

    Historical percentile context is a percentile of the real policy rate,
    not of today's neutral-rate gap.  It therefore does not require an
    historical r-star vintage for every candidate observation.
    """

    dff_row = _value_row_at_or_before(dff, target)
    pce = _core_pce_measurement(core_pce, target)
    if dff_row is None or pce is None or pce["yoy"] is None:
        return None
    return {
        "date": pd.Timestamp(dff_row["date"]),
        "dff_date": pd.Timestamp(dff_row["date"]),
        "pce_date": pd.Timestamp(pce["date"]),
        "real_policy_rate": float(dff_row["value"]) - float(pce["yoy"]),
    }


def _historical_percentile(
    current_real_policy_rate: float,
    dff: pd.DataFrame,
    core_pce: pd.DataFrame,
    as_of: pd.Timestamp,
    current_dff_date: pd.Timestamp,
    current_pce_date: pd.Timestamp,
) -> tuple[Optional[float], Optional[pd.Timestamp], Optional[pd.Timestamp], int, Optional[str]]:
    """Calculate the current real policy rate's trailing percentile."""

    window_start = as_of - pd.DateOffset(years=HISTORICAL_WINDOW_YEARS)
    candidates: Iterable[pd.Timestamp]
    window_start = window_start.normalize()
    current_dff_date = pd.Timestamp(current_dff_date).normalize()
    current_pce_date = pd.Timestamp(current_pce_date).normalize()
    if core_pce.empty:
        candidates = ()
    else:
        candidates = core_pce.loc[
            (core_pce["date"] >= window_start) & (core_pce["date"] <= as_of), "date"
        ].tolist()

    historical_rates = []
    historical_dates = []
    for candidate in candidates:
        measurement = _real_policy_measurement_at(dff, core_pce, pd.Timestamp(candidate))
        if measurement is None:
            continue
        measurement_date = measurement["date"].normalize()
        # Filter on the actual backward-filled source date, not the PCE
        # candidate date used to discover it.
        if measurement_date < window_start or measurement_date > as_of.normalize():
            continue
        # The current observation must not be part of its own percentile. A
        # measurement is current only when both source dates match.
        if (
            measurement["dff_date"].normalize() == current_dff_date
            and measurement["pce_date"].normalize() == current_pce_date
        ):
            continue
        historical_rates.append(float(measurement["real_policy_rate"]))
        historical_dates.append(pd.Timestamp(measurement["date"]))

    if not historical_rates:
        return None, None, None, 0, "Historical percentile unavailable: fewer than five years of observations"

    sample_start = min(historical_dates)
    sample_end = max(historical_dates)
    if sample_end < sample_start + pd.DateOffset(years=MIN_HISTORICAL_YEARS):
        return (
            None,
            sample_start,
            sample_end,
            len(historical_rates),
            "Historical percentile unavailable: fewer than five years of observations",
        )

    values = pd.Series(historical_rates, dtype="float64")
    percentile = float((values <= float(current_real_policy_rate)).mean() * 100.0)
    return round(percentile, 1), sample_start, sample_end, len(values), None


def _momentum(
    current_gap: float,
    horizon_days: int,
    dff: pd.DataFrame,
    core_pce: pd.DataFrame,
    rstar: pd.DataFrame,
    as_of: pd.Timestamp,
) -> tuple[Optional[str], Optional[float], Optional[pd.Timestamp]]:
    target = as_of - pd.Timedelta(days=horizon_days)
    prior = _policy_measurement_at(dff, core_pce, rstar, target)
    if prior is None:
        return None, None, None
    delta = float(current_gap) - float(prior["policy_gap"])
    label = classify_delta(
        delta,
        positive_label="TIGHTENING",
        negative_label="EASING",
        stable_label="STABLE",
        threshold=POLICY_MOMENTUM_THRESHOLD_PP,
    )
    return label, _round(delta), pd.Timestamp(prior["date"])


def _empty_policy_result(as_of: pd.Timestamp) -> Dict[str, Any]:
    return {
        "as_of": as_of,
        "state": None,
        "quality": "INSUFFICIENT_DATA",
        "reasons": [],
        "dff": None,
        "dff_observation": None,
        "dff_date": None,
        "dff_age_days": None,
        "dff_value": None,
        "core_pce": None,
        "core_pce_observation": None,
        "core_pce_date": None,
        "core_pce_age_days": None,
        "core_pce_value": None,
        "core_pce_base_date": None,
        "core_pce_base_value": None,
        "core_pce_yoy": None,
        "core_pce_yoy_pct": None,
        "rstar": None,
        "rstar_observation": None,
        "rstar_date": None,
        "rstar_age_days": None,
        "rstar_value": None,
        "neutral_real_rate": None,
        "neutral_real_rate_date": None,
        "neutral_real_rate_age_days": None,
        "real_policy_rate": None,
        "real_policy_rate_pct": None,
        "policy_gap": None,
        "policy_gap_pct": None,
        "historical_percentile": None,
        "history_start": None,
        "history_end": None,
        "history_count": 0,
        "momentum_30d": None,
        "momentum_30d_value": None,
        "momentum_30d_date": None,
        "momentum_90d": None,
        "momentum_90d_value": None,
        "momentum_90d_date": None,
        "dates": {},
        "ages": {},
        "values": {},
    }


def classify_policy_level(
    dff: pd.DataFrame,
    core_pce: pd.DataFrame,
    rstar: pd.DataFrame,
    as_of: pd.Timestamp,
) -> Dict[str, Any]:
    """Classify monetary policy from its current real-rate level.

    ``dff`` contains a daily effective-federal-funds-rate percentage,
    ``core_pce`` contains the core PCE price index, and ``rstar`` contains
    neutral real-rate estimates.  All observations after ``as_of`` are
    ignored.  Required inputs are rejected when their latest point-in-time
    observation exceeds its source-specific freshness limit.
    """

    as_of = _timestamp(as_of)
    dff_frame = _prepare_series(dff)
    pce_frame = _prepare_series(core_pce)
    rstar_frame = _prepare_series(rstar)
    result = _empty_policy_result(as_of)

    dff_row = _latest_on_or_before(dff_frame, as_of)
    pce_measurement = _core_pce_measurement(pce_frame, as_of)
    rstar_row = _latest_on_or_before(rstar_frame, as_of)

    dff_details = _row_details(dff_row, as_of)
    pce_details = _row_details(
        pd.Series({"date": pce_measurement["date"], "value": pce_measurement["value"]})
        if pce_measurement is not None
        else None,
        as_of,
    )
    rstar_details = _row_details(rstar_row, as_of)

    result.update(
        {
            "dff": dff_details["value"],
            "dff_observation": dff_details,
            "dff_date": dff_details["date"],
            "dff_age_days": dff_details["age_days"],
            "dff_value": dff_details["value"],
            "core_pce": pce_details["value"],
            "core_pce_observation": pce_details,
            "core_pce_date": pce_details["date"],
            "core_pce_age_days": pce_details["age_days"],
            "core_pce_value": pce_details["value"],
            "rstar": rstar_details["value"],
            "rstar_observation": rstar_details,
            "rstar_date": rstar_details["date"],
            "rstar_age_days": rstar_details["age_days"],
            "rstar_value": rstar_details["value"],
            "neutral_real_rate": rstar_details["value"],
            "neutral_real_rate_date": rstar_details["date"],
            "neutral_real_rate_age_days": rstar_details["age_days"],
            "dates": {
                "dff": dff_details["date"],
                "core_pce": pce_details["date"],
                "rstar": rstar_details["date"],
            },
            "ages": {
                "dff": dff_details["age_days"],
                "core_pce": pce_details["age_days"],
                "rstar": rstar_details["age_days"],
            },
            "values": {
                "dff": dff_details["value"],
                "core_pce": pce_details["value"],
                "rstar": rstar_details["value"],
            },
        }
    )

    reasons = []
    required_ok = True

    for source_name, frame in (
        ("DFF", dff_frame),
        ("Core PCE", pce_frame),
        ("R-star", rstar_frame),
    ):
        if _has_nonfinite_on_or_before(frame, as_of):
            required_ok = False
            reasons.append(f"{source_name} contains a non-finite input value")

    if dff_row is None:
        required_ok = False
        if not _has_nonfinite_on_or_before(dff_frame, as_of):
            reasons.append("Missing dff observation on or before as_of")
    elif dff_details["age_days"] > DFF_MAX_AGE_DAYS:
        required_ok = False
        reasons.append(f"DFF observation is stale ({dff_details['age_days']} days old; maximum {DFF_MAX_AGE_DAYS})")

    if pce_measurement is None:
        required_ok = False
        if not _has_nonfinite_on_or_before(pce_frame, as_of):
            reasons.append("Missing core PCE observation on or before as_of")
    else:
        if pce_details["age_days"] > CORE_PCE_MAX_AGE_DAYS:
            required_ok = False
            reasons.append(
                f"Core PCE observation is stale ({pce_details['age_days']} days old; maximum {CORE_PCE_MAX_AGE_DAYS})"
            )
        if pce_measurement["yoy"] is None:
            required_ok = False
            reasons.append("Missing core PCE observation 12 months earlier")

    if rstar_row is None:
        required_ok = False
        if not _has_nonfinite_on_or_before(rstar_frame, as_of):
            reasons.append("Missing r-star estimate on or before as_of")
    elif rstar_details["age_days"] > RSTAR_MAX_AGE_DAYS:
        required_ok = False
        reasons.append(
            f"R-star estimate is stale ({rstar_details['age_days']} days old; maximum {RSTAR_MAX_AGE_DAYS})"
        )

    if pce_measurement is not None:
        result["core_pce_base_date"] = pce_measurement["prior_date"]
        result["core_pce_base_value"] = _round(pce_measurement["prior_value"])
        result["core_pce_yoy"] = _round(pce_measurement["yoy"])
        result["core_pce_yoy_pct"] = result["core_pce_yoy"]

    if not required_ok:
        result["quality"] = "INSUFFICIENT_DATA"
        result["reasons"] = reasons
        return result

    real_policy_rate = float(dff_row["value"]) - float(pce_measurement["yoy"])
    policy_gap = real_policy_rate - float(rstar_row["value"])
    result["real_policy_rate"] = _round(real_policy_rate)
    result["real_policy_rate_pct"] = result["real_policy_rate"]
    result["rstar_value"] = _round(float(rstar_row["value"]))
    result["policy_gap"] = _round(policy_gap)
    result["policy_gap_pct"] = result["policy_gap"]
    result["state"] = classify_policy_gap(real_policy_rate, float(rstar_row["value"]))

    (
        result["historical_percentile"],
        result["history_start"],
        result["history_end"],
        result["history_count"],
        history_reason,
    ) = _historical_percentile(
        real_policy_rate,
        dff_frame,
        pce_frame,
        as_of,
        pd.Timestamp(dff_row["date"]),
        pd.Timestamp(pce_measurement["date"]),
    )
    if history_reason:
        reasons.append(history_reason)

    for horizon_days, label in ((30, "30d"), (90, "90d")):
        momentum_label, momentum_value, momentum_date = _momentum(
            policy_gap, horizon_days, dff_frame, pce_frame, rstar_frame, as_of
        )
        result[f"momentum_{label}"] = momentum_label
        result[f"momentum_{label}_value"] = momentum_value
        result[f"momentum_{label}_date"] = momentum_date
        if momentum_label is None:
            reasons.append(f"Policy {horizon_days}-day momentum unavailable: no complete historical measurement")

    result["quality"] = "PARTIAL" if reasons else "OK"
    result["reasons"] = reasons
    return result


__all__ = [
    "CORE_PCE_MAX_AGE_DAYS",
    "DFF_MAX_AGE_DAYS",
    "HISTORICAL_WINDOW_YEARS",
    "MIN_HISTORICAL_YEARS",
    "POLICY_GAP_THRESHOLD_PP",
    "POLICY_MOMENTUM_THRESHOLD_PP",
    "RSTAR_MAX_AGE_DAYS",
    "classify_delta",
    "classify_policy_gap",
    "classify_policy_level",
]
