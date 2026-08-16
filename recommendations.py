"""Sector evidence construction for research-review assessments."""

from math import isfinite
from typing import Any, Dict, List, Optional

from evidence import EvidenceFactor, aggregate_evidence


SECTOR_LIST = [
    {"name": "Technology (XLK)", "etf": "XLK"},
    {"name": "Financials (XLF)", "etf": "XLF"},
    {"name": "Healthcare (XLV)", "etf": "XLV"},
    {"name": "Energy (XLE)", "etf": "XLE"},
    {"name": "Industrials (XLI)", "etf": "XLI"},
    {"name": "Consumer Discretionary (XLY)", "etf": "XLY"},
    {"name": "Consumer Staples (XLP)", "etf": "XLP"},
    {"name": "AI Compute & Accelerators", "etf": "NVDA/AMD/TSM"},
    {"name": "High-Bandwidth Memory (HBM)", "etf": "MU/WDC"},
    {"name": "Physical AI & Robotics", "etf": "TSLA/TER/SYM"},
    {"name": "Downstream Power & Grid", "etf": "CEG/VST/ETN"},
]


METHODOLOGY = (
    "Research-only sector evidence aggregation. Independent macro, liquidity, credit, "
    "valuation, real-yield, housing, and data-quality factors determine a review posture; "
    "missing or stale evidence widens uncertainty."
)


class SectorEvidenceEngine:
    """Build independent, visible evidence factors for each tracked sector group."""

    _SITUATION_BY_STATES = {
        ("ACCOMMODATIVE", "ABUNDANT"): 1,
        ("ACCOMMODATIVE", "SCARCE"): 2,
        ("RESTRICTIVE", "SCARCE"): 3,
        ("RESTRICTIVE", "ABUNDANT"): 4,
    }

    @staticmethod
    def _state(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        return value.strip().upper() or None

    @classmethod
    def _resolve_regime_inputs(
        cls,
        summary: Dict[str, Any],
        macro_situation: Dict[str, Any],
        macro_regime: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Make structured regime state and quadrant metadata authoritative."""
        summary = dict(summary or {})
        regime = macro_regime if isinstance(macro_regime, dict) else {}
        policy = regime.get("policy")
        policy = policy if isinstance(policy, dict) else {}
        liquidity = regime.get("liquidity")
        liquidity = liquidity if isinstance(liquidity, dict) else {}

        # A supplied structured state is authoritative, including when its
        # value conflicts with a legacy snapshot field. An explicitly invalid
        # structured state must not silently fall back to that legacy field.
        if "state" in policy:
            summary["policy_state"] = cls._state(policy.get("state"))
        if "state" in liquidity:
            summary["liquidity_state"] = cls._state(liquidity.get("state"))

        policy_state = summary.get("policy_state")
        liquidity_state = summary.get("liquidity_state")
        expected_situation_id = cls._SITUATION_BY_STATES.get(
            (cls._state(policy_state), cls._state(liquidity_state))
        )

        structured_quadrant = regime.get("quadrant")
        if isinstance(structured_quadrant, dict) and structured_quadrant:
            quadrant = dict(structured_quadrant)
        else:
            quadrant = dict(macro_situation or {})

        if expected_situation_id is not None:
            candidate_id = quadrant.get("situation_id")
            try:
                candidate_id = int(candidate_id) if candidate_id is not None else None
            except (TypeError, ValueError):
                candidate_id = None
            if candidate_id is None:
                # Derive the identifier when older matrix metadata omitted it;
                # the axis pair still comes solely from structured state.
                quadrant["situation_id"] = expected_situation_id
            elif candidate_id != expected_situation_id:
                quadrant = {
                    "quality": "INDETERMINATE_CONFLICT",
                    "situation_id": 0,
                    "favored_sectors": [],
                    "favored_company_types": [],
                    "disfavored_sectors": [],
                }
        elif "state" in policy or "state" in liquidity:
            # Do not let a stale/separate quadrant provide sector metadata when
            # the structured axis pair cannot form one of the four quadrants.
            quadrant = {
                "quality": "INSUFFICIENT_DATA",
                "situation_id": 0,
                "favored_sectors": [],
                "favored_company_types": [],
                "disfavored_sectors": [],
            }

        return summary, quadrant

    def generate_assessments(
        self,
        summary: Dict[str, Any],
        credit: Dict[str, Any],
        valuations: List[Dict[str, Any]],
        ai_ecosystem: List[Dict[str, Any]],
        news_events: List[Dict[str, Any]],
        macro_situation: Dict[str, Any],
        macro_regime: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return deterministic sector assessments from the supplied evidence inputs."""

        summary = dict(summary or {})
        credit = credit or {}
        valuations = valuations or []
        ai_ecosystem = ai_ecosystem or []
        macro_regime = macro_regime or {}
        summary, macro_situation = self._resolve_regime_inputs(
            summary, macro_situation, macro_regime
        )
        _ = news_events  # News remains uninterpreted context, not directional evidence.

        valuations_by_sector = {
            item["sector"]: item for item in valuations if item.get("sector")
        }
        ai_by_group = {item["group"]: item for item in ai_ecosystem if item.get("group")}
        as_of_date = summary.get("date") or macro_situation.get("as_of_date")

        assessments = []
        for sector in SECTOR_LIST:
            sector_group = sector["name"]
            valuation = valuations_by_sector.get(sector_group) or self._matching_ai_valuation(
                sector_group, ai_by_group
            )
            factors = self._build_factors(
                sector_group=sector_group,
                summary=summary,
                credit=credit,
                valuation=valuation,
                macro_situation=macro_situation,
                as_of_date=as_of_date,
            )
            assessment = aggregate_evidence(factors, expected_weight=7)
            assessment.update(
                {
                    "sector_group": sector_group,
                    "instrument": sector["etf"],
                    "benchmark": "SPY",
                    "methodology": METHODOLOGY,
                    "as_of_date": as_of_date,
                }
            )
            assessments.append(assessment)

        return assessments

    def generate_recommendations(
        self,
        summary: Dict[str, Any],
        credit: Dict[str, Any],
        valuations: List[Dict[str, Any]],
        ai_ecosystem: List[Dict[str, Any]],
        news_events: List[Dict[str, Any]],
        macro_situation: Dict[str, Any],
        macro_regime: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return evidence-shaped sector recommendations from structured regime data.

        The former recommendation engine exposed trade actions.  The current
        evidence contract intentionally exposes factor contributions and
        review postures instead.  This compatibility entry point keeps callers
        that request recommendations on the structured regime boundary while
        preserving that non-directive output contract.
        """

        regime = macro_regime or {}
        quadrant = macro_situation or regime.get("quadrant") or {}
        return self.generate_assessments(
            summary,
            credit,
            valuations,
            ai_ecosystem,
            news_events,
            quadrant,
            macro_regime=regime,
        )

    def _build_factors(
        self,
        sector_group: str,
        summary: Dict[str, Any],
        credit: Dict[str, Any],
        valuation: Optional[Dict[str, Any]],
        macro_situation: Dict[str, Any],
        as_of_date: Optional[str],
    ) -> List[EvidenceFactor]:
        return [
            self._macro_quadrant_factor(sector_group, macro_situation, as_of_date),
            self._liquidity_factor(summary, as_of_date),
            self._credit_factor(sector_group, credit, as_of_date),
            self._valuation_factor(valuation, as_of_date),
            self._real_yield_factor(sector_group, summary, as_of_date),
            self._housing_factor(sector_group, summary, as_of_date),
            self._data_quality_factor(macro_situation, as_of_date),
        ]

    @staticmethod
    def _factor(
        factor_id: str,
        category: str,
        contribution: float,
        observed_value: Any,
        unit: str,
        observed_at: Optional[str],
        source: str,
        explanation: str,
        quality: str = "current",
        missing_reason: Optional[str] = None,
    ) -> EvidenceFactor:
        direction = (
            "positive"
            if contribution > 0
            else "negative"
            if contribution < 0
            else "neutral"
        )
        return EvidenceFactor(
            factor_id=factor_id,
            category=category,
            direction=direction,
            contribution=contribution,
            weight=1.0,
            observed_value=observed_value,
            unit=unit,
            observed_at=observed_at,
            source=source,
            quality=quality,
            explanation=explanation,
            missing_reason=missing_reason,
        )

    def _macro_quadrant_factor(
        self,
        sector_group: str,
        macro_situation: Dict[str, Any],
        as_of_date: Optional[str],
    ) -> EvidenceFactor:
        quality = macro_situation.get("quality")
        situation_id = macro_situation.get("situation_id")
        if str(quality or "").upper() not in {"OK", "PARTIAL"} or situation_id not in {1, 2, 3, 4}:
            return self._factor(
                "macro_quadrant",
                "macro",
                0,
                situation_id if situation_id is not None else quality,
                "quality",
                as_of_date,
                "macro_matrix",
                "Macro quadrant is unavailable.",
                quality="missing",
                missing_reason="Macro quadrant is unavailable.",
            )

        favored = set(macro_situation.get("favored_sectors", []))
        disfavored = set(macro_situation.get("disfavored_sectors", []))
        contribution = 2 if sector_group in favored else -2 if sector_group in disfavored else 0
        return self._factor(
            "macro_quadrant",
            "macro",
            contribution,
            macro_situation.get("name"),
            "regime",
            as_of_date,
            "macro_matrix",
            "Macro quadrant is favorable, unfavorable, or neutral for this sector group.",
        )

    def _liquidity_factor(
        self, summary: Dict[str, Any], as_of_date: Optional[str]
    ) -> EvidenceFactor:
        state = summary.get("liquidity_state")
        if not isinstance(state, str) or state.upper() not in {
            "ABUNDANT",
            "SCARCE",
            "NEUTRAL",
        }:
            return self._missing_factor(
                "liquidity",
                "liquidity",
                "Liquidity regime is unavailable.",
                as_of_date,
                "summary",
            )
        normalized = state.upper()
        contribution = 1 if normalized == "ABUNDANT" else -1 if normalized == "SCARCE" else 0
        return self._factor(
            "liquidity",
            "liquidity",
            contribution,
            normalized,
            "level_state",
            as_of_date,
            "summary",
            "Reserve-liquidity level is evaluated against its historical distribution.",
        )

    def _credit_factor(
        self, sector_group: str, credit: Dict[str, Any], as_of_date: Optional[str]
    ) -> EvidenceFactor:
        high_yield_oas = self._finite_number(credit.get("high_yield_oas"))
        if high_yield_oas is None:
            return self._missing_factor(
                "credit",
                "credit",
                "High-yield OAS is unavailable.",
                as_of_date,
                "credit",
            )
        defensive_sectors = {"Healthcare (XLV)", "Consumer Staples (XLP)"}
        contribution = 0
        if high_yield_oas > 5:
            contribution = 1 if sector_group in defensive_sectors else -3
        return self._factor(
            "credit",
            "credit",
            contribution,
            high_yield_oas,
            "percent",
            as_of_date,
            "credit",
            "High-yield option-adjusted spread is assessed for credit stress.",
        )

    def _valuation_factor(
        self, valuation: Optional[Dict[str, Any]], as_of_date: Optional[str]
    ) -> EvidenceFactor:
        percentile = self._valuation_percentile(valuation)
        if percentile is None:
            return self._missing_factor(
                "valuation_percentile",
                "valuation",
                "Valuation percentile is unavailable.",
                as_of_date,
                "sector_valuations",
            )
        contribution = 2 if percentile <= 25 else -2 if percentile >= 75 else 0
        return self._factor(
            "valuation_percentile",
            "valuation",
            contribution,
            percentile,
            "percentile",
            as_of_date,
            "sector_valuations",
            "Historical valuation percentile is discount, rich, or typical.",
        )

    def _real_yield_factor(
        self, sector_group: str, summary: Dict[str, Any], as_of_date: Optional[str]
    ) -> EvidenceFactor:
        real_yield = self._real_yield(summary)
        if real_yield is None:
            return self._missing_factor(
                "real_yield",
                "rates",
                "Real yield is unavailable.",
                as_of_date,
                "summary",
            )
        long_duration = any(
            label in sector_group for label in ("Technology", "AI", "Robotics")
        )
        contribution = -1 if long_duration and real_yield > 2 else 0
        return self._factor(
            "real_yield",
            "rates",
            contribution,
            real_yield,
            "percent",
            as_of_date,
            "summary",
            "Restrictive real yields are a headwind for long-duration sector groups.",
        )

    def _housing_factor(
        self, sector_group: str, summary: Dict[str, Any], as_of_date: Optional[str]
    ) -> EvidenceFactor:
        housing_yoy = self._finite_number(summary.get("housing_yoy"))
        if housing_yoy is None:
            return self._missing_factor(
                "housing",
                "macro",
                "Housing YoY is unavailable.",
                as_of_date,
                "summary",
            )
        cyclical = sector_group in {"Consumer Discretionary (XLY)", "Industrials (XLI)"}
        contribution = -2 if cyclical and housing_yoy < -10 else 0
        return self._factor(
            "housing",
            "macro",
            contribution,
            housing_yoy,
            "percent_yoy",
            as_of_date,
            "summary",
            "Housing growth is a cyclical-sector headwind only during sharp contraction.",
        )

    def _data_quality_factor(
        self, macro_situation: Dict[str, Any], as_of_date: Optional[str]
    ) -> EvidenceFactor:
        quality = macro_situation.get("quality")
        if quality != "OK":
            reason = (
                "Macro input quality is unavailable."
                if quality is None
                else "Macro input quality is insufficient."
            )
            return self._missing_factor(
                "data_quality", "data_quality", reason, as_of_date, "macro_matrix"
            )
        return self._factor(
            "data_quality",
            "data_quality",
            0,
            quality,
            "quality",
            as_of_date,
            "macro_matrix",
            "Macro input quality is sufficient for the available evidence.",
        )

    def _missing_factor(
        self,
        factor_id: str,
        category: str,
        reason: str,
        as_of_date: Optional[str],
        source: str,
    ) -> EvidenceFactor:
        return self._factor(
            factor_id,
            category,
            0,
            None,
            "unknown",
            as_of_date,
            source,
            reason,
            quality="missing",
            missing_reason=reason,
        )

    @staticmethod
    def _matching_ai_valuation(
        sector_group: str, ai_by_group: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        for group, valuation in ai_by_group.items():
            if sector_group.lower() in group.lower():
                return valuation
        return None

    @staticmethod
    def _valuation_percentile(valuation: Optional[Dict[str, Any]]) -> Optional[float]:
        if not valuation:
            return None
        history = valuation.get("history") or {}
        return SectorEvidenceEngine._finite_number(
            valuation.get("percentile", history.get("percentile"))
        )

    @staticmethod
    def _real_yield(summary: Dict[str, Any]) -> Optional[float]:
        explicit = SectorEvidenceEngine._finite_number(summary.get("real_yield_10y"))
        if explicit is not None:
            return explicit
        treasury_10y = SectorEvidenceEngine._finite_number(summary.get("treasury_10y"))
        breakeven_10y = SectorEvidenceEngine._finite_number(summary.get("breakeven_10y"))
        if treasury_10y is None or breakeven_10y is None:
            return None
        return treasury_10y - breakeven_10y

    @staticmethod
    def _finite_number(value: Any) -> Optional[float]:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None


# Keep the historical class import usable while routing all behavior through
# the evidence-oriented implementation above.
SectorRecommendationEngine = SectorEvidenceEngine
