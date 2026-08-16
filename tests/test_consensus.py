import pandas as pd

from consensus import NewYorkFedSMEProvider, interpret_consensus, parse_sme_frame


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


def test_consensus_carries_publication_metric_unit_source_and_parse_status():
    out = interpret_consensus(
        [
            {
                "survey_date": "2026-07-01",
                "publication_date": "2026-07-10",
                "target_date": "2027-01-01",
                "horizon_months": 6,
                "expected_dff": 4.0,
                "expected_fed_assets": 7040.0,
                "metric": "FED_FUNDS_RATE_AND_FED_BALANCE_SHEET_ASSETS",
                "unit": "percent_and_billions_usd",
                "source_url": "https://www.newyorkfed.org/sme",
                "parsing_status": "OK",
            }
        ],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )

    assert out["publication_date"] == pd.Timestamp("2026-07-10")
    assert out["target_date"] == pd.Timestamp("2027-01-01")
    assert out["metric"].startswith("FED_FUNDS_RATE")
    assert out["unit"] == "percent_and_billions_usd"
    assert out["source_url"].endswith("/sme")
    assert out["parsing_status"] == "OK"


def test_consensus_selects_latest_publication_for_same_survey_horizon():
    out = interpret_consensus(
        [
            {
                **record(),
                "publication_date": "2026-07-10",
                "expected_dff": 4.10,
            },
            {
                **record(),
                "publication_date": "2026-08-01",
                "expected_dff": 4.00,
            },
        ],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )

    assert out["publication_date"] == pd.Timestamp("2026-08-01")
    assert out["expected_dff"] == 4.00


def test_malformed_non_selected_consensus_record_does_not_poison_selected_result():
    out = interpret_consensus(
        [
            record(expected_dff=4.0),
            {"survey_date": "not-a-date", "horizon_months": 6, "expected_dff": "bad"},
        ],
        4.25,
        7000,
        pd.Timestamp("2026-08-15"),
    )

    assert out["quality"] == "OK"
    assert out["policy_direction"] == "EASING"


def test_ny_fed_sme_fixture_parser_and_provider_are_offline_testable():
    frame = pd.DataFrame(
        [
            {
                "survey_date": "2026-07-01",
                "publication_date": "2026-07-10",
                "target_date": "2027-01-01",
                "horizon_months": 6,
                "metric": "FED_FUNDS_RATE",
                "median_value": 4.0,
                "unit": "percent",
            },
            {
                "survey_date": "2026-07-01",
                "publication_date": "2026-07-10",
                "target_date": "2027-01-01",
                "horizon_months": 6,
                "metric": "FED_BALANCE_SHEET_ASSETS",
                "median_value": 7040.0,
                "unit": "billions_usd",
            },
        ]
    )
    records = parse_sme_frame(frame, source_url="https://example.test/sme")
    assert len(records) == 1
    assert records[0]["expected_dff"] == 4.0
    assert records[0]["expected_fed_assets"] == 7040.0
    assert records[0]["publication_date"] == pd.Timestamp("2026-07-10")
    assert len(records[0]["metrics"]) == 2


def test_ny_fed_sme_parser_accepts_official_release_layout():
    frame = pd.DataFrame(
        [
            {
                "survey_release_date": "2026-06-03",
                "subject": "fed_funds_target_range",
                "horizon": "Dec. 8-9 2026",
                "horizon_date": "2026-12-09",
                "aggregation": "pctl50",
                "aggregation_value": 0.0363,
                "left_header_value": "Target rate / midpoint of target range",
            },
            {
                "survey_release_date": "2026-06-03",
                "subject": "fed_assets_total_assets",
                "horizon": "December 2026",
                "horizon_date": "2026-12-15",
                "aggregation": "pctl50",
                "aggregation_value": 6794.0,
                "left_header_value": "Total Assets",
            },
        ]
    )

    records = parse_sme_frame(frame, source_url="https://example.test/jun-2026-data.xlsx")

    assert len(records) == 1
    assert records[0]["horizon_months"] == 6
    assert records[0]["expected_dff"] == 3.63
    assert records[0]["expected_fed_assets"] == 6794.0


def test_ny_fed_sme_parser_prefers_combined_panel_when_present():
    frame = pd.DataFrame(
        [
            {
                "survey_release_date": "2026-06-03",
                "panel_type": "Combined",
                "subject": "fed_funds_target_range",
                "horizon": "Dec. 8-9 2026",
                "horizon_date": "2026-12-09",
                "aggregation": "pctl50",
                "aggregation_value": 0.0363,
            },
            {
                "survey_release_date": "2026-06-03",
                "panel_type": "Primary Dealers",
                "subject": "fed_funds_target_range",
                "horizon": "Dec. 8-9 2026",
                "horizon_date": "2026-12-09",
                "aggregation": "pctl50",
                "aggregation_value": 0.08,
            },
        ]
    )

    records = parse_sme_frame(frame, source_url="https://example.test/sme.xlsx")

    assert records[0]["expected_dff"] == 3.63
    assert records[0]["parsing_status"] == "OK"

    provider = NewYorkFedSMEProvider(
        fetch_bytes=lambda _url: b"fixture",
        read_excel=lambda *_args, **_kwargs: frame,
        data_url="https://example.test/jul-data.xlsx",
    )
    provided = provider.get_records()
    assert provided[0]["source_url"] == "https://example.test/jul-data.xlsx"
