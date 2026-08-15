import pandas as pd

from macro_regime import (
    classify_delta,
    classify_liquidity_level,
    classify_policy_gap,
    classify_policy_level,
)


def series(*pairs):
    return pd.DataFrame(pairs, columns=["date", "value"]).assign(
        date=lambda frame: pd.to_datetime(frame.date)
    )


def dated(values, end, freq):
    dates = pd.date_range(end=pd.Timestamp(end), periods=len(values), freq=freq)
    return pd.DataFrame({"date": dates, "value": values})


def liquidity_fixture(effr=4.33, iorb=4.40, sofr=4.36):
    normalized_history = [10.0 + index * (10.0 / 268.0) for index in range(269)]
    normalized_values = normalized_history + [19.5]
    gdp = 30_000.0
    reserve_values = [value * gdp / 100.0 for value in normalized_values]
    return {
        "fed_assets": dated(
            [(value + 1_000.0) * 1_000.0 for value in reserve_values],
            "2026-08-14",
            "7D",
        ),
        "tga": dated([800_000.0] * 270, "2026-08-14", "7D"),
        "rrp": dated([200.0] * 270, "2026-08-14", "7D"),
        "nominal_gdp": dated([gdp] * 25, "2026-08-01", "QS"),
        "effr": dated([effr] * 5, "2026-08-14", "D"),
        "iorb": dated([iorb] * 5, "2026-08-14", "D"),
        "sofr": dated([sofr] * 5, "2026-08-14", "D"),
        "as_of": pd.Timestamp("2026-08-15"),
    }


def test_high_but_falling_liquidity_remains_abundant():
    out = classify_liquidity_level(**liquidity_fixture())

    assert out["state"] == "ABUNDANT"
    assert out["momentum_30d"] == "DETERIORATING"
    assert out["quality"] == "OK"


def test_two_money_market_pressure_flags_withhold_liquidity_state():
    out = classify_liquidity_level(
        **liquidity_fixture(effr=4.39, iorb=4.40, sofr=4.51)
    )

    assert out["core_state"] in {"ABUNDANT", "SCARCE"}
    assert out["state"] is None
    assert out["quality"] == "INDETERMINATE_CONFLICT"


def test_liquidity_level_normalizes_reserves_by_nominal_gdp():
    out = classify_liquidity_level(**liquidity_fixture())

    assert out["reserve_liquidity_billions"] == 5_850.0
    assert out["normalized_liquidity_pct_gdp"] == 19.5
    assert out["current_percentile"] > 90.0
    assert out["historical_p40"] == 14.0
    assert out["historical_p60"] == 16.0


def test_liquidity_percentile_boundaries_are_inclusive():
    from macro_regime import classify_liquidity_percentile

    assert classify_liquidity_percentile(40.0) == "SCARCE"
    assert classify_liquidity_percentile(60.0) == "ABUNDANT"
    assert classify_liquidity_percentile(50.0) == "NEUTRAL"


def test_stale_liquidity_component_withholds_core_state():
    fixture = liquidity_fixture()
    fixture["fed_assets"] = dated(
        [1_000_000.0] * 270,
        "2026-07-01",
        "7D",
    )

    out = classify_liquidity_level(**fixture)

    assert out["state"] is None
    assert out["core_state"] is None
    assert out["quality"] == "INSUFFICIENT_DATA"
    assert any("fed assets" in reason.lower() and "stale" in reason.lower() for reason in out["reasons"])


def test_missing_money_market_corroboration_keeps_core_state_but_is_partial():
    fixture = liquidity_fixture()
    fixture["sofr"] = pd.DataFrame(columns=["date", "value"])

    out = classify_liquidity_level(**fixture)

    assert out["state"] == "ABUNDANT"
    assert out["core_state"] == "ABUNDANT"
    assert out["quality"] == "PARTIAL"
    assert any("sofr" in reason.lower() for reason in out["reasons"])


def test_one_money_market_pressure_flag_is_partial_without_changing_state():
    out = classify_liquidity_level(
        **liquidity_fixture(effr=4.39, iorb=4.40, sofr=4.36)
    )

    assert out["core_state"] == "ABUNDANT"
    assert out["state"] == "ABUNDANT"
    assert out["quality"] == "PARTIAL"
    assert out["effr_iorb_pressure"] is True
    assert out["sofr_iorb_pressure"] is False


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
