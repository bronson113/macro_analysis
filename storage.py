"""Durable CSV persistence for the macro-analysis pipeline."""

import fcntl
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Union

import pandas as pd

from config import (
    FRED_SERIES,
    INDICATORS_CSV,
    MARKET_SENTIMENT_INDICATORS,
    NEWS_CSV,
    OBSERVATIONS_CSV,
    RUN_LOGS_CSV,
    SIGNALS_CSV,
    SNAPSHOTS_CSV,
    SOURCE_HEALTH_CSV,
    YAHOO_TICKERS,
)
from outcome_evaluation import SignalRecord
from source_health import SOURCE_HEALTH_COLUMNS, SourceHealth


CSV_SCHEMA_VERSION = 1

NEWS_COLUMNS = [
    "id", "date", "title", "summary", "source", "link", "category",
    "topic_tags", "interpretation_status", "published_at", "retrieved_at",
    "impact_score", "sentiment", "created_at",
]

SIGNAL_COLUMNS = [
    "signal_date", "sector_group", "instrument", "benchmark", "posture", "score",
    "coverage_pct", "uncertainty_json", "factor_snapshot_json", "created_at",
]

SNAPSHOT_COLUMNS = [
    "date", "net_liquidity", "fed_assets", "tga", "rrp", "treasury_10y", "treasury_2y",
    "spread_10y_2y", "high_yield_oas", "vix", "dxy", "sp500", "unemployment_rate",
    "cpi_yoy", "housing_yoy", "breakeven_10y", "m2_yoy", "policy_rate",
    "policy_rate_change_30d", "real_yield_10y", "cnn_fear_greed_index", "shiller_pe",
    "liquidity_regime", "yield_curve_regime", "credit_regime", "overall_regime", "created_at",
]

# Keep columns and versions in one place so new writers cannot silently drift apart.
CSV_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "indicators": {
        "version": CSV_SCHEMA_VERSION,
        "columns": ["key", "name", "source", "category", "frequency", "unit", "last_updated"],
    },
    "observations": {
        "version": CSV_SCHEMA_VERSION,
        "columns": ["indicator_key", "date", "value", "updated_at"],
    },
    "snapshots": {"version": CSV_SCHEMA_VERSION, "columns": SNAPSHOT_COLUMNS},
    "news": {"version": CSV_SCHEMA_VERSION, "columns": NEWS_COLUMNS},
    "run_logs": {
        "version": CSV_SCHEMA_VERSION,
        "columns": ["id", "run_time", "status", "records_updated", "message"],
    },
    "source_health": {"version": CSV_SCHEMA_VERSION, "columns": SOURCE_HEALTH_COLUMNS},
    "signals": {"version": CSV_SCHEMA_VERSION, "columns": SIGNAL_COLUMNS},
}


def atomic_write_csv(path: Union[str, Path], frame: pd.DataFrame) -> None:
    """Write a complete CSV then atomically replace ``path`` on the same filesystem.

    A failed write or replacement leaves the previously committed file untouched.  The
    temporary file is always removed, including when the caller intentionally tests a
    replacement failure.
    """
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            frame.to_csv(temporary_file, index=False)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
        # Persist the name update as well as the file data when the platform permits it.
        try:
            directory_fd = os.open(destination.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


class MacroStorage:
    """Read and mutate all CSV ledgers with schema and atomic-write guarantees."""

    def __init__(
        self,
        indicators_csv=INDICATORS_CSV,
        observations_csv=OBSERVATIONS_CSV,
        snapshots_csv=SNAPSHOTS_CSV,
        news_csv=NEWS_CSV,
        run_logs_csv=RUN_LOGS_CSV,
        signals_csv=None,
        source_health_csv=None,
    ):
        # RLock allows one public mutation to update multiple files without self-deadlock.
        self._lock = threading.RLock()
        self.indicators_csv = str(indicators_csv)
        self.observations_csv = str(observations_csv)
        self.snapshots_csv = str(snapshots_csv)
        self.news_csv = str(news_csv)
        self.run_logs_csv = str(run_logs_csv)
        self.signals_csv = str(
            signals_csv
            if signals_csv is not None
            else Path(self.snapshots_csv).parent / Path(SIGNALS_CSV).name
        )
        self.source_health_csv = str(
            source_health_csv
            if source_health_csv is not None
            else Path(self.snapshots_csv).parent / Path(SOURCE_HEALTH_CSV).name
        )
        self._csv_paths = {
            "indicators": Path(self.indicators_csv),
            "observations": Path(self.observations_csv),
            "snapshots": Path(self.snapshots_csv),
            "news": Path(self.news_csv),
            "run_logs": Path(self.run_logs_csv),
            "source_health": Path(self.source_health_csv),
            "signals": Path(self.signals_csv),
        }
        self._init_csvs()

    @staticmethod
    def _safe_concat(dfs: List[pd.DataFrame]) -> pd.DataFrame:
        non_empty = [
            df for df in dfs
            if df is not None and not df.empty and not df.dropna(how="all").empty
        ]
        if not non_empty:
            return pd.DataFrame()
        if len(non_empty) == 1:
            return non_empty[0].copy()
        return pd.concat(non_empty, ignore_index=True)

    @staticmethod
    def _upsert_rows(
        existing: pd.DataFrame, incoming: pd.DataFrame, key_columns: List[str]
    ) -> pd.DataFrame:
        """Update matching rows without discarding columns omitted by the writer.

        CSV schema migration deliberately retains operator-owned columns.  A normal
        writer knows only its canonical fields, so replacing an entire duplicate row
        would erase those retained values.  This helper updates only the fields the
        caller actually supplied while it is still inside the file-lock transaction.
        """
        updated = existing.drop_duplicates(subset=key_columns, keep="last").copy()
        for _, row in incoming.iterrows():
            matches = pd.Series(True, index=updated.index, dtype=bool)
            for column in key_columns:
                value = row[column]
                matches &= updated[column].isna() if pd.isna(value) else updated[column] == value
            matching_indexes = updated.index[matches]
            if len(matching_indexes):
                target_index = matching_indexes[-1]
                for column, value in row.items():
                    # Schema migration can create an all-blank column, which pandas
                    # rereads as float64.  Promote every explicitly updated column
                    # before scalar assignment so a timestamp or other text value
                    # remains valid across pandas versions.
                    if column not in updated:
                        updated[column] = pd.NA
                    if not pd.api.types.is_object_dtype(updated[column]):
                        updated[column] = updated[column].astype(object)
                    updated.at[target_index, column] = value
            else:
                updated = pd.concat([updated, pd.DataFrame([row])], ignore_index=True)
        return updated

    @staticmethod
    def _schema_columns(schema_name: str) -> List[str]:
        return list(CSV_SCHEMAS[schema_name]["columns"])

    @contextmanager
    def _file_lock(self, path: Path) -> Iterator[None]:
        """Acquire a process-cooperative sibling lock for one CSV mutation."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(f"{path.name}.lock")
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _read_csv_unlocked(self, path: Path, schema_name: str) -> pd.DataFrame:
        try:
            frame = pd.read_csv(path)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            frame = pd.DataFrame()
        return self._normalize_schema(frame, schema_name)

    def _normalize_schema(self, frame: pd.DataFrame, schema_name: str) -> pd.DataFrame:
        """Add canonical columns before retained unknown columns without dropping data."""
        canonical = self._schema_columns(schema_name)
        normalized = frame.copy()
        for column in canonical:
            if column not in normalized.columns:
                normalized[column] = pd.NA
        unknown = [column for column in normalized.columns if column not in canonical]
        return normalized[canonical + unknown]

    def _ensure_schema(self, path: Path, schema_name: str) -> None:
        with self._lock:
            with self._file_lock(path):
                try:
                    existing = pd.read_csv(path)
                except (FileNotFoundError, pd.errors.EmptyDataError):
                    existing = pd.DataFrame()
                normalized = self._normalize_schema(existing, schema_name)
                if not path.exists() or list(existing.columns) != list(normalized.columns):
                    atomic_write_csv(path, normalized)

    def _mutate_csv(
        self,
        path: Path,
        schema_name: str,
        mutation: Callable[[pd.DataFrame], pd.DataFrame],
    ) -> pd.DataFrame:
        """Read, mutate, fsync, and replace one CSV while its sibling lock is held."""
        with self._lock:
            with self._file_lock(path):
                existing = self._read_csv_unlocked(path, schema_name)
                updated = self._normalize_schema(mutation(existing.copy()), schema_name)
                atomic_write_csv(path, updated)
                return updated

    def _init_csvs(self) -> None:
        """Create and migrate every managed CSV through the same atomic writer."""
        for schema_name, path in self._csv_paths.items():
            self._ensure_schema(path, schema_name)
        self._seed_indicator_metadata()

    def _seed_indicator_metadata(self) -> None:
        now = datetime.now().isoformat()
        records = []
        for key, info in FRED_SERIES.items():
            records.append({
                "key": key,
                "name": info["name"],
                "source": "FRED",
                "category": self._categorize_key(key),
                "frequency": info.get("frequency", "daily"),
                "last_updated": now,
            })
        for key, ticker in YAHOO_TICKERS.items():
            records.append({
                "key": key,
                "name": f"{key.upper()} ({ticker})",
                "source": "YAHOO",
                "category": "Market Prices",
                "frequency": "daily",
                "last_updated": now,
            })
        for key, info in MARKET_SENTIMENT_INDICATORS.items():
            records.append({
                "key": key,
                "name": info["name"],
                "source": info["source"],
                "category": info.get("category", "Market Sentiment"),
                "frequency": info.get("frequency", "daily"),
                "last_updated": now,
            })
        seeded = pd.DataFrame(records)

        def add_or_refresh(existing: pd.DataFrame) -> pd.DataFrame:
            # Refresh only declared metadata.  Keeping the existing row preserves
            # operator-owned columns that the built-in seed cannot know about.
            refreshed = existing.drop_duplicates(subset=["key"], keep="last").copy()
            known_keys = set(refreshed["key"].dropna())
            new_rows = []
            for record in records:
                key = record["key"]
                if key in known_keys:
                    mask = refreshed["key"] == key
                    for column, value in record.items():
                        # Legacy sparse columns can be inferred as float because they
                        # contained only empty values; metadata is textual.
                        if not pd.api.types.is_object_dtype(refreshed[column]):
                            refreshed[column] = refreshed[column].astype(object)
                        refreshed.loc[mask, column] = value
                else:
                    new_rows.append(record)
            return self._safe_concat([refreshed, pd.DataFrame(new_rows)])

        self._mutate_csv(self._csv_paths["indicators"], "indicators", add_or_refresh)

    @staticmethod
    def _categorize_key(key: str) -> str:
        if any(token in key for token in ["fed", "repo", "tga", "m2", "deposits", "effr", "dff"]):
            return "Federal Reserve & Liquidity"
        if any(token in key for token in ["treasury", "spread"]):
            return "Rates & Yield Curve"
        if any(token in key for token in ["oas", "yield", "chicago_fed"]):
            return "Credit & Financial Conditions"
        if any(token in key for token in ["payrolls", "unemployment", "claims", "wage", "openings"]):
            return "Labor Market"
        if any(token in key for token in ["cpi", "pce", "breakeven"]):
            return "Inflation"
        if any(token in key for token in ["fear_greed", "sentiment"]):
            return "Market Sentiment"
        return "Economic Growth"

    def save_observations(self, indicator_key: str, df_obs: pd.DataFrame) -> int:
        if df_obs.empty:
            return 0
        to_save = df_obs.copy()
        to_save["indicator_key"] = indicator_key
        to_save["updated_at"] = datetime.now().isoformat()
        to_save = to_save[["indicator_key", "date", "value", "updated_at"]]

        def save(existing: pd.DataFrame) -> pd.DataFrame:
            return self._upsert_rows(existing, to_save, ["indicator_key", "date"])

        self._mutate_csv(self._csv_paths["observations"], "observations", save)

        def update_metadata(existing: pd.DataFrame) -> pd.DataFrame:
            existing.loc[existing["key"] == indicator_key, "last_updated"] = datetime.now().isoformat()
            return existing

        self._mutate_csv(self._csv_paths["indicators"], "indicators", update_metadata)
        return len(to_save)

    def save_news_events(self, news_items: List[Dict[str, Any]]) -> int:
        if not news_items:
            return 0
        new_rows = []
        for item in news_items:
            new_rows.append({
                "date": item.get("date", datetime.now().strftime("%Y-%m-%d")),
                "title": item["title"],
                "summary": item.get("summary", ""),
                "source": item.get("source", "News"),
                "link": item.get("link", ""),
                "category": item.get("category", "General Macro"),
                "topic_tags": self._serialize_topic_tags(item.get("topic_tags", [])),
                "interpretation_status": item.get("interpretation_status", "uninterpreted"),
                "published_at": item.get("published_at"),
                "retrieved_at": item.get("retrieved_at"),
                "impact_score": item.get("impact_score"),
                "sentiment": item.get("sentiment"),
                "created_at": datetime.now().isoformat(),
            })
        to_save = pd.DataFrame(new_rows)
        inserted = 0

        def save(existing: pd.DataFrame) -> pd.DataFrame:
            nonlocal inserted
            existing_keys = set(zip(existing["title"], existing["date"]))
            inserted = sum((row["title"], row["date"]) not in existing_keys for row in new_rows)
            max_id = existing["id"].max() if not existing.empty and pd.notna(existing["id"].max()) else 0
            combined = self._safe_concat([existing, to_save]).drop_duplicates(
                subset=["title", "date"], keep="first"
            )
            missing_ids = combined["id"].isna()
            if missing_ids.any():
                combined.loc[missing_ids, "id"] = range(
                    int(max_id) + 1, int(max_id) + 1 + int(missing_ids.sum())
                )
            return combined

        self._mutate_csv(self._csv_paths["news"], "news", save)
        return inserted

    def get_recent_news(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._lock:
            frame = self._read_csv_unlocked(self._csv_paths["news"], "news")
        if frame.empty:
            return []
        frame = frame.sort_values(by=["date", "id"], ascending=[False, False]).head(limit)
        records = frame.to_dict("records")
        for record in records:
            record["topic_tags"] = self._deserialize_topic_tags(record.get("topic_tags"))
            if self._is_missing(record.get("interpretation_status")):
                record["interpretation_status"] = "legacy_uninterpreted"
            for field in ("impact_score", "sentiment", "published_at", "retrieved_at"):
                if self._is_missing(record.get(field)):
                    record[field] = None
        return records

    @staticmethod
    def _serialize_topic_tags(tags: Any) -> str:
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = []
        if not isinstance(tags, (list, tuple, set)):
            tags = []
        return json.dumps(
            sorted({str(tag) for tag in tags if tag is not None and str(tag)}),
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize_topic_tags(value: Any) -> List[str]:
        if isinstance(value, (list, tuple, set)):
            return sorted({str(tag) for tag in value if tag is not None and str(tag)})
        if MacroStorage._is_missing(value):
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return sorted({str(tag) for tag in parsed if tag is not None and str(tag)})

    @staticmethod
    def _is_missing(value: Any) -> bool:
        return value is None or (
            not isinstance(value, (list, tuple, set, dict)) and pd.isna(value)
        )

    def get_latest_observation(self, indicator_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            frame = self._read_csv_unlocked(self._csv_paths["observations"], "observations")
        filtered = frame[frame["indicator_key"] == indicator_key]
        if filtered.empty:
            return None
        return filtered.sort_values(by="date", ascending=False).iloc[0].to_dict()

    def get_indicator_series(self, indicator_key: str, limit: int = 365) -> pd.DataFrame:
        with self._lock:
            frame = self._read_csv_unlocked(self._csv_paths["observations"], "observations")
        filtered = frame[frame["indicator_key"] == indicator_key]
        if filtered.empty:
            return pd.DataFrame(columns=["date", "value"])
        filtered = filtered.sort_values(by="date", ascending=False).head(limit).copy()
        filtered["date"] = pd.to_datetime(filtered["date"])
        return filtered.sort_values("date").reset_index(drop=True)[["date", "value"]]

    def save_daily_snapshot(self, snapshot_data: Dict[str, Any]) -> None:
        to_save = pd.DataFrame([snapshot_data])
        if "created_at" not in to_save.columns:
            to_save["created_at"] = datetime.now().isoformat()

        def save(existing: pd.DataFrame) -> pd.DataFrame:
            return self._upsert_rows(existing, to_save, ["date"])

        self._mutate_csv(self._csv_paths["snapshots"], "snapshots", save)

    def get_recent_snapshots(self, limit: int = 30) -> pd.DataFrame:
        with self._lock:
            frame = self._read_csv_unlocked(self._csv_paths["snapshots"], "snapshots")
        if frame.empty:
            return frame
        return frame.sort_values(by="date", ascending=False).head(limit).reset_index(drop=True)

    def save_signal_assessments(
        self, assessments: List[Dict[str, Any]], signal_date: Optional[str] = None
    ) -> int:
        if not assessments:
            return 0
        rows = []
        for assessment in assessments:
            candidate = dict(assessment)
            if signal_date is not None:
                candidate["signal_date"] = signal_date
            try:
                record = SignalRecord.from_mapping(candidate)
            except (TypeError, ValueError):
                continue
            values = record.to_mapping()
            rows.append({
                "signal_date": values["signal_date"],
                "sector_group": values["sector_group"],
                "instrument": values["instrument"],
                "benchmark": values["benchmark"],
                "posture": values["posture"],
                "score": values["score"],
                "coverage_pct": values["coverage_pct"],
                "uncertainty_json": self._stable_json(values["score_range"]),
                "factor_snapshot_json": self._stable_json(values["factor_snapshot"]),
                "created_at": datetime.now().isoformat(),
            })
        if not rows:
            return 0
        ledger_key = ["signal_date", "sector_group", "instrument", "benchmark"]
        inserted = 0

        def save(existing: pd.DataFrame) -> pd.DataFrame:
            nonlocal inserted
            existing = existing.drop_duplicates(subset=ledger_key, keep="first")
            existing_keys = {tuple(row[column] for column in ledger_key) for row in existing.to_dict("records")}
            new_rows = []
            for row in rows:
                record_key = tuple(row[column] for column in ledger_key)
                if record_key not in existing_keys:
                    new_rows.append(row)
                    existing_keys.add(record_key)
            inserted = len(new_rows)
            return self._safe_concat([existing, pd.DataFrame(new_rows, columns=SIGNAL_COLUMNS)])

        self._mutate_csv(self._csv_paths["signals"], "signals", save)
        return inserted

    def get_signal_assessments(self) -> List[Dict[str, Any]]:
        with self._lock:
            frame = self._read_csv_unlocked(self._csv_paths["signals"], "signals")
        if frame.empty:
            return []
        records = []
        for row in frame.sort_values(["signal_date", "sector_group", "instrument"]).to_dict("records"):
            try:
                record = SignalRecord.from_mapping({
                    "signal_date": row.get("signal_date"),
                    "sector_group": row.get("sector_group"),
                    "instrument": row.get("instrument"),
                    "benchmark": row.get("benchmark"),
                    "posture": row.get("posture"),
                    "score": row.get("score"),
                    "coverage_pct": row.get("coverage_pct"),
                    "uncertainty": self._load_json(row.get("uncertainty_json"), []),
                    "factor_snapshot": self._load_json(row.get("factor_snapshot_json"), {}),
                })
            except (TypeError, ValueError):
                continue
            records.append(record.to_mapping())
        return records

    @staticmethod
    def _stable_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _load_json(value: Any, fallback: Any) -> Any:
        if MacroStorage._is_missing(value):
            return fallback
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return fallback

    def log_run(self, status: str, records_updated: int, message: str) -> None:
        def save(existing: pd.DataFrame) -> pd.DataFrame:
            max_id = existing["id"].max() if not existing.empty and pd.notna(existing["id"].max()) else 0
            row = pd.DataFrame([{
                "id": int(max_id) + 1,
                "run_time": datetime.now().isoformat(),
                "status": status,
                "records_updated": records_updated,
                "message": message,
            }])
            return self._safe_concat([existing, row])

        self._mutate_csv(self._csv_paths["run_logs"], "run_logs", save)

    def save_source_health(
        self,
        health: Optional[Union[SourceHealth, Mapping[str, Any]]] = None,
        **values: Any,
    ) -> Dict[str, Any]:
        """Append one immutable source-result record to the health ledger."""
        if health is None:
            health = SourceHealth(**values)
        elif isinstance(health, Mapping):
            health = SourceHealth.from_mapping(health)
        if not isinstance(health, SourceHealth):
            raise TypeError("health must be a SourceHealth record or mapping")
        row = pd.DataFrame([health.to_mapping()])

        def save(existing: pd.DataFrame) -> pd.DataFrame:
            return self._safe_concat([existing, row])

        self._mutate_csv(self._csv_paths["source_health"], "source_health", save)
        return health.to_mapping()

    def get_latest_source_health(
        self, source: Optional[str] = None, fetch_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            frame = self._read_csv_unlocked(self._csv_paths["source_health"], "source_health")
        if source is not None:
            frame = frame[frame["source"] == source]
        if fetch_key is not None:
            frame = frame[frame["fetch_key"] == fetch_key]
        if frame.empty:
            return None
        latest = frame.sort_values("fetch_time", ascending=False).iloc[0].to_dict()
        return SourceHealth.from_mapping(latest).to_mapping()
