import unittest
from dataclasses import FrozenInstanceError

from evidence import EvidenceFactor, aggregate_evidence
from recommendations import SectorEvidenceEngine


def factor(factor_id, contribution, quality="current", weight=1.0):
    return EvidenceFactor(
        factor_id=factor_id,
        category="macro",
        direction="positive" if contribution > 0 else "negative" if contribution < 0 else "neutral",
        contribution=contribution,
        weight=weight,
        observed_value=contribution,
        unit="score",
        observed_at="2026-08-01",
        source="fixture",
        quality=quality,
        explanation=f"{factor_id} explanation",
    )


def fixture_inputs():
    return {
        "summary": {
            "date": "2026-08-01",
            "liquidity_regime": "Expanding (+30d)",
            "treasury_10y": 4.6,
            "breakeven_10y": 2.1,
            "housing_yoy": -12.0,
        },
        "credit": {"high_yield_oas": 5.2},
        "valuations": [
            {"sector": "Technology (XLK)", "history": {"percentile": 20.0}},
            {"sector": "Financials (XLF)", "history": {"percentile": 80.0}},
        ],
        "ai_ecosystem": [
            {
                "group": "1. AI Compute & Accelerators",
                "history": {"percentile": 80.0},
            }
        ],
        "news_events": [{"headline": "Context only"}],
        "macro_situation": {
            "quality": "OK",
            "favored_sectors": ["Technology (XLK)", "AI Compute & Accelerators"],
            "disfavored_sectors": ["Consumer Discretionary (XLY)"],
        },
    }


class TestEvidenceAggregation(unittest.TestCase):
    def test_conflicting_factors_remain_visible_and_produce_neutral_uncertainty(self):
        result = aggregate_evidence(
            [factor("liquidity", 3), factor("credit", -3)], expected_weight=2
        )

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["posture"], "NEUTRAL")
        self.assertEqual(
            [item["factor_id"] for item in result["positive_factors"]], ["liquidity"]
        )
        self.assertEqual(
            [item["factor_id"] for item in result["negative_factors"]], ["credit"]
        )
        self.assertLess(result["score_range"][0], 0)
        self.assertGreater(result["score_range"][1], 0)

    def test_missing_and_stale_evidence_widen_range_and_reduce_coverage(self):
        current = aggregate_evidence(
            [
                factor("liquidity", 3),
                factor("valuation", 0),
                factor("credit", 0),
            ],
            expected_weight=3,
        )
        degraded = aggregate_evidence(
            [
                factor("liquidity", 3),
                factor("valuation", 0, quality="missing"),
                factor("credit", 0, quality="stale"),
            ],
            expected_weight=3,
        )

        self.assertLess(degraded["coverage_pct"], current["coverage_pct"])
        self.assertGreater(
            degraded["score_range"][1] - degraded["score_range"][0],
            current["score_range"][1] - current["score_range"][0],
        )
        self.assertEqual(
            {item["factor_id"] for item in degraded["missing_evidence"]},
            {"valuation", "credit"},
        )

    def test_only_a_range_clear_of_neutral_threshold_gets_directional_posture(self):
        self.assertEqual(
            aggregate_evidence([factor("a", 4), factor("b", 4)], 2)["posture"],
            "WATCH",
        )
        self.assertEqual(
            aggregate_evidence([factor("a", -4), factor("b", -4)], 2)["posture"],
            "AVOID",
        )
        self.assertEqual(aggregate_evidence([], 2)["posture"], "NEUTRAL")

    def test_factor_is_immutable_and_rejects_out_of_range_contributions(self):
        evidence = factor("liquidity", 1)

        with self.assertRaises(FrozenInstanceError):
            evidence.contribution = 2
        with self.assertRaisesRegex(ValueError, "contribution"):
            factor("invalid", 6)


class TestSectorEvidenceEngine(unittest.TestCase):
    def test_missing_inputs_are_zero_contribution_factors_with_explicit_reasons(self):
        assessment = SectorEvidenceEngine().generate_assessments(
            summary={"date": "2026-08-01"},
            credit={},
            valuations=[],
            ai_ecosystem=[],
            news_events=[],
            macro_situation={},
        )[0]

        missing = {
            item["factor_id"]: item["missing_reason"]
            for item in assessment["missing_evidence"]
        }
        self.assertEqual(
            missing,
            {
                "macro_quadrant": "Macro quadrant is unavailable.",
                "liquidity": "Liquidity regime is unavailable.",
                "credit": "High-yield OAS is unavailable.",
                "valuation_percentile": "Valuation percentile is unavailable.",
                "real_yield": "Real yield is unavailable.",
                "housing": "Housing YoY is unavailable.",
                "data_quality": "Macro input quality is unavailable.",
            },
        )
        self.assertTrue(all(item["contribution"] == 0 for item in assessment["factors"]))

    def test_sector_assessment_is_order_independent_and_has_no_trade_fields(self):
        engine = SectorEvidenceEngine()
        kwargs = fixture_inputs()

        first = engine.generate_assessments(**kwargs)
        second = engine.generate_assessments(
            **{**kwargs, "valuations": list(reversed(kwargs["valuations"]))}
        )

        self.assertEqual(first, second)
        self.assertTrue({item["posture"] for item in first} <= {"WATCH", "NEUTRAL", "AVOID"})
        self.assertTrue(
            all("action" not in item and "conviction" not in item for item in first)
        )
        self.assertTrue(
            all(
                {
                    "sector_group",
                    "instrument",
                    "benchmark",
                    "posture",
                    "score",
                    "score_range",
                    "coverage_pct",
                    "positive_factors",
                    "negative_factors",
                    "neutral_factors",
                    "missing_evidence",
                    "factors",
                    "methodology",
                    "as_of_date",
                } <= set(item)
                for item in first
            )
        )


if __name__ == "__main__":
    unittest.main()
