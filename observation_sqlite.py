"""Compact SQLite storage for observation histories."""

from __future__ import annotations

import io
import lzma
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Callable, Mapping, Optional, Union

import pandas as pd


FrameMerger = Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]


class ObservationSQLiteStore:
    """Store one LZMA-compressed CSV payload per indicator in SQLite."""

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            # FULL auto-vacuum keeps the committed database compact as payloads
            # are replaced by later runs. Set it before creating the first table.
            connection.execute("PRAGMA page_size = 4096")
            connection.execute("PRAGMA auto_vacuum = FULL")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    indicator_key TEXT PRIMARY KEY,
                    payload BLOB NOT NULL,
                    row_count INTEGER NOT NULL
                ) WITHOUT ROWID
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=60)
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 60000")
        return connection

    @staticmethod
    def _compress(frame: pd.DataFrame) -> bytes:
        # The SQLite primary key carries the indicator key once per series.
        # Keep the CSV header so each payload still describes its own schema.
        payload_frame = frame.drop(columns=["indicator_key"], errors="ignore")
        csv_bytes = payload_frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
        return lzma.compress(csv_bytes, preset=6)

    @staticmethod
    def _decompress(payload: bytes) -> pd.DataFrame:
        csv_bytes = lzma.decompress(payload)
        if not csv_bytes:
            return pd.DataFrame()
        return pd.read_csv(io.BytesIO(csv_bytes), low_memory=False)

    @property
    def is_empty(self) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(row_count), 0) FROM observations"
            ).fetchone()
        return not row or row[0] == 0

    @property
    def row_count(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(row_count), 0) FROM observations"
            ).fetchone()
        return int(row[0] if row else 0)

    def read_indicator(self, indicator_key: str) -> pd.DataFrame:
        """Decompress only one indicator's payload."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM observations WHERE indicator_key = ?",
                (indicator_key,),
            ).fetchone()
        if not row:
            return pd.DataFrame()
        frame = self._decompress(row[0])
        if "indicator_key" not in frame.columns:
            frame.insert(0, "indicator_key", indicator_key)
        return frame

    def read_all(self) -> pd.DataFrame:
        """Decompress all indicators for reports and maintenance tools."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT indicator_key, payload FROM observations ORDER BY indicator_key"
            ).fetchall()
        frames = []
        for indicator_key, payload in rows:
            frame = self._decompress(payload)
            if "indicator_key" not in frame.columns:
                frame.insert(0, "indicator_key", indicator_key)
            frames.append(frame)
        frames = [frame for frame in frames if not frame.empty]
        return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()

    def update_batches(
        self,
        incoming: Mapping[str, pd.DataFrame],
        merge: FrameMerger,
    ) -> int:
        """Merge several indicators and commit them together in one transaction."""
        batches = [(key, frame) for key, frame in incoming.items() if not frame.empty]
        if not batches:
            return 0
        changed_rows = 0
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            for indicator_key, frame in batches:
                row = connection.execute(
                    "SELECT payload FROM observations WHERE indicator_key = ?",
                    (indicator_key,),
                ).fetchone()
                existing = self._decompress(row[0]) if row else pd.DataFrame()
                if row and "indicator_key" not in existing.columns:
                    existing.insert(0, "indicator_key", indicator_key)
                updated = merge(existing, frame)
                payload = self._compress(updated)
                connection.execute(
                    """
                    INSERT INTO observations(indicator_key, payload, row_count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(indicator_key) DO UPDATE SET
                        payload = excluded.payload,
                        row_count = excluded.row_count
                    """,
                    (indicator_key, payload, len(updated)),
                )
                changed_rows += len(frame)
            connection.commit()
        return changed_rows

    def replace_all(self, by_indicator: Mapping[str, pd.DataFrame]) -> int:
        """Replace the complete store in one transaction for verified migrations."""
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM observations")
            row_count = 0
            for indicator_key, frame in by_indicator.items():
                if frame.empty:
                    continue
                connection.execute(
                    "INSERT INTO observations(indicator_key, payload, row_count) VALUES (?, ?, ?)",
                    (indicator_key, self._compress(frame), len(frame)),
                )
                row_count += len(frame)
            connection.commit()
        return row_count

    def integrity_check(self) -> Optional[str]:
        with closing(self._connect()) as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
        return row[0] if row else None


def read_observations(path: Union[str, Path]) -> pd.DataFrame:
    """Read a SQLite observation store or a legacy CSV fixture."""
    source = Path(path)
    if source.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        if not source.exists():
            return pd.DataFrame()
        return ObservationSQLiteStore(source).read_all()
    try:
        return pd.read_csv(source, low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def count_observations(path: Union[str, Path]) -> int:
    """Count rows without decompressing SQLite payloads for CLI status output."""
    source = Path(path)
    if source.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        if not source.exists():
            return 0
        return ObservationSQLiteStore(source).row_count
    return len(read_observations(source))
