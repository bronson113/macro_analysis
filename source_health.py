"""Normalized, machine-readable health records for external data sources."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional


SOURCE_HEALTH_COLUMNS = [
    "source",
    "fetch_key",
    "observation_time",
    "fetch_time",
    "status",
    "is_stale",
    "record_count",
    "error_category",
    "message",
]


def classify_source_error(message: Optional[str]) -> str:
    """Map provider-specific errors to durable categories for consumers and alerts."""
    text = (message or "").lower()

    if any(token in text for token in (
        "timeout", "timed out", "connection", "connect", "dns", "name resolution",
        "network is unreachable", "temporarily unavailable",
    )):
        return "network"
    if any(token in text for token in ("range", "outside", "schema", "validation")):
        return "validation"
    if any(token in text for token in (
        "missing", "empty", "payload", "regex", "xml", "json", "csv", "html",
        "decode", "parse",
    )):
        return "parse"
    return "unknown"


@dataclass(frozen=True)
class SourceHealth:
    """The persisted outcome of one source fetch for one logical data key."""

    source: str
    fetch_key: str
    observation_time: Optional[str]
    fetch_time: str
    status: str
    is_stale: bool
    record_count: int
    error_category: str
    message: str

    def to_mapping(self) -> Dict[str, Any]:
        """Return CSV-safe primitives using the canonical public field names."""
        values = asdict(self)
        values["observation_time"] = values["observation_time"] or ""
        values["is_stale"] = bool(values["is_stale"])
        values["record_count"] = int(values["record_count"])
        values["error_category"] = values["error_category"] or ""
        values["message"] = values["message"] or ""
        return values

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "SourceHealth":
        """Restore a record from pandas/CSV values without leaking NaN sentinels."""
        def clean(value: Any) -> Optional[str]:
            if value is None:
                return None
            text = str(value)
            return None if text.lower() == "nan" else text

        stale = values.get("is_stale", False)
        if isinstance(stale, str):
            stale = stale.strip().lower() in {"1", "true", "yes"}
        try:
            record_count = int(float(values.get("record_count", 0) or 0))
        except (TypeError, ValueError):
            record_count = 0
        return cls(
            source=clean(values.get("source")) or "",
            fetch_key=clean(values.get("fetch_key")) or "",
            observation_time=clean(values.get("observation_time")),
            fetch_time=clean(values.get("fetch_time")) or "",
            status=clean(values.get("status")) or "",
            is_stale=bool(stale),
            record_count=record_count,
            error_category=clean(values.get("error_category")) or "",
            message=clean(values.get("message")) or "",
        )
