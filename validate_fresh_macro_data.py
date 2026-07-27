"""Fail CI when the daily pipeline lacks fresh data required by the macro skill."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from config import OBSERVATIONS_CSV


CORE_SERIES_MAX_AGE_DAYS = {
    "fed_total_assets": 10,
    "tga_balance": 10,
    "reverse_repo": 5,
    "dff": 5,
}
LIQUIDITY_SERIES = ("fed_total_assets", "tga_balance", "reverse_repo")
LOOKBACK_DAYS = 30


def validate_observations(path: Path, today: date | None = None) -> list[str]:
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

    errors = validate_observations(args.observations)
    if errors:
        print("Fresh macro data validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Fresh macro data validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
