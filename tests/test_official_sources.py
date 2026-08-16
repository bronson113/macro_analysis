import pandas as pd

import config
from fetcher import MacroFetcher
from storage import MacroStorage
from consensus import NewYorkFedSMEProvider
from hlw_rstar import HolstonLaubachWilliamsProvider, parse_hlw_frame


def test_hlw_source_is_configured_to_the_new_york_fed_workbook():
    assert config.HLW_RSTAR_SOURCE["source"] == "NY Fed HLW"
    assert config.HLW_RSTAR_SOURCE["url"].endswith(
        "Holston_Laubach_Williams_current_estimates.xlsx"
    )
    assert config.HLW_RSTAR_SOURCE["unit"] == "percent"


def test_hlw_parser_selects_us_natural_rate_and_keeps_publication_metadata():
    frame = pd.DataFrame(
        {
            "Date": ["2025Q4", "2026Q1"],
            "Natural Rate (r*) US": [0.15, 0.20],
        }
    )

    records = parse_hlw_frame(
        frame,
        publication_date="2026-05-29",
        source_url=config.HLW_RSTAR_SOURCE["url"],
    )

    assert records == [
        {
            "date": pd.Timestamp("2025-10-01"),
            "value": 0.15,
            "publication_date": pd.Timestamp("2026-05-29"),
            "vintage_date": pd.Timestamp("2026-05-29"),
            "source_url": config.HLW_RSTAR_SOURCE["url"],
            "unit": "percent",
            "parsing_status": "OK",
        },
        {
            "date": pd.Timestamp("2026-01-01"),
            "value": 0.20,
            "publication_date": pd.Timestamp("2026-05-29"),
            "vintage_date": pd.Timestamp("2026-05-29"),
            "source_url": config.HLW_RSTAR_SOURCE["url"],
            "unit": "percent",
            "parsing_status": "OK",
        },
    ]


def test_hlw_parser_accepts_official_two_row_header_shape():
    frame = pd.DataFrame(
        [[45200, 0.20]],
        columns=pd.MultiIndex.from_tuples(
            [
                ("Unnamed: 0_level_0", "Date"),
                ("Natural Rate (r*)", "US"),
            ]
        ),
    )

    records = parse_hlw_frame(
        frame,
        publication_date="2026-05-29",
        source_url=config.HLW_RSTAR_SOURCE["url"],
    )

    assert records[0]["value"] == 0.20


def test_hlw_provider_is_testable_with_an_offline_fixture():
    fixture = pd.DataFrame(
        {
            "date": ["2026-01-01"],
            "rstar": [0.2],
        }
    )
    provider = HolstonLaubachWilliamsProvider(
        fetch_bytes=lambda _url: b"fixture",
        read_excel=lambda *_args, **_kwargs: fixture,
        publication_date="2026-05-29",
    )

    records = provider.get_records()

    assert records[0]["value"] == 0.2
    assert records[0]["publication_date"] == pd.Timestamp("2026-05-29")
    assert records[0]["source_url"] == config.HLW_RSTAR_SOURCE["url"]


def test_fetcher_persists_hlw_records_with_official_source_metadata(tmp_path):
    fixture = pd.DataFrame({"date": ["2026-01-01"], "rstar": [0.2]})
    provider = HolstonLaubachWilliamsProvider(
        fetch_bytes=lambda _url: b"fixture",
        read_excel=lambda *_args, **_kwargs: fixture,
        publication_date="2026-05-29",
    )
    storage = MacroStorage(
        indicators_csv=tmp_path / "ind.csv",
        observations_csv=tmp_path / "obs.csv",
        snapshots_csv=tmp_path / "snap.csv",
        news_csv=tmp_path / "news.csv",
        run_logs_csv=tmp_path / "logs.csv",
    )
    fetcher = MacroFetcher(storage, hlw_provider=provider)

    count, error = fetcher.fetch_hlw_rstar()
    rows = storage.get_indicator_series("rstar", limit=None, include_metadata=True)

    assert error is None
    assert count == 1
    assert rows.iloc[0]["unit"] == "percent"
    assert rows.iloc[0]["vintage_date"] == pd.Timestamp("2026-05-29")


def test_fetcher_persists_ny_fed_sme_records_for_default_analyzer_boundary(tmp_path):
    frame = pd.DataFrame([
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
    ])
    provider = NewYorkFedSMEProvider(
        fetch_bytes=lambda _url: b"fixture",
        read_excel=lambda *_args, **_kwargs: frame,
        data_url="https://example.test/sme.xlsx",
    )
    storage = MacroStorage(
        indicators_csv=tmp_path / "ind.csv",
        observations_csv=tmp_path / "obs.csv",
        snapshots_csv=tmp_path / "snap.csv",
        news_csv=tmp_path / "news.csv",
        run_logs_csv=tmp_path / "logs.csv",
    )
    fetcher = MacroFetcher(storage, consensus_provider=provider)

    count, error = fetcher.fetch_consensus()
    records = storage.get_consensus_records(as_of=pd.Timestamp("2026-08-15"))

    assert error is None
    assert count == 1
    assert records[0]["expected_dff"] == 4.0
    assert records[0]["publication_date"] == pd.Timestamp("2026-07-10")
