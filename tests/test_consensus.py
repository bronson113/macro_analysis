import pandas as pd

from consensus import interpret_consensus


def record(*, survey_date="2026-07-01", horizon_months=6, expected_dff=4.25, expected_fed_assets=7000.0):
    return {
        "survey_date": survey_date,
        "horizon_months": horizon_months,
        "expected_dff": expected_dff,
        "expected_fed_assets": expected_fed_assets,
    }


def test_consensus_selects_closest_horizon_to_six_months_and_is_non_blocking():
    records = [
        record(horizon_months=3, expected_dff=4.3, expected_fed_assets=7000),
        record(horizon_months=7, expected_dff=4.0, expected_fed_assets=7040),
    ]

    out = interpret_consensus(records, 4.25, 7000, pd.Timestamp("2026-08-15"))

    assert out["selected_horizon_months"] == 7
    assert out["policy_direction"] == "EASING"
    assert out["balance_sheet_direction"] == "EXPANDING"
    assert out["blocks_quadrant"] is False


def test_consensus_horizon_ties_choose_the_lower_horizon():
    out = interpret_consensus(
        [
            record(horizon_months=5, expected_dff=4.2),
            record(horizon_months=7, expected_dff=4.2),
        ],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )

    assert out["selected_horizon_months"] == 5


def test_consensus_policy_thresholds_are_inclusive():
    below = interpret_consensus(
        [record(expected_dff=4.15)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )
    above = interpret_consensus(
        [record(expected_dff=4.35)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )
    stable = interpret_consensus(
        [record(expected_dff=4.2499)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )

    assert below["policy_direction"] == "EASING"
    assert above["policy_direction"] == "TIGHTENING"
    assert stable["policy_direction"] == "STABLE"


def test_consensus_balance_sheet_thresholds_are_inclusive():
    expanding = interpret_consensus(
        [record(expected_fed_assets=7035)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )
    contracting = interpret_consensus(
        [record(expected_fed_assets=6965)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )
    stable = interpret_consensus(
        [record(expected_fed_assets=7034.9)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )

    assert expanding["balance_sheet_direction"] == "EXPANDING"
    assert contracting["balance_sheet_direction"] == "CONTRACTING"
    assert stable["balance_sheet_direction"] == "STABLE"


def test_consensus_older_than_120_days_is_stale():
    out = interpret_consensus(
        [record(survey_date="2026-03-01")],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )

    assert out["quality"] == "STALE"
    assert out["blocks_quadrant"] is False


def test_consensus_missing_or_unsupported_inputs_are_unavailable():
    missing_metric = interpret_consensus(
        [{"survey_date": "2026-07-01", "horizon_months": 6, "expected_dff": 4.0}],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )
    unsupported_horizon = interpret_consensus(
        [record(horizon_months=2)], 4.25, 7000, pd.Timestamp("2026-08-15")
    )

    assert missing_metric["quality"] == "UNAVAILABLE"
    assert unsupported_horizon["quality"] == "UNAVAILABLE"
    assert missing_metric["blocks_quadrant"] is False
    assert unsupported_horizon["blocks_quadrant"] is False


def test_consensus_ignores_future_survey_vintages():
    out = interpret_consensus(
        [record(survey_date="2026-08-16")],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )

    assert out["quality"] == "UNAVAILABLE"
    assert out["selected_horizon_months"] is None
