"""Offline-testable ingestion for the New York Fed HLW r-star workbook."""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Optional

import pandas as pd
import requests

from config import HLW_RSTAR_SOURCE


def _timestamp(value: Any) -> Optional[pd.Timestamp]:
    if value is None or (not isinstance(value, (pd.Timestamp, datetime)) and pd.isna(value)):
        return None
    try:
        if isinstance(value, str):
            quarter = re.fullmatch(r"\s*(\d{4})\s*Q([1-4])\s*", value, flags=re.IGNORECASE)
            if quarter:
                return pd.Period(f"{quarter.group(1)}Q{quarter.group(2)}", freq="Q").start_time
        numeric = float(value)
        # Excel serial dates used by the official workbook.
        if 20_000 <= numeric <= 80_000:
            return pd.Timestamp("1899-12-30") + pd.to_timedelta(numeric, unit="D")
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed.normalize() if not pd.isna(parsed) else None


def _flatten_column(column: Any) -> str:
    if isinstance(column, tuple):
        return " ".join(str(part) for part in column if str(part).lower() != "nan").strip()
    return str(column)


def _find_column(frame: pd.DataFrame, *, date: bool = False) -> Optional[Any]:
    for column in frame.columns:
        name = _flatten_column(column).strip().lower()
        if date and (name == "date" or name.startswith("date ") or name.endswith(" date") or " date " in name):
            return column
        if not date and (
            name in {"rstar", "r-star", "natural rate", "natural_rate"}
            or ("natural rate" in name and "us" in name)
            or ("r*" in name and "us" in name)
        ):
            return column
    return None


def parse_hlw_frame(
    frame: pd.DataFrame,
    *,
    publication_date: Any,
    source_url: str,
    unit: str = "percent",
) -> list[dict[str, Any]]:
    """Extract US natural-rate rows from an official or fixture workbook frame."""

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("HLW workbook contains no rows")
    date_column = _find_column(frame, date=True)
    value_column = _find_column(frame)
    if date_column is None or value_column is None:
        raise ValueError("HLW workbook is missing Date or US natural-rate columns")
    publication = _timestamp(publication_date)
    if publication is None:
        raise ValueError("HLW publication date is invalid")

    records: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        observation_date = _timestamp(row.get(date_column))
        try:
            value = float(row.get(value_column))
        except (TypeError, ValueError):
            continue
        if observation_date is None or not pd.notna(value) or not pd.api.types.is_number(value):
            continue
        records.append(
            {
                "date": observation_date,
                "value": value,
                "publication_date": publication,
                "vintage_date": publication,
                "source_url": source_url,
                "unit": unit,
                "parsing_status": "OK",
            }
        )
    if not records:
        raise ValueError("HLW workbook contains no valid US natural-rate rows")
    return records


class HolstonLaubachWilliamsProvider:
    """Fetch the official workbook while allowing deterministic fixture injection."""

    def __init__(
        self,
        *,
        source: Optional[Mapping[str, Any]] = None,
        fetch_bytes: Optional[Callable[[str], bytes]] = None,
        read_excel: Optional[Callable[..., pd.DataFrame]] = None,
        publication_date: Any = None,
        timeout: int = 20,
    ):
        self.source = dict(source or HLW_RSTAR_SOURCE)
        self.fetch_bytes = fetch_bytes or self._fetch_bytes
        self.read_excel = read_excel or pd.read_excel
        self.publication_date = publication_date
        self.timeout = timeout

    def _fetch_bytes(self, url: str) -> bytes:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.content

    def get_records(self, as_of: Any = None) -> list[dict[str, Any]]:
        source_url = str(self.source["url"])
        content = self.fetch_bytes(source_url)
        publication_date = self.publication_date or datetime.now().date().isoformat()
        frame = self.read_excel(
            io.BytesIO(content),
            sheet_name=self.source.get("sheet_name", "HLW Estimates"),
            # The official workbook uses two header rows: the first labels
            # the grouped measure ("Natural Rate (r*)") and the second labels
            # the country ("US").  Reading both preserves enough provenance
            # for the parser to select the US r-star column rather than an
            # adjacent trend-growth or output-gap column.
            header=[4, 5],
        )
        records = parse_hlw_frame(
            frame,
            publication_date=publication_date,
            source_url=source_url,
            unit=str(self.source.get("unit", "percent")),
        )
        if as_of is None:
            return records
        analysis_date = _timestamp(as_of)
        if analysis_date is None:
            return []
        return [record for record in records if record["publication_date"] <= analysis_date]


__all__ = [
    "HolstonLaubachWilliamsProvider",
    "parse_hlw_frame",
]
