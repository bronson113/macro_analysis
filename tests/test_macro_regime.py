import pandas as pd

from macro_regime import classify_delta, classify_policy_gap, classify_policy_level


def series(*pairs):
    return pd.DataFrame(pairs, columns=["date", "value"]).assign(
        date=lambda frame: pd.to_datetime(frame.date)
    )


def test_policy_uses_real_rate_gap_not_recent_direction():
    out = classify_policy_level(
        series(("2026-08-14", 4.25), ("2026-07-14", 4.50)),
        series(("2026-06-30", 120.0), ("2025-06-30", 116.0)),
        series(("2026-06-30", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] == "RESTRICTIVE"
    assert out["real_policy_rate"] == 0.802
    assert out["policy_gap"] == 0.702


def test_policy_boundaries_are_neutral():
    assert classify_policy_gap(4.0 - 3.0, 0.5) == "NEUTRAL"
    assert classify_policy_gap(2.0 - 2.0, 0.5) == "NEUTRAL"


def test_policy_stale_required_input_withholds_state():
    out = classify_policy_level(
        series(("2026-08-01", 4.25)),
        series(("2026-06-30", 120.0), ("2025-06-30", 116.0)),
        series(("2026-06-30", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] is None
    assert out["quality"] == "INSUFFICIENT_DATA"
    assert any("dff" in reason.lower() and "stale" in reason.lower() for reason in out["reasons"])


def test_policy_without_five_year_history_keeps_state_but_withholds_percentile():
    out = classify_policy_level(
        series(("2026-08-14", 4.25)),
        series(("2026-06-30", 120.0), ("2025-06-30", 116.0)),
        series(("2026-06-30", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] == "RESTRICTIVE"
    assert out["historical_percentile"] is None
    assert any("five years" in reason.lower() for reason in out["reasons"])


def test_high_but_easing_policy_remains_restrictive_and_reports_momentum():
    out = classify_policy_level(
        series(
            ("2026-08-14", 4.25),
            ("2026-07-14", 4.50),
            ("2026-05-17", 4.50),
        ),
        series(
            ("2026-06-30", 120.0),
            ("2025-06-30", 116.0),
            ("2026-04-30", 118.0),
            ("2025-04-30", 114.0),
        ),
        series(("2026-06-30", 0.10), ("2026-04-30", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] == "RESTRICTIVE"
    assert out["momentum_30d"] == "EASING"
    assert out["momentum_90d"] == "EASING"


def test_classify_delta_uses_strict_threshold_boundaries():
    assert classify_delta(0.10, "TIGHTENING", "EASING", "STABLE", 0.10) == "STABLE"
    assert classify_delta(-0.10, "TIGHTENING", "EASING", "STABLE", 0.10) == "STABLE"
    assert classify_delta(0.1001, "TIGHTENING", "EASING", "STABLE", 0.10) == "TIGHTENING"
    assert classify_delta(-0.1001, "TIGHTENING", "EASING", "STABLE", 0.10) == "EASING"
