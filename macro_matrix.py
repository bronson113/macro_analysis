"""Combine current policy and reserve-liquidity states into macro quadrants.

The matrix is deliberately a small combination layer. Policy and liquidity
levels are calculated by :mod:`macro_regime`; momentum, inflation, labor, and
other diagnostics are interpretation context only and cannot select a
quadrant.
"""

from typing import Any, Dict, Mapping, Optional


POLICY_STATES = {"ACCOMMODATIVE", "RESTRICTIVE", "NEUTRAL"}
LIQUIDITY_STATES = {"ABUNDANT", "SCARCE", "NEUTRAL"}
WITHHOLDING_QUALITIES = {
    "INSUFFICIENT_DATA",
    "INDETERMINATE_CONFLICT",
    "UNAVAILABLE",
    "STALE",
}


def _state(value: Any, allowed: set[str]) -> Optional[str]:
    """Return an accepted current-level state, or ``None`` for a legacy label."""

    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    return candidate if candidate in allowed else None


def _context_value(context: Mapping[str, Any], key: str, default: Any = None) -> Any:
    value = context.get(key, default)
    if value is not None:
        return value
    # Measurements may be passed directly by MacroAnalyzer. This is display
    # context only; it is never used for axis selection.
    for measurement_key in ("policy", "liquidity", "macro"):
        measurement = context.get(measurement_key)
        if isinstance(measurement, Mapping) and key in measurement:
            return measurement[key]
    return default


class MacroMatrixEngine:
    """Map current policy/liquidity levels to one of four research quadrants."""

    def classify_situation(
        self,
        policy_state: Optional[str],
        liquidity_state: Optional[str],
        *,
        quality: str = "OK",
        context: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return a level-based quadrant and contextual interpretation.

        Only the two explicit state arguments participate in the mapping. The
        optional context can enrich descriptions and structured output, but
        changing momentum, CPI, labor, or consensus cannot change the
        ``situation_id``.
        """

        context = context if isinstance(context, Mapping) else {}
        normalized_policy = _state(policy_state, POLICY_STATES)
        normalized_liquidity = _state(liquidity_state, LIQUIDITY_STATES)
        normalized_quality = str(quality or "OK").upper()
        reasons = []
        conflicts = []

        if normalized_policy is None:
            reasons.append("Current policy state is unavailable or unsupported")
        elif normalized_policy == "NEUTRAL":
            reasons.append("Policy is neutral inside the neutral band")

        if normalized_liquidity is None:
            reasons.append("Current liquidity state is unavailable or unsupported")
        elif normalized_liquidity == "NEUTRAL":
            reasons.append("Liquidity is neutral between historical thresholds")

        if normalized_quality == "INDETERMINATE_CONFLICT":
            conflicts.append("Core regime inputs are materially contradictory")
        if normalized_quality in WITHHOLDING_QUALITIES:
            reasons.append(
                f"Regime quality {normalized_quality} does not support an actionable quadrant"
            )

        situation_id = 0
        if (
            normalized_quality not in WITHHOLDING_QUALITIES
            and normalized_policy in {"ACCOMMODATIVE", "RESTRICTIVE"}
            and normalized_liquidity in {"ABUNDANT", "SCARCE"}
        ):
            situation_id = {
                ("ACCOMMODATIVE", "ABUNDANT"): 1,
                ("ACCOMMODATIVE", "SCARCE"): 2,
                ("RESTRICTIVE", "SCARCE"): 3,
                ("RESTRICTIVE", "ABUNDANT"): 4,
            }[(normalized_policy, normalized_liquidity)]

        effective_quality = normalized_quality
        if situation_id == 0 and normalized_quality == "OK":
            effective_quality = "INSUFFICIENT_DATA"

        common = {
            "policy_state": normalized_policy,
            "liquidity_state": normalized_liquidity,
            "policy_measurement": context.get("policy") or {},
            "liquidity_measurement": context.get("liquidity") or {},
            "current_state": {
                "policy": normalized_policy,
                "liquidity": normalized_liquidity,
                "policy_level": normalized_policy,
                "liquidity_level": normalized_liquidity,
                "policy_state": normalized_policy,
                "liquidity_state": normalized_liquidity,
                "situation_id": situation_id,
            },
            "momentum": context.get("momentum") or {
                "policy_30d": _context_value(context, "momentum_30d"),
                "policy_90d": _context_value(context, "momentum_90d"),
            },
            "consensus": context.get("consensus") or {},
            "data_quality": context.get("data_quality") or {"quality": effective_quality},
            "momentum_30d": (context.get("momentum") or {}).get("liquidity_30d"),
            "momentum_90d": (context.get("momentum") or {}).get("liquidity_90d"),
            "missing_inputs": list(context.get("missing_inputs") or reasons),
            "conflicts": list(context.get("conflicts") or conflicts),
            "quality": effective_quality,
        }

        if situation_id == 0:
            return {
                **common,
                "situation_id": 0,
                "name": "NO ACTIONABLE MACRO QUADRANT",
                "rates_label": (
                    "Interest Rates: Neutral / unavailable"
                    if normalized_policy in {None, "NEUTRAL"}
                    else f"Interest Rates: {normalized_policy.title()}"
                ),
                "bs_label": (
                    "Reserve Liquidity: Neutral / unavailable"
                    if normalized_liquidity in {None, "NEUTRAL"}
                    else f"Reserve Liquidity: {normalized_liquidity.title()}"
                ),
                "description": (
                    "The macro framework is withheld because at least one current "
                    "policy or reserve-liquidity level is neutral, missing, stale, "
                    "or materially conflicted."
                ),
                "favored_sectors": [],
                "favored_company_types": [],
                "disfavored_sectors": [],
            }

        cpi_yoy = _context_value(context, "cpi_yoy")
        sahm_rule_triggered = bool(_context_value(context, "sahm_rule_triggered", False))
        spread_10y_2y = _context_value(context, "spread_10y_2y")
        m2_yoy = _context_value(context, "m2_yoy")

        if situation_id == 1:
            name = "SITUATION 1: ACCOMMODATIVE POLICY + ABUNDANT RESERVE LIQUIDITY"
            rates_label = "Interest Rates: Accommodative (current level)"
            bs_label = "Reserve Liquidity: Abundant (current level)"
            description = (
                "Risk-liquidity tailwind: policy is accommodative and reserve "
                "liquidity remains historically abundant."
            )
            if sahm_rule_triggered:
                description += " SAHM rule triggered; monitor labor deterioration."
            favored_sectors = [
                "Technology (XLK)",
                "AI Compute & Accelerators",
                "High-Bandwidth Memory (HBM)",
                "Physical AI & Robotics",
                "Downstream Power & Grid",
                "Consumer Discretionary (XLY)",
            ]
            favored_company_types = ["High-growth tech", "Capex super-cycle (AI, Grid)"]
            disfavored_sectors = ["Cash", "Consumer Staples (XLP)"]
        elif situation_id == 2:
            name = "SITUATION 2: ACCOMMODATIVE POLICY + SCARCE RESERVE LIQUIDITY"
            rates_label = "Interest Rates: Accommodative (current level)"
            bs_label = "Reserve Liquidity: Scarce (current level)"
            description = (
                "Policy is accommodative while reserve liquidity remains scarce; "
                "easing support is limited by the liquidity backdrop."
            )
            if sahm_rule_triggered:
                description += " SAHM rule triggered; monitor for recession risk."
            try:
                if spread_10y_2y is not None and float(spread_10y_2y) > 0:
                    description += " Yield curve un-inversion is a caution signal."
            except (TypeError, ValueError):
                pass
            favored_sectors = ["Healthcare (XLV)", "Consumer Staples (XLP)"]
            favored_company_types = ["Defensive cash flow", "Low debt"]
            disfavored_sectors = [
                "Technology (XLK)",
                "Consumer Discretionary (XLY)",
                "Industrials (XLI)",
                "AI Compute & Accelerators",
                "Physical AI & Robotics",
            ]
        elif situation_id == 3:
            name = "SITUATION 3: RESTRICTIVE POLICY + SCARCE RESERVE LIQUIDITY"
            rates_label = "Interest Rates: Restrictive (current level)"
            bs_label = "Reserve Liquidity: Scarce (current level)"
            description = (
                "Restrictive policy and scarce reserve liquidity create the "
                "strongest liquidity and valuation headwind."
            )
            favored_sectors = ["Financials (XLF)", "Cash"]
            favored_company_types = ["Net-Interest-Margin beneficiaries", "Zero debt"]
            disfavored_sectors = [
                "Technology (XLK)",
                "AI Compute & Accelerators",
                "Physical AI & Robotics",
                "Consumer Discretionary (XLY)",
            ]
        else:
            name = "SITUATION 4: RESTRICTIVE POLICY + ABUNDANT RESERVE LIQUIDITY"
            rates_label = "Interest Rates: Restrictive (current level)"
            bs_label = "Reserve Liquidity: Abundant (current level)"
            description = (
                "Policy remains restrictive while reserve liquidity is abundant; "
                "the liquidity backdrop offsets some policy restraint."
            )
            try:
                if cpi_yoy is not None and float(cpi_yoy) > 3.0:
                    description += f" Sticky inflation remains visible ({float(cpi_yoy):.1f}% CPI)."
            except (TypeError, ValueError):
                pass
            favored_sectors = ["Energy (XLE)", "Financials (XLF)", "Industrials (XLI)"]
            favored_company_types = ["Real asset owners", "Inflation-indexed revenues"]
            disfavored_sectors = ["Consumer Discretionary (XLY)"]

        try:
            if m2_yoy is not None and float(m2_yoy) < 0:
                description += (
                    f" M2 Money Supply is contracting ({float(m2_yoy):.1f}% YoY), "
                    "signaling deflationary pressure on earnings."
                )
        except (TypeError, ValueError):
            pass

        return {
            **common,
            "situation_id": situation_id,
            "name": name,
            "rates_label": rates_label,
            "bs_label": bs_label,
            "description": description,
            "favored_sectors": favored_sectors,
            "favored_company_types": favored_company_types,
            "disfavored_sectors": disfavored_sectors,
        }
