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


def test_policy_boundaries_just_outside_neutral_band_are_actionable():
    assert classify_policy_gap(0.5001, 0.0) == "RESTRICTIVE"
    assert classify_policy_gap(-0.5001, 0.0) == "ACCOMMODATIVE"


def test_core_pce_requires_an_exact_one_year_observation():
    out = classify_policy_level(
        series(("2026-08-14", 4.25)),
        series(("2026-06-30", 120.0), ("2025-05-31", 116.0)),
        series(("2026-06-30", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] is None
    assert out["quality"] == "INSUFFICIENT_DATA"
    assert any("12 months" in reason.lower() for reason in out["reasons"])


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


def test_stale_core_pce_withholds_state():
    out = classify_policy_level(
        series(("2026-08-14", 4.25)),
        series(("2026-05-31", 120.0), ("2025-05-31", 116.0)),
        series(("2026-08-14", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] is None
    assert any("core pce" in reason.lower() and "stale" in reason.lower() for reason in out["reasons"])


def test_stale_rstar_withholds_state():
    out = classify_policy_level(
        series(("2026-08-14", 4.25)),
        series(("2026-06-30", 120.0), ("2025-06-30", 116.0)),
        series(("2026-02-15", 0.10)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] is None
    assert any("r-star" in reason.lower() and "stale" in reason.lower() for reason in out["reasons"])


def test_nonfinite_required_inputs_withhold_state():
    fixtures = [
        (
            "dff",
            series(("2026-08-14", float("inf"))),
            series(("2026-06-30", 120.0), ("2025-06-30", 116.0)),
            series(("2026-06-30", 0.10)),
        ),
        (
            "core PCE",
            series(("2026-08-14", 4.25)),
            series(("2026-06-30", float("inf")), ("2025-06-30", 116.0)),
            series(("2026-06-30", 0.10)),
        ),
        (
            "r-star",
            series(("2026-08-14", 4.25)),
            series(("2026-06-30", 120.0), ("2025-06-30", 116.0)),
            series(("2026-06-30", float("inf"))),
        ),
    ]

    for name, dff, core_pce, rstar in fixtures:
        out = classify_policy_level(dff, core_pce, rstar, pd.Timestamp("2026-08-15"))
        assert out["state"] is None, name
        assert out["quality"] == "INSUFFICIENT_DATA", name
        assert any("finite" in reason.lower() for reason in out["reasons"]), name


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


def test_five_year_percentile_excludes_the_exact_current_observation():
    out = classify_policy_level(
        series(
            ("2016-09-01", 3.0),
            ("2020-01-01", 5.0),
            ("2022-01-01", 2.0),
            ("2024-08-10", 1.0),
            ("2025-08-10", 1.0),
            ("2026-08-10", 4.0),
        ),
        series(
            ("2015-09-01", 100.0),
            ("2016-09-01", 100.0),
            ("2019-01-01", 100.0),
            ("2020-01-01", 100.0),
            ("2021-01-01", 100.0),
            ("2022-01-01", 100.0),
            ("2023-08-10", 100.0),
            ("2024-08-10", 100.0),
            ("2025-08-10", 100.0),
            ("2026-08-10", 100.0),
        ),
        series(("2026-08-10", 0.0)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["historical_percentile"] == 66.7
    assert out["history_count"] == 6


def test_history_uses_backward_filled_measurement_dates_inside_window():
    out = classify_policy_level(
        series(("2015-01-01", 4.0), ("2026-08-10", 4.25)),
        series(
            ("2015-01-01", 100.0),
            ("2016-09-01", 100.0),
            ("2025-08-10", 100.0),
            ("2026-08-10", 100.0),
        ),
        series(("2026-08-10", 0.0)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["historical_percentile"] is None
    assert out["history_count"] == 0
    assert out["history_start"] is None


def test_history_requires_five_calendar_years_not_just_1825_days():
    out = classify_policy_level(
        series(("2021-08-15", 3.0), ("2026-08-14", 4.0), ("2026-08-15", 4.25)),
        series(
            ("2020-08-15", 100.0),
            ("2021-08-15", 100.0),
            ("2025-08-14", 100.0),
            ("2026-08-14", 100.0),
            ("2025-08-15", 100.0),
            ("2026-08-15", 100.0),
        ),
        series(("2026-08-15", 0.0)),
        pd.Timestamp("2026-08-15"),
    )

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


def test_policy_momentum_exact_30_and_90_day_boundaries_are_stable():
    out = classify_policy_level(
        series(
            ("2026-08-14", 4.00),
            ("2026-07-14", 4.10),
            ("2026-05-17", 3.90),
        ),
        series(
            ("2026-06-30", 120.0),
            ("2025-06-30", 116.0),
            ("2026-04-30", 120.0),
            ("2025-04-30", 116.0),
        ),
        series(("2026-06-30", 0.0), ("2026-04-30", 0.0)),
        pd.Timestamp("2026-08-15"),
    )

    assert out["momentum_30d"] == "STABLE"
    assert out["momentum_90d"] == "STABLE"


def test_classify_delta_uses_strict_threshold_boundaries():
    assert classify_delta(0.10, "TIGHTENING", "EASING", "STABLE", 0.10) == "STABLE"
    assert classify_delta(-0.10, "TIGHTENING", "EASING", "STABLE", 0.10) == "STABLE"
    assert classify_delta(0.1001, "TIGHTENING", "EASING", "STABLE", 0.10) == "TIGHTENING"
    assert classify_delta(-0.1001, "TIGHTENING", "EASING", "STABLE", 0.10) == "EASING"


def test_classify_delta_treats_decimal_rounding_at_threshold_as_stable():
    assert classify_delta(0.4 - 0.3, "TIGHTENING", "EASING", "STABLE", 0.10) == "STABLE"
    assert classify_delta(0.3 - 0.4, "TIGHTENING", "EASING", "STABLE", 0.10) == "STABLE"
