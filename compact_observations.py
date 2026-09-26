"""Remove repeated FRED history vintages while retaining each value change."""

import argparse
from pathlib import Path

import pandas as pd

from config import OBSERVATIONS_CSV
from storage import atomic_write_csv


def compact_repeated_fred_vintages(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the first vintage of each consecutive value run per observation."""
    if frame.empty:
        return frame.copy()
    fred = frame["source_url"].fillna("").str.startswith(
        "https://fred.stlouisfed.org/"
    ) & frame["vintage_date"].notna()
    candidates = frame.loc[fred].sort_values(
        ["indicator_key", "date", "vintage_date"], kind="stable"
    )
    groups = ["indicator_key", "date", "source_url", "unit", "release_date", "publication_date"]
    groups = [column for column in groups if column in candidates.columns]
    previous = candidates.groupby(groups, dropna=False, sort=False)["value"].shift()
    repeated = candidates["value"].eq(previous)
    return frame.drop(index=candidates.index[repeated]).reset_index(drop=True)


def compact_file(path: Path) -> tuple[int, int]:
    frame = pd.read_csv(path, low_memory=False)
    compacted = compact_repeated_fred_vintages(frame)
    if len(compacted) < len(frame):
        atomic_write_csv(path, compacted)
    return len(frame), len(compacted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=OBSERVATIONS_CSV)
    args = parser.parse_args()
    before, after = compact_file(args.path)
    print(f"Observation vintages: {before} rows before, {after} after")
