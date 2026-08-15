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

FED_ASSETS_MAX_AGE_DAYS = 14
TGA_MAX_AGE_DAYS = 14
RRP_MAX_AGE_DAYS = 7
NOMINAL_GDP_MAX_AGE_DAYS = 120
EFFR_MAX_AGE_DAYS = 7
IORB_MAX_AGE_DAYS = 7
SOFR_MAX_AGE_DAYS = 7
LIQUIDITY_MOMENTUM_THRESHOLD_PCT_GDP = 0.05
LIQUIDITY_MIN_HISTORY_WEEKS = 200

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


def reserve_liquidity_billions(
    fed_assets_millions: float,
    tga_millions: float,
    rrp_billions: float,
) -> float:
    """Return the reserve-liquidity proxy in billions of dollars.

    Fed total assets and the Treasury General Account are supplied in
    millions, while ON RRP is supplied in billions.  Keeping that unit
    conversion at this small pure boundary makes the source units explicit
    and prevents a raw-dollar series from being used accidentally.
    """

    return float(fed_assets_millions) / 1000.0 - float(tga_millions) / 1000.0 - float(rrp_billions)


def classify_liquidity_percentile(rank: float) -> str:
    """Classify a liquidity percentile using inclusive level boundaries."""

    try:
        numeric_rank = float(rank)
    except (TypeError, ValueError):
        return "INSUFFICIENT_DATA"
    if not math.isfinite(numeric_rank):
        return "INSUFFICIENT_DATA"
    if numeric_rank >= 60.0:
        return "ABUNDANT"
    if numeric_rank <= 40.0:
        return "SCARCE"
    return "NEUTRAL"


def _liquidity_weekly_dates(
    fed_assets: pd.DataFrame,
    as_of: pd.Timestamp,
) -> list[pd.Timestamp]:
    """Select one backward-looking Fed-assets observation per seven-day bin."""

    eligible = fed_assets.loc[fed_assets["date"] <= as_of].copy()
    if eligible.empty:
        return []

    current_date = pd.Timestamp(eligible.iloc[-1]["date"])
    elapsed_days = (current_date.normalize() - eligible["date"].dt.normalize()).dt.days
    eligible["week_bin"] = elapsed_days // 7
    selected = (
        eligible.sort_values("date")
        .groupby("week_bin", sort=True, as_index=False)
        .tail(1)
        .sort_values("date")
    )
    return [pd.Timestamp(date) for date in selected["date"].tolist()]


def _aligned_liquidity_rows(
    fed_assets: pd.DataFrame,
    tga: pd.DataFrame,
    rrp: pd.DataFrame,
    nominal_gdp: pd.DataFrame,
    as_of: pd.Timestamp,
) -> list[Dict[str, Any]]:
    """Join liquidity inputs at weekly Fed-assets dates without look-ahead."""

    source_specs = (
        ("fed_assets", fed_assets, FED_ASSETS_MAX_AGE_DAYS),
        ("tga", tga, TGA_MAX_AGE_DAYS),
        ("rrp", rrp, RRP_MAX_AGE_DAYS),
        ("nominal_gdp", nominal_gdp, NOMINAL_GDP_MAX_AGE_DAYS),
    )
    aligned: list[Dict[str, Any]] = []
    for weekly_date in _liquidity_weekly_dates(fed_assets, as_of):
        rows: Dict[str, pd.Series] = {}
        valid = True
        for name, frame, max_age in source_specs:
            row = _latest_on_or_before(frame, weekly_date)
            if row is None or _age_days(pd.Timestamp(row["date"]), weekly_date) > max_age:
                valid = False
                break
            rows[name] = row
        if not valid:
            continue

        fed_assets_millions = float(rows["fed_assets"]["value"])
        tga_millions = float(rows["tga"]["value"])
        rrp_billions = float(rows["rrp"]["value"])
        nominal_gdp_billions = float(rows["nominal_gdp"]["value"])
        if nominal_gdp_billions == 0.0:
            continue
        reserve_billions = reserve_liquidity_billions(
            fed_assets_millions,
            tga_millions,
            rrp_billions,
        )
        normalized_pct_gdp = 100.0 * reserve_billions / nominal_gdp_billions
        aligned.append(
            {
                "date": pd.Timestamp(weekly_date),
                "fed_assets_millions": fed_assets_millions,
                "fed_assets_date": pd.Timestamp(rows["fed_assets"]["date"]),
                "tga_millions": tga_millions,
                "tga_date": pd.Timestamp(rows["tga"]["date"]),
                "rrp_billions": rrp_billions,
                "rrp_date": pd.Timestamp(rows["rrp"]["date"]),
                "nominal_gdp_billions": nominal_gdp_billions,
                "nominal_gdp_date": pd.Timestamp(rows["nominal_gdp"]["date"]),
                "reserve_liquidity_billions": reserve_billions,
                "normalized_liquidity_pct_gdp": normalized_pct_gdp,
            }
        )
    return aligned


def _liquidity_money_market_means(
    effr: pd.DataFrame,
    iorb: pd.DataFrame,
    sofr: pd.DataFrame,
    as_of: pd.Timestamp,
) -> tuple[Optional[float], Optional[float], list[pd.Timestamp]]:
    """Return five-business-day mean EFFR/IORB and SOFR/IORB spreads."""

    lookups = []
    for frame in (effr, iorb, sofr):
        eligible = frame.loc[frame["date"] <= as_of]
        lookups.append({pd.Timestamp(row["date"]): float(row["value"]) for _, row in eligible.iterrows()})
    common_dates = set(lookups[0]).intersection(lookups[1], lookups[2])
    common_dates = sorted(date for date in common_dates if pd.Timestamp(date).weekday() < 5)
    selected_dates = common_dates[-5:]
    if len(selected_dates) < 5:
        return None, None, selected_dates

    effr_iorb = [100.0 * (lookups[0][date] - lookups[1][date]) for date in selected_dates]
    sofr_iorb = [100.0 * (lookups[2][date] - lookups[1][date]) for date in selected_dates]
    return float(sum(effr_iorb) / len(effr_iorb)), float(sum(sofr_iorb) / len(sofr_iorb)), selected_dates


def _empty_liquidity_result(as_of: pd.Timestamp) -> Dict[str, Any]:
    return {
        "as_of": as_of,
        "state": None,
        "core_state": None,
        "quality": "INSUFFICIENT_DATA",
        "reasons": [],
        "reserve_liquidity_billions": None,
        "normalized_liquidity_pct_gdp": None,
        "normalized_liquidity": None,
        "current_percentile": None,
        "liquidity_percentile": None,
        "historical_percentile": None,
        "historical_median": None,
        "historical_p40": None,
        "historical_p60": None,
        "historical_40th_percentile": None,
        "historical_60th_percentile": None,
        "threshold_40": None,
        "threshold_60": None,
        "history_start": None,
        "history_end": None,
        "history_sample_start": None,
        "history_sample_end": None,
        "history_count": 0,
        "momentum_30d": None,
        "momentum_30d_value": None,
        "momentum_30d_date": None,
        "momentum_90d": None,
        "momentum_90d_value": None,
        "momentum_90d_date": None,
        "effr_iorb_spread_bp": None,
        "sofr_iorb_spread_bp": None,
        "effr_iorb_pressure": None,
        "sofr_iorb_pressure": None,
        "pressure_flags": [],
        "corroboration_dates": [],
        "fed_assets": None,
        "fed_assets_observation": None,
        "fed_assets_date": None,
        "fed_assets_age_days": None,
        "fed_assets_value": None,
        "fed_assets_millions": None,
        "tga": None,
        "tga_observation": None,
        "tga_date": None,
        "tga_age_days": None,
        "tga_value": None,
        "tga_millions": None,
        "rrp": None,
        "rrp_observation": None,
        "rrp_date": None,
        "rrp_age_days": None,
        "rrp_value": None,
        "rrp_billions": None,
        "nominal_gdp": None,
        "nominal_gdp_observation": None,
        "nominal_gdp_date": None,
        "nominal_gdp_age_days": None,
        "nominal_gdp_value": None,
        "nominal_gdp_billions": None,
        "effr": None,
        "effr_observation": None,
        "effr_date": None,
        "effr_age_days": None,
        "effr_value": None,
        "iorb": None,
        "iorb_observation": None,
        "iorb_date": None,
        "iorb_age_days": None,
        "iorb_value": None,
        "sofr": None,
        "sofr_observation": None,
        "sofr_date": None,
        "sofr_age_days": None,
        "sofr_value": None,
        "dates": {},
        "ages": {},
        "values": {},
    }


def classify_liquidity_level(
    fed_assets: pd.DataFrame,
    tga: pd.DataFrame,
    rrp: pd.DataFrame,
    nominal_gdp: pd.DataFrame,
    effr: pd.DataFrame,
    iorb: pd.DataFrame,
    sofr: pd.DataFrame,
    as_of: pd.Timestamp,
) -> Dict[str, Any]:
    """Classify reserve liquidity by its historical GDP-normalized level.

    Fed total assets and TGA are expected in millions, ON RRP and nominal GDP
    in billions, and money-market rates in percentage points.  All joins are
    backward-looking from weekly Fed-assets observations; current level
    classification excludes that current observation from its percentile
    sample.
    """

    as_of = _timestamp(as_of)
    frames = {
        "fed_assets": _prepare_series(fed_assets),
        "tga": _prepare_series(tga),
        "rrp": _prepare_series(rrp),
        "nominal_gdp": _prepare_series(nominal_gdp),
        "effr": _prepare_series(effr),
        "iorb": _prepare_series(iorb),
        "sofr": _prepare_series(sofr),
    }
    result = _empty_liquidity_result(as_of)
    reasons: list[str] = []

    source_specs = (
        ("fed_assets", FED_ASSETS_MAX_AGE_DAYS, "Fed assets"),
        ("tga", TGA_MAX_AGE_DAYS, "TGA"),
        ("rrp", RRP_MAX_AGE_DAYS, "RRP"),
        ("nominal_gdp", NOMINAL_GDP_MAX_AGE_DAYS, "Nominal GDP"),
    )
    required_ok = True
    current_rows: Dict[str, Optional[pd.Series]] = {}
    for key, max_age, label in source_specs:
        frame = frames[key]
        row = _latest_on_or_before(frame, as_of)
        current_rows[key] = row
        if _has_nonfinite_on_or_before(frame, as_of):
            required_ok = False
            reasons.append(f"{label} contains a non-finite input value")
        elif row is None:
            required_ok = False
            reasons.append(f"Missing {key.replace('_', ' ')} observation on or before as_of")
        else:
            age = _age_days(pd.Timestamp(row["date"]), as_of)
            if age is not None and age > max_age:
                required_ok = False
                reasons.append(
                    f"{label} observation is stale ({age} days old; maximum {max_age})"
                )

    aligned = _aligned_liquidity_rows(
        frames["fed_assets"],
        frames["tga"],
        frames["rrp"],
        frames["nominal_gdp"],
        as_of,
    )
    current_anchor = (
        pd.Timestamp(current_rows["fed_assets"]["date"])
        if current_rows["fed_assets"] is not None
        else None
    )
    current_record = next(
        (row for row in aligned if current_anchor is not None and row["date"] == current_anchor),
        None,
    )
    if current_record is None:
        required_ok = False
        reasons.append("Missing complete weekly liquidity observation on or before as_of")
    else:
        result["reserve_liquidity_billions"] = _round(current_record["reserve_liquidity_billions"])
        result["normalized_liquidity_pct_gdp"] = _round(
            current_record["normalized_liquidity_pct_gdp"]
        )
        result["normalized_liquidity"] = result["normalized_liquidity_pct_gdp"]

        source_record_specs = (
            ("fed_assets", "fed_assets_millions"),
            ("tga", "tga_millions"),
            ("rrp", "rrp_billions"),
            ("nominal_gdp", "nominal_gdp_billions"),
        )
        for key, value_key in source_record_specs:
            value = _round(current_record[value_key])
            date = current_record[f"{key}_date"]
            age = _age_days(date, as_of)
            observation = {"date": date, "age_days": age, "value": value}
            result[key] = value
            result[f"{key}_observation"] = observation
            result[f"{key}_date"] = date
            result[f"{key}_age_days"] = age
            result[f"{key}_value"] = value
            if key == "fed_assets":
                result["fed_assets_millions"] = value
            elif key == "tga":
                result["tga_millions"] = value
            elif key == "rrp":
                result["rrp_billions"] = value
            elif key == "nominal_gdp":
                result["nominal_gdp_billions"] = value
            result["dates"][key] = date
            result["ages"][key] = age
            result["values"][key] = value

    # Historical level sample: use the trailing ten calendar years and never
    # include the current weekly observation in its own percentile.
    window_start = (as_of - pd.DateOffset(years=HISTORICAL_WINDOW_YEARS)).normalize()
    current_date = current_record["date"].normalize() if current_record is not None else None
    history = [
        row
        for row in aligned
        if row["date"].normalize() >= window_start
        and (current_date is None or row["date"].normalize() < current_date)
    ]
    history_values = pd.Series(
        [row["normalized_liquidity_pct_gdp"] for row in history],
        dtype="float64",
    )
    result["history_count"] = int(len(history))
    if history:
        result["history_start"] = history[0]["date"]
        result["history_end"] = history[-1]["date"]
        result["history_sample_start"] = result["history_start"]
        result["history_sample_end"] = result["history_end"]

    history_valid = True
    if len(history) < LIQUIDITY_MIN_HISTORY_WEEKS:
        history_valid = False
        reasons.append(
            "Liquidity history unavailable: "
            f"{len(history)} aligned weekly observations (minimum {LIQUIDITY_MIN_HISTORY_WEEKS})"
        )
    if history and result["history_end"] < result["history_start"] + pd.DateOffset(years=MIN_HISTORICAL_YEARS):
        history_valid = False
        reasons.append("Liquidity history unavailable: fewer than five years of observations")
    elif not history:
        history_valid = False
        reasons.append("Liquidity history unavailable: fewer than five years of observations")

    if current_record is not None and history:
        current_value = float(current_record["normalized_liquidity_pct_gdp"])
        result["current_percentile"] = _round(float((history_values <= current_value).mean() * 100.0), 1)
        result["liquidity_percentile"] = result["current_percentile"]
        result["historical_percentile"] = result["current_percentile"]
        result["historical_median"] = _round(float(history_values.median()))
        result["historical_p40"] = _round(float(history_values.quantile(0.40)))
        result["historical_p60"] = _round(float(history_values.quantile(0.60)))
        result["historical_40th_percentile"] = result["historical_p40"]
        result["historical_60th_percentile"] = result["historical_p60"]
        result["threshold_40"] = result["historical_p40"]
        result["threshold_60"] = result["historical_p60"]
        if history_valid:
            result["core_state"] = classify_liquidity_percentile(result["current_percentile"])

    # Independent momentum overlays use the nearest aligned observation on or
    # before each target date.
    if current_record is not None:
        for horizon_days, label in ((30, "30d"), (90, "90d")):
            target = as_of - pd.Timedelta(days=horizon_days)
            prior = next(
                (
                    row
                    for row in reversed(aligned)
                    if row["date"] <= target
                ),
                None,
            )
            if prior is None:
                reasons.append(
                    f"Liquidity {horizon_days}-day momentum unavailable: no complete historical measurement"
                )
                continue
            delta = float(current_record["normalized_liquidity_pct_gdp"]) - float(
                prior["normalized_liquidity_pct_gdp"]
            )
            result[f"momentum_{label}"] = classify_delta(
                delta,
                positive_label="IMPROVING",
                negative_label="DETERIORATING",
                stable_label="STABLE",
                threshold=LIQUIDITY_MOMENTUM_THRESHOLD_PCT_GDP,
            )
            result[f"momentum_{label}_value"] = _round(delta)
            result[f"momentum_{label}_date"] = prior["date"]

    # Current money-market observations are corroborating inputs.  They can
    # lower confidence or withhold the state, but never rewrite the history-
    # based core classification.
    corroboration_specs = (
        ("effr", EFFR_MAX_AGE_DAYS, "EFFR"),
        ("iorb", IORB_MAX_AGE_DAYS, "IORB"),
        ("sofr", SOFR_MAX_AGE_DAYS, "SOFR"),
    )
    corroboration_ok = True
    for key, max_age, label in corroboration_specs:
        frame = frames[key]
        row = _latest_on_or_before(frame, as_of)
        if row is not None:
            detail = _row_details(row, as_of)
            result[key] = detail["value"]
            result[f"{key}_observation"] = detail
            result[f"{key}_date"] = detail["date"]
            result[f"{key}_age_days"] = detail["age_days"]
            result[f"{key}_value"] = detail["value"]
            result["dates"][key] = detail["date"]
            result["ages"][key] = detail["age_days"]
            result["values"][key] = detail["value"]
        if _has_nonfinite_on_or_before(frame, as_of):
            corroboration_ok = False
            reasons.append(f"{label} contains a non-finite input value")
        elif row is None:
            corroboration_ok = False
            reasons.append(f"Missing {label} corroboration on or before as_of")
        elif _age_days(pd.Timestamp(row["date"]), as_of) > max_age:
            corroboration_ok = False
            reasons.append(
                f"{label} corroboration is stale ("
                f"{_age_days(pd.Timestamp(row['date']), as_of)} days old; maximum {max_age})"
            )

    effr_iorb_bp, sofr_iorb_bp, corroboration_dates = _liquidity_money_market_means(
        frames["effr"], frames["iorb"], frames["sofr"], as_of
    )
    result["effr_iorb_spread_bp"] = _round(effr_iorb_bp)
    result["sofr_iorb_spread_bp"] = _round(sofr_iorb_bp)
    result["corroboration_dates"] = corroboration_dates
    if effr_iorb_bp is None or sofr_iorb_bp is None:
        corroboration_ok = False
        reasons.append("Five-business-day money-market corroboration is unavailable")
    elif corroboration_ok:
        result["effr_iorb_pressure"] = bool(effr_iorb_bp >= -2.0)
        result["sofr_iorb_pressure"] = bool(sofr_iorb_bp >= 10.0)
    pressure_flags = []
    if result["effr_iorb_pressure"]:
        pressure_flags.append("EFFR_IORB")
        reasons.append("EFFR-IORB spread flags reserve pressure")
    if result["sofr_iorb_pressure"]:
        pressure_flags.append("SOFR_IORB")
        reasons.append("SOFR-IORB spread flags funding pressure")
    result["pressure_flags"] = pressure_flags

    if not required_ok or not history_valid:
        result["state"] = None
        result["core_state"] = None
        result["quality"] = "INSUFFICIENT_DATA"
    else:
        result["state"] = result["core_state"]
        if len(pressure_flags) >= 2:
            result["state"] = None
            result["quality"] = "INDETERMINATE_CONFLICT"
        else:
            result["quality"] = "PARTIAL" if reasons or not corroboration_ok or pressure_flags else "OK"
    if len(pressure_flags) >= 2:
        result["quality"] = "INDETERMINATE_CONFLICT"
        result["state"] = None
    result["reasons"] = reasons
    return result


__all__ = [
    "CORE_PCE_MAX_AGE_DAYS",
    "DFF_MAX_AGE_DAYS",
    "EFFR_MAX_AGE_DAYS",
    "FED_ASSETS_MAX_AGE_DAYS",
    "HISTORICAL_WINDOW_YEARS",
    "IORB_MAX_AGE_DAYS",
    "LIQUIDITY_MIN_HISTORY_WEEKS",
    "LIQUIDITY_MOMENTUM_THRESHOLD_PCT_GDP",
    "MIN_HISTORICAL_YEARS",
    "NOMINAL_GDP_MAX_AGE_DAYS",
    "POLICY_GAP_THRESHOLD_PP",
    "POLICY_MOMENTUM_THRESHOLD_PP",
    "RRP_MAX_AGE_DAYS",
    "RSTAR_MAX_AGE_DAYS",
    "SOFR_MAX_AGE_DAYS",
    "TGA_MAX_AGE_DAYS",
    "classify_delta",
    "classify_liquidity_level",
    "classify_liquidity_percentile",
    "classify_policy_gap",
    "classify_policy_level",
    "reserve_liquidity_billions",
]
