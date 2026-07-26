"""Helpers for stock valuation multiples relative to their peer group."""

import re
from typing import Optional


def relative_multiple_key(group: str, ticker: str, multiple: str) -> str:
    group_slug = re.sub(r"[^a-z0-9]+", "_", group.lower()).strip("_")
    group_slug = group_slug.split("_")[0] if group_slug else "group"
    return f"stock_rel_{multiple}_{group_slug}_{ticker.lower()}"


def safe_ratio(numerator, denominator) -> Optional[float]:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    if numerator <= 0:
        return None
    return numerator / denominator
