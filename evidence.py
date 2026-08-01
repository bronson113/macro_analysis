"""Immutable evidence records and deterministic research-posture aggregation."""

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Optional


VALID_DIRECTIONS = {"positive", "negative", "neutral"}
VALID_QUALITY = {"current", "stale", "missing"}


@dataclass(frozen=True)
class EvidenceFactor:
    """A single bounded, source-attributed input to a research assessment."""

    factor_id: str
    category: str
    direction: str
    contribution: float
    weight: float
    observed_value: Any
    unit: str
    observed_at: Optional[str]
    source: str
    quality: str
    explanation: str
    missing_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.direction not in VALID_DIRECTIONS:
            raise ValueError(f"invalid direction: {self.direction}")
        if self.quality not in VALID_QUALITY:
            raise ValueError(f"invalid quality: {self.quality}")
        if not -5 <= self.contribution <= 5:
            raise ValueError("contribution must be between -5 and 5")
        if self.weight <= 0:
            raise ValueError("weight must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def aggregate_evidence(
    factors: Iterable[EvidenceFactor], expected_weight: float
) -> dict[str, Any]:
    """Aggregate visible evidence without allowing later rules to overwrite it."""

    factors = list(factors)
    serialized = [item.to_dict() for item in factors]
    usable = [item for item in factors if item.quality == "current"]
    stale = [item for item in factors if item.quality == "stale"]

    available_weight = sum(item.weight for item in usable)
    stale_weight = sum(item.weight for item in stale)
    denominator = max(float(expected_weight), 1.0)
    coverage = min(1.0, available_weight / denominator)

    score = max(
        -10.0,
        min(10.0, sum(item.contribution * item.weight for item in usable)),
    )
    positive_weight = sum(item.weight for item in usable if item.contribution > 0)
    negative_weight = sum(item.weight for item in usable if item.contribution < 0)
    disagreement = min(positive_weight, negative_weight) / max(
        positive_weight, negative_weight, 1.0
    )
    half_width = min(
        5.0,
        (1.0 - coverage) * 4.0
        + disagreement * 2.0
        + stale_weight / denominator * 2.0,
    )
    low = score - half_width
    high = score + half_width
    if low < -10.0:
        high = min(10.0, high + (-10.0 - low))
        low = -10.0
    elif high > 10.0:
        low = max(-10.0, low - (high - 10.0))
        high = 10.0
    posture = "WATCH" if low >= 2.0 else "AVOID" if high <= -2.0 else "NEUTRAL"

    return {
        "score": round(score, 2),
        "score_range": [round(low, 2), round(high, 2)],
        "coverage_pct": round(coverage * 100.0, 1),
        "posture": posture,
        "positive_factors": [
            item
            for item in serialized
            if item["quality"] == "current" and item["contribution"] > 0
        ],
        "negative_factors": [
            item
            for item in serialized
            if item["quality"] == "current" and item["contribution"] < 0
        ],
        "neutral_factors": [
            item
            for item in serialized
            if item["quality"] == "current" and item["contribution"] == 0
        ],
        "missing_evidence": [
            item for item in serialized if item["quality"] != "current"
        ],
        "factors": serialized,
    }
