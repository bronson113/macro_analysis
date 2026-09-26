"""Migrate the legacy compressed observation CSV into the committed SQLite store."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from config import OBSERVATIONS_DB, OBSERVATIONS_CSV
from storage import MacroStorage


DEFAULT_MAX_BYTES = 5_000_000


def migrate(
    source: Path = OBSERVATIONS_CSV,
    database: Path = OBSERVATIONS_DB,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    remove_source: bool = False,
) -> tuple[int, int]:
    """Migrate and verify data before checking size or removing the source."""
    if not source.exists() and not database.exists():
        raise FileNotFoundError(f"Neither observation source nor SQLite store exists: {source}")

    if source.exists():
        with tempfile.TemporaryDirectory(prefix="macro-observation-migration-") as temp_dir:
            temp = Path(temp_dir)
            storage = MacroStorage(
                indicators_csv=temp / "indicators.csv",
                observations_csv=None,
                observations_db=database,
                snapshots_csv=temp / "snapshots.csv",
                news_csv=temp / "news.csv",
                run_logs_csv=temp / "run_logs.csv",
            )
            row_count = storage.migrate_observations_csv(source)
            store = storage._observation_store
    else:
        from observation_sqlite import ObservationSQLiteStore

        store = ObservationSQLiteStore(database)
        row_count = store.row_count

    if row_count == 0:
        raise RuntimeError("Observation store is empty; refusing to remove or publish it")

    if store is None or store.integrity_check() != "ok":
        raise RuntimeError(f"SQLite integrity check failed for {database}")
    database_bytes = database.stat().st_size
    if database_bytes > max_bytes:
        raise RuntimeError(
            f"Observation SQLite store is too large: {database_bytes} bytes "
            f"(maximum {max_bytes})"
        )

    # The source is deleted only after the importer verifies the rows, SQLite
    # integrity passes, and the committed artifact meets its size limit.
    if remove_source and source.exists():
        source.unlink()
    return row_count, database_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=OBSERVATIONS_CSV)
    parser.add_argument("--database", type=Path, default=OBSERVATIONS_DB)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument(
        "--remove-source",
        action="store_true",
        help="Remove the legacy CSV after migration, integrity, and size checks pass",
    )
    args = parser.parse_args()
    row_count, database_bytes = migrate(
        args.source,
        args.database,
        max_bytes=args.max_bytes,
        remove_source=args.remove_source,
    )
    print(f"Verified {row_count:,} observation rows in SQLite ({database_bytes:,} bytes).")
    if args.remove_source:
        print("Removed the legacy observation CSV after verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
