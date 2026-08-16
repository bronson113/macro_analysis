"""Fail CI when the daily pipeline lacks fresh data required by the macro skill."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from config import OBSERVATIONS_CSV, SOURCE_HEALTH_CSV


CORE_SERIES_MAX_AGE_DAYS = {
    "fed_total_assets": 14,
    "tga_balance": 14,
    "reverse_repo": 7,
    "nominal_gdp": 120,
    "dff": 7,
    "core_pce": 75,
    "rstar": 180,
    "effr": 7,
    "iorb": 7,
    "sofr": 7,
}
LIQUIDITY_SERIES = ("fed_total_assets", "tga_balance", "reverse_repo")
LOOKBACK_DAYS = 30
EXPECTED_UNITS = {
    "fed_total_assets": {"millions"},
    "tga_balance": {"millions"},
    "reverse_repo": {"billions"},
    "nominal_gdp": {"billions"},
    "dff": {"percent"},
    "effr": {"percent"},
    "iorb": {"percent"},
    "sofr": {"percent"},
    "core_pce": {"index"},
    "rstar": {"percent"},
}


def validate_observations(
    path: Path,
    today: date | None = None,
    source_health_path: Path | None = None,
) -> list[str]:
    """Return validation errors for the policy and reserve-liquidity gate inputs."""
    today = today or date.today()
    if not path.exists():
        return [f"Missing observations file: {path}"]

    frame = pd.read_csv(path)
    required_columns = {"indicator_key", "date", "value"}
    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        return [f"Observations file missing columns: {', '.join(sorted(missing_columns))}"]

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["indicator_key", "date", "value"])

    errors: list[str] = []
    series_frames: dict[str, pd.DataFrame] = {}
    for key, max_age_days in CORE_SERIES_MAX_AGE_DAYS.items():
        series = frame[frame["indicator_key"] == key].sort_values("date")
        series_frames[key] = series
        if series.empty:
            errors.append(f"{key}: no observations")
            continue

        latest = series.iloc[-1]["date"]
        age_days = (today - latest).days
        if age_days < 0:
            errors.append(f"{key}: latest observation {latest} is in the future")
        elif age_days > max_age_days:
            errors.append(
                f"{key}: latest observation {latest} is stale "
                f"({age_days} days old; maximum {max_age_days})"
            )

        if key == "nominal_gdp" and (series["value"] <= 0).any():
            errors.append("nominal_gdp: non-positive GDP value is invalid")
        if key == "nominal_gdp":
            mis_scaled = series.loc[
                ~series["value"].between(1_000.0, 1_000_000.0)
            ]
            if not mis_scaled.empty and (series["value"] > 0).all():
                errors.append(
                    "nominal_gdp: value appears mis-scaled for billions "
                    "(expected roughly 1,000 to 1,000,000)"
                )
        if "unit" in series.columns:
            units = {
                str(unit).strip().lower()
                for unit in series["unit"].dropna()
                if str(unit).strip()
            }
            expected = EXPECTED_UNITS.get(key, set())
            if expected and units and not units.issubset(expected):
                errors.append(
                    f"{key}: unexpected source unit(s) {', '.join(sorted(units))}; "
                    f"expected {', '.join(sorted(expected))}"
                )

    if source_health_path is not None:
        health_path = Path(source_health_path)
        if not health_path.exists():
            errors.append(f"source health: missing health file {health_path}")
        else:
            try:
                health = pd.read_csv(health_path)
            except (OSError, pd.errors.EmptyDataError) as error:
                errors.append(f"source health: could not read health file ({error})")
                health = pd.DataFrame()
            if health.empty or "fetch_key" not in health.columns:
                errors.append("source health: file has no fetch_key records")
            else:
                if "fetch_time" in health.columns:
                    health = health.sort_values("fetch_time", kind="stable")
                latest_health = health.drop_duplicates("fetch_key", keep="last")
                for key in CORE_SERIES_MAX_AGE_DAYS:
                    row = latest_health[latest_health["fetch_key"] == key]
                    if row.empty:
                        errors.append(f"{key}: source health record is missing")
                        continue
                    status = str(row.iloc[-1].get("status", "")).upper()
                    stale = str(row.iloc[-1].get("is_stale", "")).lower() in {"true", "1", "yes"}
                    if status != "CURRENT" or stale:
                        errors.append(
                            f"{key}: source health is not current (status={status or 'UNKNOWN'})"
                        )

    for key in (*LIQUIDITY_SERIES, "dff"):
        series = series_frames.get(key)
        if series is None or series.empty:
            continue
        latest = series.iloc[-1]["date"]
        cutoff = latest - timedelta(days=LOOKBACK_DAYS)
        if series[series["date"] <= cutoff].empty:
            errors.append(
                f"{key}: no observation on or before {cutoff} for the "
                f"{LOOKBACK_DAYS}-day trend calculation"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--observations",
        type=Path,
        default=OBSERVATIONS_CSV,
        help="Path to macro observations CSV",
    )
    args = parser.parse_args()

    errors = validate_observations(
        args.observations,
        source_health_path=SOURCE_HEALTH_CSV,
    )
    if errors:
        print("Fresh macro data validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Fresh macro data validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
