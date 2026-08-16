"""Focused tests for selective sector evidence report presentation."""

from copy import deepcopy
from pathlib import Path

from reporter import MacroReporter


class _StorageStub:
    def get_latest_observation(self, _metric):
        return None


def _analysis(assessments):
    return {
        "summary": {"date": "2026-08-15"},
        "liquidity_details": {},
        "policy_details": {},
        "yield_curve_details": {},
        "credit_details": {},
        "market_details": {},
        "macro_details": {},
        "news_events": [],
        "sector_valuations": [],
        "ai_ecosystem": [],
        "macro_situation": {},
        "constituent_assessments": [],
        "evidence_assessments": assessments,
    }


def _write_report(tmp_path, assessments):
    reporter = MacroReporter(
        storage=_StorageStub(), output_dir=tmp_path, verbose=False
    )
    report_path = reporter.generate_markdown_report(_analysis(assessments))
    return Path(report_path).read_text(encoding="utf-8")


def _valid_assessment(sector, score, posture="NEUTRAL", **overrides):
    assessment = {
        "sector_group": sector,
        "instrument": f"ETF-{sector[:3].upper()}",
        "posture": posture,
        "score": score,
        "score_range": [-10.0, 10.0],
        "coverage_pct": 85.7,
        "factors": [],
        "missing_evidence": [
            {"missing_reason": "Valuation percentile is unavailable."}
        ],
    }
    assessment.update(overrides)
    return assessment


def test_no_signal_report_skips_repeated_sector_table_and_counts_only_usable_inputs(
    tmp_path,
):
    assessments = [
        _valid_assessment("Utilities", 1.0),
        "malformed assessment",
        _valid_assessment("Technology", "not-a-score"),
        _valid_assessment("Industrials", -4.0),
        _valid_assessment("Empty sector", 0.0, sector_group=""),
        _valid_assessment("Bad range", 0.0, score_range=[-10.0]),
        _valid_assessment("Bad coverage", 0.0, coverage_pct=float("nan")),
        {"sector_group": "Not a dict contract", "score": 0.0},
    ]

    content = _write_report(tmp_path, assessments)

    assert "## 5. Sector Evidence Ranking" in content
    assert "No meaningful sector differentiation from current evidence." in content
    assert "Usable assessments: `2`" in content
    assert "Score spread: `5.0` points" in content
    assert "Valuation percentile is unavailable. (`2` of `2` sectors)" in content
    assert "| Relative evidence |" not in content
    assert "Sector Evidence Assessments" not in content


def test_differentiated_report_selects_stable_stronger_and_weaker_rows_and_formats_factors(
    tmp_path,
):
    observed_factors = [
        {
            "factor_id": "real_yield",
            "quality": "current",
            "contribution": -1.0,
            "weight": 1.0,
            "observed_value": 2.44,
            "unit": "percent",
            "observed_at": "2026-08-14",
        },
        {
            "factor_id": "macro_quadrant",
            "quality": "current",
            "contribution": 1.0,
            "weight": 1.0,
            "observed_value": "favorable",
            "unit": "regime",
            "observed_at": "2026-08-14",
        },
    ]
    assessments = [
        _valid_assessment("Alpha", 6.0, "WATCH", factors=deepcopy(observed_factors)),
        _valid_assessment("Beta", 6.0, "WATCH", factors=deepcopy(observed_factors)),
        _valid_assessment("Gamma", 6.0, "WATCH", factors=deepcopy(observed_factors)),
        _valid_assessment("Delta", 6.0, "WATCH", factors=deepcopy(observed_factors)),
        _valid_assessment("Middle One", 1.0),
        _valid_assessment("Middle Two", 0.0),
        _valid_assessment("Lower One", -3.0, "AVOID"),
        _valid_assessment("Lower Two", -5.0, "AVOID"),
        _valid_assessment("Lower Three", -5.0, "AVOID"),
    ]

    content = _write_report(tmp_path, assessments)
    ranking = content.split("## 5. Sector Evidence Ranking", 1)[1]

    assert (
        "| Relative evidence | Sector / Group | Instrument | Posture | Score | Coverage | "
        "Leading observed factors | Primary missing input |"
    ) in content
    assert ranking.count("Stronger evidence") <= 3
    assert ranking.count("Weaker evidence") <= 3
    assert "10Y real yield: 2.44% (-1.0; 2026-08-14)" in ranking
    assert "Additional sectors tied at this score: `1`" in ranking
    assert "relative research evidence, not an allocation recommendation" in ranking
    assert "score is not a forecast return" in ranking
    assert "Macro quadrant is favorable, unfavorable, or neutral" not in ranking

    for sector in ("Alpha", "Beta", "Gamma", "Lower One", "Lower Two", "Lower Three"):
        assert ranking.count(sector) == 1
    assert ranking.count("(tied)") >= 2
