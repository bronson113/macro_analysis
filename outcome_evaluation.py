"""Point-in-time evaluation of prospectively recorded research postures.

This module deliberately accepts normalized, caller-supplied price histories.  Keeping
data retrieval outside the evaluator makes its no-look-ahead rules testable and keeps
the calculations deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from statistics import median
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


MINIMUM_SAMPLE_SIZE = 30
MINIMUM_ELAPSED_DAYS = 365
FACTOR_SNAPSHOT_FIELDS = (
    "positive_factors",
    "negative_factors",
    "neutral_factors",
    "missing_evidence",
    "factors",
    "methodology",
    "as_of_date",
)


@dataclass(frozen=True)
class SignalRecord:
    """One prospective posture captured when the underlying evidence was available."""

    signal_date: str
    sector_group: str
    instrument: str
    benchmark: str
    posture: str
    score: float
    score_range: Tuple[float, ...]
    coverage_pct: Optional[float]
    factor_snapshot: Dict[str, Any]

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "SignalRecord":
        uncertainty = record.get("score_range", record.get("uncertainty", ()))
        if uncertainty is None:
            uncertainty = ()
        if not isinstance(uncertainty, (list, tuple)):
            raise ValueError("score_range must be a list or tuple")

        factor_snapshot = record.get("factor_snapshot")
        if not isinstance(factor_snapshot, Mapping):
            factor_snapshot = {
                field: record.get(field)
                for field in FACTOR_SNAPSHOT_FIELDS
                if field in record
            }

        return cls(
            signal_date=_date_string(record.get("signal_date") or record.get("as_of_date")),
            sector_group=str(record.get("sector_group") or ""),
            instrument=str(record.get("instrument") or ""),
            benchmark=str(record.get("benchmark") or "SPY"),
            posture=str(record.get("posture") or "NEUTRAL").upper(),
            score=float(record.get("score")),
            score_range=tuple(float(value) for value in uncertainty),
            coverage_pct=_optional_float(record.get("coverage_pct")),
            factor_snapshot=dict(factor_snapshot),
        )

    def to_mapping(self) -> Dict[str, Any]:
        """Return the stable public record used by CSV persistence and evaluation."""
        return {
            "signal_date": self.signal_date,
            "sector_group": self.sector_group,
            "instrument": self.instrument,
            "benchmark": self.benchmark,
            "posture": self.posture,
            "score": self.score,
            "score_range": list(self.score_range),
            "uncertainty": list(self.score_range),
            "coverage_pct": self.coverage_pct,
            "factor_snapshot": self.factor_snapshot,
        }


def evaluate_signals(
    signals: Iterable[Mapping[str, Any] | SignalRecord],
    prices: Mapping[str, Any],
    horizons: Sequence[int] = (21, 63, 126, 252),
    transaction_cost_bps: float = 10,
) -> Dict[str, Any]:
    """Calculate only outcomes whose entry and target prices have matured.

    An entry is the first mutually available instrument/benchmark observation on or
    after the signal date.  Each target is that entry date plus the requested number
    of business days; end prices are the first mutually available observations on or
    after the target.  Consequently no price prior to a decision or its horizon can
    affect an outcome.
    """
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps cannot be negative")

    normalized_prices = _normalize_prices(prices)
    normalized_horizons = tuple(sorted({int(value) for value in horizons if int(value) > 0}))
    cost_pct = float(transaction_cost_bps) / 100.0
    outcomes: List[Dict[str, Any]] = []

    for raw_signal in signals:
        try:
            signal = raw_signal if isinstance(raw_signal, SignalRecord) else SignalRecord.from_mapping(raw_signal)
            signal_date = _parse_date(signal.signal_date)
        except (TypeError, ValueError):
            continue

        asset_prices = _instrument_prices(signal.instrument, normalized_prices)
        benchmark_prices = normalized_prices.get(signal.benchmark)
        if not asset_prices or not benchmark_prices:
            continue

        entry = _shared_first_on_or_after(asset_prices, benchmark_prices, signal_date)
        if entry is None:
            continue
        entry_date, asset_entry, benchmark_entry = entry

        for horizon in normalized_horizons:
            target_date = _trading_day_target(
                asset_prices, benchmark_prices, entry_date, horizon
            )
            if target_date is None:
                continue
            exit_price = _shared_first_on_or_after(asset_prices, benchmark_prices, target_date)
            if exit_price is None:
                continue
            outcome_date, asset_exit, benchmark_exit = exit_price
            asset_return = ((asset_exit / asset_entry) - 1.0) * 100.0
            benchmark_return = ((benchmark_exit / benchmark_entry) - 1.0) * 100.0
            gross_excess = asset_return - benchmark_return
            net_excess = gross_excess - cost_pct
            posture = signal.posture
            hit = (
                net_excess > 0
                if posture == "WATCH"
                else net_excess < 0
                if posture == "AVOID"
                else None
            )

            outcomes.append(
                {
                    "signal_date": signal.signal_date,
                    "entry_date": entry_date.isoformat(),
                    "outcome_date": outcome_date.isoformat(),
                    "horizon_trading_days": horizon,
                    "sector_group": signal.sector_group,
                    "instrument": signal.instrument,
                    "benchmark": signal.benchmark,
                    "posture": posture,
                    "score": _rounded(signal.score),
                    "score_band": int(round(signal.score)),
                    "asset_return_pct": _rounded(asset_return),
                    "benchmark_return_pct": _rounded(benchmark_return),
                    "gross_excess_return_pct": _rounded(gross_excess),
                    "transaction_cost_bps": _rounded(float(transaction_cost_bps)),
                    "transaction_cost_pct": _rounded(cost_pct),
                    "net_excess_return_pct": _rounded(net_excess),
                    "max_drawdown_pct": _rounded(
                        _maximum_drawdown(asset_prices, entry_date, outcome_date)
                    ),
                    "hit": hit,
                }
            )

    outcomes.sort(
        key=lambda row: (
            row["signal_date"],
            row["horizon_trading_days"],
            row["sector_group"],
            row["instrument"],
        )
    )
    summary = _summarize(outcomes)
    summary["by_horizon"] = _group_summaries(outcomes, "horizon_trading_days")

    return {
        "methodology": {
            "minimum_sample_size": MINIMUM_SAMPLE_SIZE,
            "minimum_elapsed_days": MINIMUM_ELAPSED_DAYS,
            "transaction_cost_bps": _rounded(float(transaction_cost_bps)),
            "cost_treatment": "One-way cost subtracted from asset-minus-benchmark excess return.",
            "research_disclosure": "Point-in-time research evaluation only; insufficient samples are not strategy validation.",
        },
        "outcomes": outcomes,
        "summary": summary,
    }


def _group_summaries(
    outcomes: Sequence[Dict[str, Any]], key: str
) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for outcome in outcomes:
        groups.setdefault(str(outcome[key]), []).append(outcome)

    result: Dict[str, Dict[str, Any]] = {}
    for group_key in sorted(groups, key=lambda value: int(value)):
        rows = groups[group_key]
        group_summary = _summarize(rows)
        group_summary["by_posture"] = _posture_summaries(rows)
        group_summary["by_score_band"] = _nested_summaries(rows, "score_band")
        result[group_key] = group_summary
    return result


def _posture_summaries(
    outcomes: Sequence[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for outcome in outcomes:
        groups.setdefault(str(outcome["posture"]), []).append(outcome)
    summaries: Dict[str, Dict[str, Any]] = {}
    for posture in sorted(groups):
        rows = groups[posture]
        summary = _summarize(rows)
        summary["by_score_band"] = _nested_summaries(rows, "score_band")
        summaries[posture] = summary
    return summaries


def _nested_summaries(
    outcomes: Sequence[Dict[str, Any]], key: str
) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for outcome in outcomes:
        groups.setdefault(str(outcome[key]), []).append(outcome)
    return {group: _summarize(groups[group]) for group in sorted(groups)}


def _summarize(outcomes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    sample_size = len(outcomes)
    directed = [row for row in outcomes if row["hit"] is not None]
    excess_returns = [row["net_excess_return_pct"] for row in outcomes]
    drawdowns = [row["max_drawdown_pct"] for row in outcomes]

    if outcomes:
        first_signal = min(_parse_date(row["signal_date"]) for row in outcomes)
        last_outcome = max(_parse_date(row["outcome_date"]) for row in outcomes)
        elapsed_days = (last_outcome - first_signal).days
    else:
        elapsed_days = 0

    return {
        "status": (
            "EVALUATION_ONLY"
            if sample_size >= MINIMUM_SAMPLE_SIZE and elapsed_days >= MINIMUM_ELAPSED_DAYS
            else "INSUFFICIENT_SAMPLE"
        ),
        "sample_size": sample_size,
        "directed_sample_size": len(directed),
        "elapsed_days": elapsed_days,
        "hit_rate_pct": _rounded(100.0 * sum(bool(row["hit"]) for row in directed) / len(directed))
        if directed
        else None,
        "mean_net_excess_return_pct": _rounded(sum(excess_returns) / sample_size)
        if sample_size
        else None,
        "median_net_excess_return_pct": _rounded(median(excess_returns)) if sample_size else None,
        "max_drawdown_pct": _rounded(min(drawdowns)) if drawdowns else None,
    }


def _normalize_prices(prices: Mapping[str, Any]) -> Dict[str, List[Tuple[date, float]]]:
    if not isinstance(prices, Mapping):
        return {}
    return {
        str(ticker): points
        for ticker, values in prices.items()
        if (points := _normalize_price_history(values))
    }


def _normalize_price_history(values: Any) -> List[Tuple[date, float]]:
    """Normalize common list, Series, and DataFrame price representations."""
    if values is None:
        return []
    if hasattr(values, "columns"):
        columns = list(values.columns)
        for preferred in ("Close", "Adj Close", "close", "adj_close"):
            if preferred in columns:
                return _normalize_price_history(values[preferred])
        return []
    if hasattr(values, "items") and not isinstance(values, Mapping):
        values = list(values.items())
    elif isinstance(values, Mapping):
        values = list(values.items())

    normalized: Dict[date, float] = {}
    try:
        iterator = iter(values)
    except TypeError:
        return []
    for value in iterator:
        if isinstance(value, Mapping):
            when = value.get("date", value.get("Date"))
            price = value.get("close", value.get("Close", value.get("price")))
        else:
            try:
                when, price = value[0], value[1]
            except (TypeError, IndexError):
                continue
        try:
            parsed_date = _parse_date(when)
            parsed_price = float(price)
        except (TypeError, ValueError):
            continue
        if isfinite(parsed_price) and parsed_price > 0:
            normalized[parsed_date] = parsed_price
    return sorted(normalized.items())


def _instrument_prices(
    instrument: str, prices: Mapping[str, List[Tuple[date, float]]]
) -> List[Tuple[date, float]]:
    direct = prices.get(instrument)
    if direct:
        return direct

    components = [part.strip() for part in instrument.split("/") if part.strip()]
    if len(components) < 2 or any(not prices.get(component) for component in components):
        return []
    component_maps = [dict(prices[component]) for component in components]
    common_dates = set(component_maps[0])
    for values in component_maps[1:]:
        common_dates.intersection_update(values)
    if not common_dates:
        return []
    first_date = min(common_dates)
    bases = [values[first_date] for values in component_maps]
    return [
        (
            current_date,
            100.0
            * sum(values[current_date] / base for values, base in zip(component_maps, bases))
            / len(component_maps),
        )
        for current_date in sorted(common_dates)
    ]


def _shared_first_on_or_after(
    asset_prices: Sequence[Tuple[date, float]],
    benchmark_prices: Sequence[Tuple[date, float]],
    target: date,
) -> Optional[Tuple[date, float, float]]:
    benchmark_by_date = dict(benchmark_prices)
    for observed_at, asset_price in asset_prices:
        if observed_at < target:
            continue
        benchmark_price = benchmark_by_date.get(observed_at)
        if benchmark_price is not None:
            return observed_at, asset_price, benchmark_price
    return None


def _maximum_drawdown(
    prices: Sequence[Tuple[date, float]], start: date, end: date
) -> float:
    path = [price for when, price in prices if start <= when <= end]
    if not path:
        return 0.0
    peak = path[0]
    worst_drawdown = 0.0
    for price in path:
        peak = max(peak, price)
        worst_drawdown = min(worst_drawdown, ((price / peak) - 1.0) * 100.0)
    return worst_drawdown


def _trading_day_target(
    asset_prices: Sequence[Tuple[date, float]],
    benchmark_prices: Sequence[Tuple[date, float]],
    entry_date: date,
    horizon: int,
) -> Optional[date]:
    """Return the horizon-th observed common market session after entry.

    Price histories encode the actual exchange sessions, including holidays.  Counting
    their shared observation dates avoids treating a market holiday as a trading day.
    """
    benchmark_dates = {observed_at for observed_at, _ in benchmark_prices}
    common_sessions = [
        observed_at
        for observed_at, _ in asset_prices
        if observed_at >= entry_date and observed_at in benchmark_dates
    ]
    return common_sessions[horizon] if len(common_sessions) > horizon else None


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        raise ValueError("a signal date is required")
    return date.fromisoformat(str(value)[:10])


def _date_string(value: Any) -> str:
    return _parse_date(value).isoformat()


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _rounded(value: float) -> float:
    return round(value, 4)
