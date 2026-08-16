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


def normalized_values_fixture(normalized_values, *, freq="7D"):
    """Build source-unit observations from literal normalized test values."""

    gdp = 30_000.0
    reserve_values = [value * gdp / 100.0 for value in normalized_values]
    return {
        "fed_assets": dated(
            [(value + 1_000.0) * 1_000.0 for value in reserve_values],
            "2026-08-14",
            freq,
        ),
        "tga": dated([800_000.0] * len(normalized_values), "2026-08-14", freq),
        "rrp": dated([200.0] * len(normalized_values), "2026-08-14", freq),
        "nominal_gdp": dated([gdp] * 50, "2026-08-01", "QS"),
        "effr": dated([4.33] * 5, "2026-08-14", "D"),
        "iorb": dated([4.40] * 5, "2026-08-14", "D"),
        "sofr": dated([4.36] * 5, "2026-08-14", "D"),
        "as_of": pd.Timestamp("2026-08-15"),
    }


def test_high_but_falling_liquidity_remains_abundant():
    out = classify_liquidity_level(**liquidity_fixture())

    assert out["state"] == "ABUNDANT"
    assert out["momentum_30d"] == "DETERIORATING"
    assert out["quality"] == "OK"
    assert out["current_percentile"] == 94.8
    assert out["history_count"] == 269
    assert out["history_start"] == pd.Timestamp("2021-06-18")
    assert out["history_end"] == pd.Timestamp("2026-08-07")
    assert out["effr_iorb_spread_bp"] == -7.0
    assert out["sofr_iorb_spread_bp"] == -4.0


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


def test_non_positive_nominal_gdp_is_rejected_with_structured_quality_reason():
    fixture = liquidity_fixture()
    fixture["nominal_gdp"] = fixture["nominal_gdp"].assign(value=0.0)

    out = classify_liquidity_level(**fixture)

    assert out["state"] is None
    assert out["quality"] == "INSUFFICIENT_DATA"
    assert any("gdp" in reason.lower() and "positive" in reason.lower() for reason in out["reasons"])


def test_declared_source_unit_mismatch_is_rejected_before_normalization():
    fixture = liquidity_fixture()
    fixture["nominal_gdp"] = fixture["nominal_gdp"].assign(unit="millions")

    out = classify_liquidity_level(**fixture)

    assert out["state"] is None
    assert out["quality"] == "INSUFFICIENT_DATA"
    assert any("unit" in reason.lower() and "gdp" in reason.lower() for reason in out["reasons"])


def test_mis_scaled_nominal_gdp_is_rejected_with_structured_reason():
    fixture = liquidity_fixture()
    fixture["nominal_gdp"] = fixture["nominal_gdp"].assign(
        value=30_000_000.0,
        unit="billions",
    )

    out = classify_liquidity_level(**fixture)

    assert out["state"] is None
    assert any("gdp" in reason.lower() and "scale" in reason.lower() for reason in out["reasons"])


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


def test_effr_iorb_pressure_boundary_is_inclusive_at_minus_two_basis_points():
    out = classify_liquidity_level(
        **liquidity_fixture(effr=4.38, iorb=4.40, sofr=4.36)
    )

    assert out["effr_iorb_spread_bp"] == -2.0
    assert out["effr_iorb_pressure"] is True
    assert out["state"] == "ABUNDANT"


def test_sofr_iorb_pressure_boundary_is_inclusive_at_plus_ten_basis_points():
    out = classify_liquidity_level(
        **liquidity_fixture(effr=4.33, iorb=4.40, sofr=4.50)
    )

    assert out["sofr_iorb_spread_bp"] == 10.0
    assert out["sofr_iorb_pressure"] is True
    assert out["state"] == "ABUNDANT"


def test_money_market_spread_means_use_five_literal_business_day_observations():
    fixture = liquidity_fixture()
    fixture["effr"] = dated([4.30, 4.31, 4.32, 4.33, 4.34], "2026-08-14", "D")
    fixture["iorb"] = dated([4.40, 4.40, 4.40, 4.40, 4.40], "2026-08-14", "D")
    fixture["sofr"] = dated([4.35, 4.36, 4.37, 4.38, 4.39], "2026-08-14", "D")

    out = classify_liquidity_level(**fixture)

    assert out["effr_iorb_spread_bp"] == -8.0
    assert out["sofr_iorb_spread_bp"] == -3.0
    assert out["corroboration_dates"] == [
        pd.Timestamp("2026-08-10"),
        pd.Timestamp("2026-08-11"),
        pd.Timestamp("2026-08-12"),
        pd.Timestamp("2026-08-13"),
        pd.Timestamp("2026-08-14"),
    ]


def test_rank_just_below_abundant_boundary_stays_neutral_before_rounding():
    values = [10.0] * 241 + [30.0] * 161 + [20.0]

    out = classify_liquidity_level(**normalized_values_fixture(values))

    # 241 / 402 * 100 = 59.950248756..., which reports as 60.0 but is
    # strictly below the abundant boundary.
    assert out["history_count"] == 402
    assert out["current_percentile"] == 60.0
    assert out["state"] == "NEUTRAL"


def test_rank_just_above_scarce_boundary_stays_neutral_before_rounding():
    values = [10.0] * 161 + [30.0] * 241 + [20.0]

    out = classify_liquidity_level(**normalized_values_fixture(values))

    # 161 / 402 * 100 = 40.049751243..., which reports as 40.0 but is
    # strictly above the scarce boundary.
    assert out["history_count"] == 402
    assert out["current_percentile"] == 40.0
    assert out["state"] == "NEUTRAL"


def test_as_of_joins_ignore_future_extreme_observations():
    fixture = liquidity_fixture()
    future_date = pd.Timestamp("2026-08-21")
    for key, value in (
        ("fed_assets", 99_000_000.0),
        ("tga", 1.0),
        ("rrp", 1.0),
        ("nominal_gdp", 1.0),
        ("effr", 9.0),
        ("iorb", 1.0),
        ("sofr", 9.0),
    ):
        fixture[key] = pd.concat(
            [
                fixture[key],
                pd.DataFrame({"date": [future_date], "value": [value]}),
            ],
            ignore_index=True,
        )

    out = classify_liquidity_level(**fixture)

    assert out["normalized_liquidity_pct_gdp"] == 19.5
    assert out["state"] == "ABUNDANT"
    assert out["fed_assets_date"] == pd.Timestamp("2026-08-14")
    assert out["nominal_gdp_date"] == pd.Timestamp("2026-07-01")
    assert out["effr_date"] == pd.Timestamp("2026-08-14")


def test_required_liquidity_freshness_limits_are_inclusive_and_one_day_stale_fails():
    required_limits = (
        ("fed_assets", 14, "7D"),
        ("tga", 14, "7D"),
        ("rrp", 7, "7D"),
        ("nominal_gdp", 120, "93D"),
    )
    for key, limit_days, frequency in required_limits:
        fresh = liquidity_fixture()
        target = fresh["as_of"] - pd.Timedelta(days=limit_days)
        fresh[key] = dated(
            [fresh[key]["value"].iloc[-1]] * len(fresh[key]),
            target,
            frequency,
        )
        fresh_out = classify_liquidity_level(**fresh)
        assert fresh_out["state"] is not None, key
        assert not any(
            key.replace("_", " ") in reason.lower() and "stale" in reason.lower()
            for reason in fresh_out["reasons"]
        ), key

        stale = liquidity_fixture()
        stale_target = stale["as_of"] - pd.Timedelta(days=limit_days + 1)
        stale[key] = dated(
            [stale[key]["value"].iloc[-1]] * len(stale[key]),
            stale_target,
            frequency,
        )
        stale_out = classify_liquidity_level(**stale)
        assert stale_out["state"] is None, key
        assert any("stale" in reason.lower() for reason in stale_out["reasons"]), key


def test_money_market_freshness_limits_are_inclusive_and_one_day_stale_is_partial():
    for key in ("effr", "iorb", "sofr"):
        fresh = liquidity_fixture()
        fresh_dates = pd.date_range(end="2026-08-08", periods=7, freq="D")
        fresh[key] = pd.DataFrame({"date": fresh_dates, "value": [4.33] * 7})
        # Keep all three corroboration series on the same five business days.
        for other in ("effr", "iorb", "sofr"):
            if other != key:
                fresh[other] = pd.DataFrame({"date": fresh_dates, "value": [4.33] * 7})
        fresh_out = classify_liquidity_level(**fresh)
        assert fresh_out["state"] == "ABUNDANT", key

        stale = {
            name: frame.copy() if hasattr(frame, "copy") else frame
            for name, frame in fresh.items()
        }
        stale_dates = pd.date_range(end="2026-08-07", periods=7, freq="D")
        stale[key] = pd.DataFrame({"date": stale_dates, "value": [4.33] * 7})
        stale_out = classify_liquidity_level(**stale)
        assert stale_out["state"] == "ABUNDANT", key
        assert stale_out["quality"] == "PARTIAL", key
        assert any(
            key in reason.lower() and "stale" in reason.lower()
            for reason in stale_out["reasons"]
        ), key


def test_liquidity_history_requires_two_hundred_weeks_and_five_calendar_years():
    short_span = normalized_values_fixture([10.0] * 200 + [20.0])
    short_span_out = classify_liquidity_level(**short_span)
    assert short_span_out["history_count"] == 200
    assert short_span_out["state"] is None
    assert any("five years" in reason.lower() for reason in short_span_out["reasons"])

    sparse = normalized_values_fixture([10.0] * 100 + [20.0], freq="19D")
    sparse_out = classify_liquidity_level(**sparse)
    assert sparse_out["history_count"] == 100
    assert sparse_out["state"] is None
    assert any("minimum 200" in reason.lower() for reason in sparse_out["reasons"])


def test_liquidity_momentum_exact_boundaries_are_stable():
    increasing = classify_liquidity_level(
        **normalized_values_fixture([10.0] * 269 + [10.05])
    )
    decreasing = classify_liquidity_level(
        **normalized_values_fixture([10.0] * 269 + [9.95])
    )

    assert increasing["momentum_30d"] == "STABLE"
    assert increasing["momentum_90d"] == "STABLE"
    assert decreasing["momentum_30d"] == "STABLE"
    assert decreasing["momentum_90d"] == "STABLE"


def test_liquidity_momentum_just_outside_boundaries_is_actionable():
    increasing = classify_liquidity_level(
        **normalized_values_fixture([10.0] * 269 + [10.0501])
    )
    decreasing = classify_liquidity_level(
        **normalized_values_fixture([10.0] * 269 + [9.9499])
    )

    assert increasing["momentum_30d"] == "IMPROVING"
    assert increasing["momentum_90d"] == "IMPROVING"
    assert decreasing["momentum_30d"] == "DETERIORATING"
    assert decreasing["momentum_90d"] == "DETERIORATING"


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


def test_rstar_freshness_uses_publication_date_when_available():
    rstar = series(("2026-01-01", 0.10)).assign(
        publication_date=pd.to_datetime(["2026-05-29"]),
        vintage_date=pd.to_datetime(["2026-05-29"]),
        unit="percent",
    )
    out = classify_policy_level(
        series(("2026-08-14", 4.25)).assign(unit="percent"),
        series(
            ("2026-06-30", 120.0),
            ("2025-06-30", 116.0),
        ).assign(unit="index"),
        rstar,
        pd.Timestamp("2026-08-15"),
    )

    assert out["state"] == "RESTRICTIVE"
    assert out["rstar_date"] == pd.Timestamp("2026-01-01")
    assert out["rstar_age_days"] == 78


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
