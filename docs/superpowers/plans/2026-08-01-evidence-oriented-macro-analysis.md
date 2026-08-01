# Evidence-Oriented Macro Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace deterministic trade calls with transparent evidence postures, rigorous aggregate valuation and peer cohorts, point-in-time outcome evaluation, semantic report changes, resilient CSV/source handling, and updated web consumers.

**Architecture:** Immutable evidence factors flow through a pure aggregator into `WATCH`, `NEUTRAL`, or `AVOID` assessments. Valuation, peer, news, source-health, and outcome-evaluation modules produce explicit quality metadata, while Python reports and the React dashboard consume one structured payload contract.

**Tech Stack:** Python 3.10, pandas, yfinance, `unittest`, React 19, Node test runner, Vite, GitHub Actions.

## Global Constraints

- The deterministic layer must not emit `BUY`, `SELL`, `ACCUMULATE`, `TRIM`, or conviction labels.
- Public deterministic postures are exactly `WATCH`, `NEUTRAL`, or `AVOID` and are research-review states, not execution instructions.
- Missing or stale evidence widens uncertainty and is never silently treated as current.
- Keyword-tagged news is `uninterpreted` context and contributes no directional score.
- Historical evaluation must be point-in-time and must not reconstruct unavailable historical valuation or news inputs.
- CSV remains the persistence format; commercial providers and database migration are out of scope.
- Rename `DynamicMacroAnalyst` to `MechanicalMacroAnalyst`; deterministic code must not describe itself as an LLM or Gemini analyst.
- Do not add a repository license without owner direction.
- Every behavior change follows a witnessed failing-test then passing-test cycle.

---

## File Structure

- `evidence.py`: immutable factor model, validation, aggregation, uncertainty, and posture mapping.
- `recommendations.py`: sector-specific factor construction through `SectorEvidenceEngine`; no mutable action overrides.
- `valuation.py`: aggregate-fundamental sector multiples, historical percentile classification, and coverage metadata.
- `peer_cohorts.py`: declared comparable-company cohorts and minimum-peer policy.
- `mechanical_analyst.py`: company-to-cohort historical relative valuation and watch candidates.
- `news_analyzer.py`: provenance-rich retrieval tags with no mechanical sentiment.
- `outcome_evaluation.py`: point-in-time signal/outcome models and return metrics.
- `storage.py`: centralized CSV schemas, cooperative locks, atomic writes, source health, and signal ledger persistence.
- `source_health.py`: normalized source-result metadata and error categories.
- `analyzer.py`: orchestration and unified public analysis contract.
- `reporter.py`: evidence/posture rendering and structured semantic change-state sidecars.
- `raw_data_engine.py`: provider-neutral payload metadata and evidence assessments.
- `extract_dashboard_data.py`: export structured assessments, source health, and evaluation summaries.
- `web/src/components/EvidenceAssessment.jsx`: accessible posture, range, coverage, factor, and missing-evidence UI.
- `web/src/App.jsx`, `web/src/components/NewsFeed.jsx`, `web/src/components/StockMatrix.jsx`: new payload consumers.
- `web/src/utils/evidencePresentation.js`: pure display helpers tested with Node.
- `tests/test_evidence.py`, `tests/test_valuation.py`, `tests/test_news_context.py`, `tests/test_outcome_evaluation.py`, `tests/test_storage_resilience.py`: focused behavior tests.
- `tests/test_macro_pipeline.py`: end-to-end Python contract and semantic-report migration tests.
- `web/src/utils/evidencePresentation.test.mjs`: web contract tests.
- `README.md`, `docs/chatgpt_coworker_morning_prompt.md`, `.gitignore`, `.github/workflows/*.yml`: documentation and operational hardening.

---

### Task 1: Immutable Evidence Domain and Sector Aggregation

**Files:**
- Create: `evidence.py`
- Modify: `recommendations.py`
- Create: `tests/test_evidence.py`

**Interfaces:**
- Produces: `EvidenceFactor`, `aggregate_evidence(factors, expected_weight) -> dict`, and `SectorEvidenceEngine.generate_assessments(...) -> list[dict]`.
- Assessment keys: `sector_group`, `instrument`, `benchmark`, `posture`, `score`, `score_range`, `coverage_pct`, `positive_factors`, `negative_factors`, `neutral_factors`, `missing_evidence`, `factors`, `methodology`, and `as_of_date`. `instrument` is the sector ETF or declared basket being assessed; `benchmark` is `SPY`.

- [ ] **Step 1: Write failing evidence aggregation tests**

```python
from evidence import EvidenceFactor, aggregate_evidence


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


def test_conflicting_factors_remain_visible_and_produce_neutral_uncertainty():
    result = aggregate_evidence([factor("liquidity", 3), factor("credit", -3)], expected_weight=2)
    assert result["score"] == 0
    assert result["posture"] == "NEUTRAL"
    assert [item["factor_id"] for item in result["positive_factors"]] == ["liquidity"]
    assert [item["factor_id"] for item in result["negative_factors"]] == ["credit"]
    assert result["score_range"][0] < 0 < result["score_range"][1]


def test_missing_and_stale_evidence_widen_range_and_reduce_coverage():
    current = aggregate_evidence([
        factor("liquidity", 3),
        factor("valuation", 0),
        factor("credit", 0),
    ], expected_weight=3)
    degraded = aggregate_evidence([
        factor("liquidity", 3),
        factor("valuation", 0, quality="missing"),
        factor("credit", 0, quality="stale"),
    ], expected_weight=3)
    assert degraded["coverage_pct"] < current["coverage_pct"]
    assert degraded["score_range"][1] - degraded["score_range"][0] > current["score_range"][1] - current["score_range"][0]
    assert {item["factor_id"] for item in degraded["missing_evidence"]} == {"valuation", "credit"}


def test_only_a_range_clear_of_neutral_threshold_gets_directional_posture():
    assert aggregate_evidence([factor("a", 4), factor("b", 4)], 2)["posture"] == "WATCH"
    assert aggregate_evidence([factor("a", -4), factor("b", -4)], 2)["posture"] == "AVOID"
    assert aggregate_evidence([], 2)["posture"] == "NEUTRAL"
```

- [ ] **Step 2: Run the focused tests and witness the import failure**

Run: `python -m unittest tests.test_evidence -v`

Expected: FAIL because `evidence` does not exist.

- [ ] **Step 3: Implement the immutable model and pure aggregator**

```python
from dataclasses import asdict, dataclass
from typing import Any, Optional

VALID_DIRECTIONS = {"positive", "negative", "neutral"}
VALID_QUALITY = {"current", "stale", "missing"}


@dataclass(frozen=True)
class EvidenceFactor:
    factor_id: str
    category: str
    direction: str
    contribution: float
    weight: float
    observed_value: Any
    unit: str
    observed_at: Optional[str]
    source: str
    quality: str
    explanation: str
    missing_reason: Optional[str] = None

    def __post_init__(self):
        if self.direction not in VALID_DIRECTIONS:
            raise ValueError(f"invalid direction: {self.direction}")
        if self.quality not in VALID_QUALITY:
            raise ValueError(f"invalid quality: {self.quality}")
        if not -5 <= self.contribution <= 5:
            raise ValueError("contribution must be between -5 and 5")
        if self.weight <= 0:
            raise ValueError("weight must be positive")

    def to_dict(self):
        return asdict(self)


def aggregate_evidence(factors, expected_weight):
    serialized = [item.to_dict() for item in factors]
    usable = [item for item in factors if item.quality == "current"]
    stale = [item for item in factors if item.quality == "stale"]
    available_weight = sum(item.weight for item in usable)
    stale_weight = sum(item.weight for item in stale)
    denominator = max(float(expected_weight), 1.0)
    coverage = min(1.0, available_weight / denominator)
    score = max(-10.0, min(10.0, sum(item.contribution * item.weight for item in usable)))
    positive_weight = sum(item.weight for item in usable if item.contribution > 0)
    negative_weight = sum(item.weight for item in usable if item.contribution < 0)
    disagreement = min(positive_weight, negative_weight) / max(positive_weight, negative_weight, 1.0)
    half_width = min(5.0, (1.0 - coverage) * 4.0 + disagreement * 2.0 + stale_weight / denominator * 2.0)
    low = max(-10.0, score - half_width)
    high = min(10.0, score + half_width)
    posture = "WATCH" if low >= 2.0 else "AVOID" if high <= -2.0 else "NEUTRAL"
    return {
        "score": round(score, 2),
        "score_range": [round(low, 2), round(high, 2)],
        "coverage_pct": round(coverage * 100.0, 1),
        "posture": posture,
        "positive_factors": [item for item in serialized if item["quality"] == "current" and item["contribution"] > 0],
        "negative_factors": [item for item in serialized if item["quality"] == "current" and item["contribution"] < 0],
        "neutral_factors": [item for item in serialized if item["quality"] == "current" and item["contribution"] == 0],
        "missing_evidence": [item for item in serialized if item["quality"] != "current"],
        "factors": serialized,
    }
```

- [ ] **Step 4: Replace mutable recommendations with factor construction**

Implement `SectorEvidenceEngine` in `recommendations.py`. Build independent factors for macro quadrant (`+2` favored, `-2` disfavored, `0` otherwise), liquidity (`+1` expanding, `-1` contracting), credit (`-3` above 5% except `+1` for Healthcare and Consumer Staples), valuation percentile (`+2` at or below 25th percentile, `-2` at or above 75th), restrictive real yield (`-1` for Technology, AI, and Robotics above 2%), housing (`-2` for Consumer Discretionary and Industrials below -10% YoY), and data quality. Pass expected weight `7` to `aggregate_evidence`; absent inputs become zero-contribution `missing` factors with exact reasons. Add `sector_group`, the assessed `instrument`, `benchmark="SPY"`, methodology text, and date after aggregation.

- [ ] **Step 5: Add tests proving rule order cannot change the result and trade fields are absent**

```python
def test_sector_assessment_is_order_independent_and_has_no_trade_fields():
    engine = SectorEvidenceEngine()
    kwargs = fixture_inputs()
    first = engine.generate_assessments(**kwargs)
    second = engine.generate_assessments(**{**kwargs, "valuations": list(reversed(kwargs["valuations"]))})
    assert first == second
    assert {item["posture"] for item in first} <= {"WATCH", "NEUTRAL", "AVOID"}
    assert all("action" not in item and "conviction" not in item for item in first)
```

Run: `python -m unittest tests.test_evidence -v`

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add evidence.py recommendations.py tests/test_evidence.py
git commit -m "feat: replace trade rules with evidence aggregation"
```

---

### Task 2: Aggregate-Fundamental Valuation and Historical Percentiles

**Files:**
- Modify: `valuation.py`
- Create: `tests/test_valuation.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- Produces: `aggregate_sector_fundamentals(rows) -> dict` and `SectorValuationEngine.classify_history(sector, multiple, value) -> dict`.
- Valuation result keys include `trailing_pe`, `forward_pe`, `ev_ebitda`, `coverage`, `history`, and `valuation_status`.

- [ ] **Step 1: Write hand-calculated aggregate tests**

```python
from valuation import aggregate_sector_fundamentals


def test_aggregate_multiples_use_implied_fundamentals_not_mean_ratios():
    result = aggregate_sector_fundamentals([
        {"ticker": "A", "marketCap": 900.0, "enterpriseValue": 1000.0, "trailingPE": 30.0, "forwardPE": 18.0, "enterpriseToEbitda": 10.0},
        {"ticker": "B", "marketCap": 100.0, "enterpriseValue": 120.0, "trailingPE": 10.0, "forwardPE": 10.0, "enterpriseToEbitda": 6.0},
    ])
    assert result["trailing_pe"] == 25.0
    assert result["forward_pe"] == 16.67
    assert result["ev_ebitda"] == 9.33
    assert result["coverage"]["forward_pe_pct"] == 100.0


def test_negative_and_missing_denominators_reduce_coverage_instead_of_entering_ratio():
    result = aggregate_sector_fundamentals([
        {"ticker": "A", "marketCap": 80.0, "forwardPE": 20.0},
        {"ticker": "LOSS", "marketCap": 20.0, "forwardPE": -5.0},
    ])
    assert result["forward_pe"] == 20.0
    assert result["coverage"]["forward_pe_pct"] == 80.0
    assert result["coverage"]["excluded_forward_pe"] == ["LOSS"]
```

- [ ] **Step 2: Run the valuation tests and witness the missing helper failure**

Run: `python -m unittest tests.test_valuation -v`

Expected: FAIL because `aggregate_sector_fundamentals` does not exist.

- [ ] **Step 3: Implement aggregation from implied earnings and EBITDA**

Use `marketCap / trailingPE`, `marketCap / forwardPE`, and `enterpriseValue / enterpriseToEbitda` only for positive finite ratios and numerators. Divide summed numerators by summed implied denominators. Round display values to two decimals. Coverage is eligible numerator divided by total positive numerator. Return eligible and excluded ticker lists for all three metrics.

- [ ] **Step 4: Replace hard-coded norms with stored historical distributions**

For each sector/multiple storage key, load up to 756 observations. Require 60 observations spanning at least 180 days. With enough history, compute the current percentile using the proportion of observations less than or equal to the current value and return `Discounted Historical Range` at or below 25, `Typical Historical Range` between 25 and 75, and `Rich Historical Range` at or above 75. Otherwise return `Insufficient History` with sample count and span. Remove `HISTORICAL_NORMS` from decision logic and expose the history result alongside coverage.

- [ ] **Step 5: Add history boundary tests and run the focused suite**

```python
def test_history_classification_refuses_short_samples():
    storage = FakeStorage([10.0, 11.0, 12.0])
    result = SectorValuationEngine(storage).classify_history("Technology (XLK)", "forward_pe", 15.0)
    assert result == {"status": "Insufficient History", "percentile": None, "sample_size": 3, "span_days": 2}


def test_history_classification_uses_percentile_not_fixed_fair_multiple():
    storage = FakeStorage(list(range(10, 70)), day_spacing=4)
    result = SectorValuationEngine(storage).classify_history("Technology (XLK)", "forward_pe", 65.0)
    assert result["status"] == "Rich Historical Range"
    assert result["percentile"] >= 75
```

Run: `python -m unittest tests.test_valuation tests.test_macro_pipeline -v`

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add valuation.py tests/test_valuation.py tests/test_macro_pipeline.py
git commit -m "feat: aggregate sector valuation fundamentals"
```

---

### Task 3: Comparable Peer Cohorts and Mechanical Analyst Naming

**Files:**
- Create: `peer_cohorts.py`
- Create: `mechanical_analyst.py`
- Delete: `llm_analyst.py`
- Modify: `raw_data_engine.py`
- Modify: `analyzer.py`
- Modify: `stock_relative_valuation.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- Produces: `PEER_COHORTS`, `ticker_to_cohort() -> dict[str, str]`, and `MechanicalMacroAnalyst.analyze_raw_payload(payload) -> dict`.
- Candidate keys: `group`, `ticker`, `relative_valuation_status`, `posture`, `evidence`, and `missing_evidence`; no `action`, `conviction`, or buy language.

- [ ] **Step 1: Write failing cohort and eligibility tests**

```python
def test_technology_business_models_are_not_one_peer_group():
    mapping = ticker_to_cohort()
    assert mapping["MU"] == "Memory"
    assert mapping["NVDA"] == "Fabless Accelerators"
    assert mapping["TSM"] == "Foundries"
    assert mapping["MSFT"] == "Software & Cloud"
    assert len({mapping[ticker] for ticker in ["MU", "NVDA", "TSM", "AAPL", "MSFT"]}) == 5


def test_analyst_refuses_relative_call_with_fewer_than_three_valid_peers():
    result = MechanicalMacroAnalyst(FakeStorage()).analyze_raw_payload(payload_with_two_memory_companies())
    item = result["constituent_assessments"][0]
    assert item["relative_valuation_status"] == "Insufficient Comparable Peers"
    assert item["posture"] == "NEUTRAL"
```

- [ ] **Step 2: Run tests and witness missing-module failures**

Run: `python -m unittest tests.test_macro_pipeline -v`

Expected: FAIL because `peer_cohorts` and `mechanical_analyst` do not exist.

- [ ] **Step 3: Declare focused cohorts**

Create cohorts for Memory (`MU`, `WDC`, `STX`), Fabless Accelerators (`NVDA`, `AMD`, `AVGO`, `QCOM`), Foundries (`TSM`, `INTC`, `GFS`), Semiconductor Equipment (`ASML`, `AMAT`, `LRCX`, `KLAC`, `TER`), Software & Cloud (`MSFT`, `ORCL`, `CRM`, `ADBE`), Consumer Hardware & Platforms (`AAPL`, `GOOGL`, `META`), Banks (`JPM`, `BAC`, `WFC`, `C`, `SCHW`), Capital Markets (`GS`, `MS`, `BLK`, `AXP`), Managed Care (`UNH`, `HUM`, `ELV`, `CI`, `CVS`), Pharmaceuticals (`JNJ`, `LLY`, `ABBV`, `MRK`, `PFE`), Energy Producers (`XOM`, `CVX`, `COP`, `EOG`), Refiners (`MPC`, `PSX`, `VLO`), Industrial Machinery (`GE`, `CAT`, `HON`, `DE`, `ROK`), Retail & Consumer (`AMZN`, `HD`, `MCD`, `NKE`, `LOW`, `SBUX`, `BKNG`), Physical AI & Robotics (`TSLA`, `SYM`, `ISRG`), Downstream Power & Grid (`CEG`, `VST`, `ETN`, `GEV`), Datacenter Cooling (`VRT`, `MOD`, `SMCI`), and Critical Minerals (`FCX`, `MP`). Enforce one primary cohort per ticker in `ticker_to_cohort` and fail fast on duplicates.

- [ ] **Step 4: Move and rewrite the deterministic analyst**

Rename the class and module. Compute cohort medians rather than broad averages. Require at least three valid peers, at least 60 historical relative observations spanning 180 days, and a current ratio at least 20% below its historical median before returning `WATCH`. Otherwise return `NEUTRAL` with explicit reasons. Remove the legacy below-current-average fallback and every trade directive.

- [ ] **Step 5: Make raw payload metadata provider-neutral**

Change docstrings and metadata engine version to `3.0-EvidenceRawPayload`, build stock rows from `PEER_COHORTS`, and include `peer_cohort`. Update `analyzer.py` imports and attribute names to `mechanical_analyst`.

- [ ] **Step 6: Run regression tests and commit**

Run: `python -m unittest tests.test_macro_pipeline -v`

Expected: PASS with the historical-relative tests using focused cohorts and no trade actions.

```bash
git add peer_cohorts.py mechanical_analyst.py raw_data_engine.py analyzer.py stock_relative_valuation.py tests/test_macro_pipeline.py
git rm llm_analyst.py
git commit -m "feat: use comparable cohorts for relative valuation"
```

---

### Task 4: Uninterpreted News Context

**Files:**
- Modify: `news_analyzer.py`
- Modify: `storage.py`
- Create: `tests/test_news_context.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- Produces: `MacroNewsAnalyzer._tag_topics(title, summary) -> list[str]` and stored news fields `topic_tags`, `interpretation_status`, `published_at`, and `retrieved_at`.

- [ ] **Step 1: Write failing tests proving keywords do not become sentiment**

```python
def test_keyword_tags_are_context_not_directional_scores():
    result = MacroNewsAnalyzer(FakeStorage())._build_context(
        "CEO says rate hike fears are not justified",
        "The company rejected reports of a crisis.",
    )
    assert set(result["topic_tags"]) == {"monetary_policy", "stress"}
    assert result["interpretation_status"] == "uninterpreted"
    assert result["impact_score"] is None
    assert result["sentiment"] is None


def test_news_cannot_change_sector_evidence_score():
    without_news = build_sector_assessment(news_events=[])
    with_news = build_sector_assessment(news_events=[{"title": "crisis rate hike layoffs", "topic_tags": ["stress"], "interpretation_status": "uninterpreted"}])
    assert with_news["score"] == without_news["score"]
    assert with_news["posture"] == without_news["posture"]
```

- [ ] **Step 2: Run focused tests and witness current classifier behavior fail**

Run: `python -m unittest tests.test_news_context -v`

Expected: FAIL because the current classifier emits fixed scores and sentiment.

- [ ] **Step 3: Implement topic tagging and provenance fields**

Map phrases to non-directional tags: hawkish/dovish phrases → `monetary_policy`, defaults/crisis/stress phrases → `stress`, and company warning/layoff phrases → `corporate_fundamentals`. Deduplicate and sort tags. Every fetched item sets `impact_score=None`, `sentiment=None`, `interpretation_status="uninterpreted"`, `published_at` when supplied, and `retrieved_at` to the fetch timestamp.

- [ ] **Step 4: Update storage schema and reads for news context**

Persist `topic_tags` as stable JSON text, preserve null score/sentiment, and deserialize tags in `get_recent_news`. Keep existing CSV rows readable by defaulting absent tags to `[]` and interpretation status to `legacy_uninterpreted`.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_news_context tests.test_macro_pipeline -v`

Expected: PASS.

```bash
git add news_analyzer.py storage.py tests/test_news_context.py tests/test_macro_pipeline.py
git commit -m "feat: treat news keywords as uninterpreted context"
```

---

### Task 5: Unified Analyzer Contract and Semantic Report Changes

**Files:**
- Modify: `analyzer.py`
- Modify: `reporter.py`
- Modify: `raw_data_engine.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- `MacroAnalyzer.generate_full_snapshot()` returns `evidence_assessments` and `constituent_assessments` rather than `recommendations` and action-bearing lagging opportunities.
- Reporter sidecars: `notable_state_YYYY-MM-DD.json` and `latest_notable_state.json`, containing `{key, fingerprint, body}` objects.

- [ ] **Step 1: Write the failing Shiller semantic regression test**

```python
def test_shiller_numeric_drift_inside_same_rating_is_unchanged():
    previous = [{
        "key": "valuation:shiller_pe",
        "fingerprint": "valuation:shiller_pe|Very Expensive",
        "body": "**Valuation:** Shiller PE Ratio is `39.93` (`Very Expensive`).",
    }]
    current = NotableItem(
        key="valuation:shiller_pe",
        fingerprint="valuation:shiller_pe|Very Expensive",
        body="**Valuation:** Shiller PE Ratio is `40.62` (`Very Expensive`).",
    )
    assert apply_notable_change_labels([current], previous) == [
        "**Unchanged:** **Valuation:** Shiller PE Ratio is `40.62` (`Very Expensive`)."
    ]
```

- [ ] **Step 2: Write a failing end-to-end contract test**

```python
def test_snapshot_and_report_expose_evidence_without_trade_directives():
    analysis = build_fixture_analysis()
    assert analysis["evidence_assessments"]
    serialized = json.dumps(analysis["evidence_assessments"])
    assert "conviction" not in serialized.lower()
    assert not re.search(r"\b(BUY|SELL|ACCUMULATE|TRIM)\b", serialized)
    report = render_fixture_report(analysis)
    assert "Evidence Posture" in report
    assert "Uncertainty Range" in report
    assert "Missing Evidence" in report
```

- [ ] **Step 3: Run the two tests and witness failures**

Run: `python -m unittest tests.test_macro_pipeline -v`

Expected: FAIL because reports compare prose and the analyzer still returns recommendations.

- [ ] **Step 4: Integrate evidence assessments in the analyzer**

Call `SectorEvidenceEngine.generate_assessments`, store the result under `evidence_assessments`, and pass assessments into `raw_engine.build_raw_payload(evidence_assessments=...)`. Remove all post-processing that mutates `action`, `conviction`, or rationale. Return mechanical company results as `constituent_assessments`.

- [ ] **Step 5: Implement structured notable-state comparison**

Add frozen `NotableItem(key, fingerprint, body)`. Build fingerprints from macro regime fields, evidence posture plus material score bucket, sentiment classification, and Shiller classification. Load the newest prior `notable_state_YYYY-MM-DD.json`; compare fingerprints; render the current body for unchanged items and append the prior body only for changed fingerprints. Atomically write dated and latest state sidecars after report generation. Remove prose-derived comparison keys and full-body equality as the primary mechanism.

- [ ] **Step 6: Replace report action tables with evidence tables**

Render columns for sector, posture, score range, coverage, positive factors, negative factors, and missing evidence. Add this exact disclosure near the top and footer: `Deterministic outputs are research heuristics, not trade instructions or a validated strategy. WATCH and AVOID indicate research priority only.`

- [ ] **Step 7: Run Python integration tests and commit**

Run: `python -m unittest tests.test_macro_pipeline -v`

Expected: PASS, including the 39.93 → 40.62 unchanged regression.

```bash
git add analyzer.py reporter.py raw_data_engine.py tests/test_macro_pipeline.py
git commit -m "feat: publish evidence postures and semantic changes"
```

---

### Task 6: Point-in-Time Signal Ledger and Outcome Evaluation

**Files:**
- Create: `outcome_evaluation.py`
- Modify: `storage.py`
- Modify: `config.py`
- Modify: `analyzer.py`
- Modify: `main.py`
- Create: `tests/test_outcome_evaluation.py`

**Interfaces:**
- Produces: `SignalRecord`, `evaluate_signals(signals, prices, horizons=(21, 63, 126, 252), transaction_cost_bps=10) -> dict`, storage methods `save_signal_assessments` and `get_signal_assessments`, and CLI `python main.py evaluate`. Each signal stores `instrument` (the assessed sector ETF or basket) and `benchmark` (`SPY`).

- [ ] **Step 1: Write hand-calculated, no-look-ahead tests**

```python
def test_forward_return_starts_after_signal_and_subtracts_benchmark_and_cost():
    signals = [{"signal_date": "2026-01-02", "sector_group": "Technology (XLK)", "instrument": "XLK", "benchmark": "SPY", "posture": "WATCH", "score": 4.0}]
    prices = {
        "XLK": [("2026-01-02", 100.0), ("2026-02-02", 110.0)],
        "SPY": [("2026-01-02", 200.0), ("2026-02-02", 210.0)],
    }
    result = evaluate_signals(signals, prices, horizons=(1,), transaction_cost_bps=10)
    row = result["outcomes"][0]
    assert row["asset_return_pct"] == 10.0
    assert row["benchmark_return_pct"] == 5.0
    assert row["net_excess_return_pct"] == 4.9


def test_unmatured_horizon_is_excluded_and_labeled_insufficient():
    result = evaluate_signals(one_signal(), short_price_history(), horizons=(252,))
    assert result["outcomes"] == []
    assert result["summary"]["status"] == "INSUFFICIENT_SAMPLE"
    assert result["summary"]["sample_size"] == 0
```

- [ ] **Step 2: Run focused tests and witness missing-module failure**

Run: `python -m unittest tests.test_outcome_evaluation -v`

Expected: FAIL because `outcome_evaluation` does not exist.

- [ ] **Step 3: Implement deterministic outcome metrics**

Normalize prices by date, use the first available price on or after the signal date as entry, and the first price on or after each trading-day horizon target. Never use a price before the signal. Compute total return, SPY-relative excess return, one-way 10 bps research transaction cost, hit rate (`WATCH` succeeds when net excess return is positive; `AVOID` when negative), mean, median, and path maximum drawdown. Group results by horizon, posture, and integer score band. Label fewer than 30 matured observations or less than 365 elapsed days `INSUFFICIENT_SAMPLE`.

- [ ] **Step 4: Persist prospective signals and wire the CLI**

Add `SIGNALS_CSV` and `OUTCOMES_JSON` paths. Store factor snapshots and uncertainty as stable JSON. `MacroAnalyzer.generate_full_snapshot` appends current assessments after generation. `python main.py evaluate` loads the ledger, downloads only required tickers and SPY with yfinance from the earliest signal date, calls the pure evaluator, and atomically writes `output/outcome_evaluation.json`.

- [ ] **Step 5: Run evaluation and pipeline tests, then commit**

Run: `python -m unittest tests.test_outcome_evaluation tests.test_macro_pipeline -v`

Expected: PASS with no look-ahead and explicit small-sample labels.

```bash
git add outcome_evaluation.py storage.py config.py analyzer.py main.py tests/test_outcome_evaluation.py
git commit -m "feat: add point-in-time outcome evaluation"
```

---

### Task 7: Atomic CSV Storage and Source Health

**Files:**
- Create: `source_health.py`
- Modify: `storage.py`
- Modify: `config.py`
- Modify: `fetcher.py`
- Modify: `scheduler.py`
- Create: `tests/test_storage_resilience.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- Produces: `atomic_write_csv(path, frame)`, `SourceHealth`, `classify_source_error(message)`, `save_source_health`, and `get_latest_source_health`.

- [ ] **Step 1: Write failing atomicity and source-health tests**

```python
def test_atomic_write_keeps_original_when_replacement_fails(self):
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "observations.csv"
        path.write_text("value\n1\n", encoding="utf-8")
        with patch("storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                atomic_write_csv(path, pd.DataFrame([{"value": 2}]))
        self.assertEqual(path.read_text(encoding="utf-8"), "value\n1\n")


def test_fetch_failure_is_recorded_as_stale_machine_readable_health(tmp_path):
    storage = temp_storage(tmp_path)
    fetcher = MacroFetcher(storage=storage)
    fetcher.fetch_fred_series = lambda key, info: (0, "timed out")
    fetcher.fetch_all()
    health = storage.get_latest_source_health(source="FRED")
    assert health["status"] == "ERROR"
    assert health["error_category"] == "network"
    assert health["is_stale"] is True
```

- [ ] **Step 2: Run focused tests and witness failures**

Run: `python -m unittest tests.test_storage_resilience -v`

Expected: FAIL because atomic storage and source-health contracts do not exist.

- [ ] **Step 3: Centralize and version CSV schemas**

Define `CSV_SCHEMAS` in `storage.py` with an integer version and exact columns for indicators, observations, snapshots, news, run logs, source health, and signals. Initialization creates absent files through the atomic writer. Existing files gain missing columns in schema order without deleting unknown columns.

- [ ] **Step 4: Implement cooperative locks and atomic replacement**

Use a sibling `.lock` file and `fcntl.flock(..., LOCK_EX)` on macOS/Linux. Under the lock, reread the current CSV, apply the mutation, write a named temporary file in the same directory, flush, `os.fsync`, and `os.replace`. Clean temporary files in `finally`. Route every storage mutation through this helper. Keep the in-process `RLock` to prevent nested deadlock.

- [ ] **Step 5: Normalize and persist source health**

`SourceHealth` contains `source`, `fetch_key`, `observation_time`, `fetch_time`, `status`, `is_stale`, `record_count`, `error_category`, and `message`. Classify timeout/connection/DNS as `network`, missing payload/regex/XML/JSON as `parse`, range/schema errors as `validation`, and all other failures as `unknown`. `fetch_all` saves one row per fetch key; successful rows are `CURRENT`, and failures are `ERROR` plus stale when a prior observation remains. Scheduler includes counts by source status in its return value.

- [ ] **Step 6: Run storage and pipeline tests, then commit**

Run: `python -m unittest tests.test_storage_resilience tests.test_macro_pipeline -v`

Expected: PASS without partial-file corruption and with machine-readable health rows.

```bash
git add source_health.py storage.py config.py fetcher.py scheduler.py tests/test_storage_resilience.py tests/test_macro_pipeline.py
git commit -m "feat: harden csv writes and record source health"
```

---

### Task 8: Web Consumers, Documentation, and Workflow Hardening

**Files:**
- Create: `web/src/components/EvidenceAssessment.jsx`
- Create: `web/src/utils/evidencePresentation.js`
- Create: `web/src/utils/evidencePresentation.test.mjs`
- Modify: `web/src/App.jsx`
- Modify: `web/src/components/NewsFeed.jsx`
- Modify: `web/src/components/StockMatrix.jsx`
- Modify: `web/src/index.css`
- Modify: `extract_dashboard_data.py`
- Modify: `update_web_data.sh`
- Modify: `README.md`
- Modify: `docs/chatgpt_coworker_morning_prompt.md`
- Modify: `.gitignore`
- Modify: `.github/workflows/daily_macro.yml`
- Modify: `.github/workflows/chatgpt_coworker.yml`
- Modify: `tests/test_github_workflows.py`
- Modify: `tests/test_dashboard_history.py`

**Interfaces:**
- Web payload adds `evidence_assessments`, `source_health`, and `outcome_evaluation`.
- `buildAssessmentView(assessment) -> {tone, rangeLabel, coverageLabel, positives, negatives, missing}`.

- [ ] **Step 1: Write failing web presentation tests**

```javascript
test('buildAssessmentView exposes posture range coverage and missing evidence', () => {
  const view = buildAssessmentView({
    posture: 'WATCH',
    score_range: [2.1, 5.4],
    coverage_pct: 71.4,
    positive_factors: [{ factor_id: 'liquidity', explanation: 'Liquidity expanding.' }],
    negative_factors: [{ factor_id: 'real_yield', explanation: 'Real yields restrictive.' }],
    missing_evidence: [{ factor_id: 'valuation', missing_reason: 'Insufficient history.' }],
  });
  assert.deepEqual(view, {
    tone: 'positive',
    rangeLabel: '+2.1 to +5.4',
    coverageLabel: '71% evidence coverage',
    positives: ['Liquidity expanding.'],
    negatives: ['Real yields restrictive.'],
    missing: ['Valuation: Insufficient history.'],
  });
});
```

- [ ] **Step 2: Write failing workflow tests for immutable pins**

```python
def test_all_workflow_actions_are_pinned_to_full_commit_shas(self):
    for path in WORKFLOW_PATHS:
        content = path.read_text(encoding="utf-8")
        uses = re.findall(r"uses:\s+([^\s#]+)", content)
        assert uses
        assert all(re.search(r"@[0-9a-f]{40}$", item) for item in uses)
```

- [ ] **Step 3: Run tests and witness missing consumer/pin failures**

Run: `cd web && npm test`

Expected: FAIL because `evidencePresentation.js` does not exist.

Run: `python -m unittest tests.test_github_workflows tests.test_dashboard_history -v`

Expected: FAIL because workflows use mutable tags and exports lack evidence fields.

- [ ] **Step 4: Implement the evidence dashboard**

Render a top-level `EvidenceAssessment` section from `data.evidence_assessments` before trends. Each card displays the sector, posture badge, score range, coverage meter, positive and negative lists, missing-evidence list, and the research-only disclosure. Use accessible headings and text labels in addition to color. Update Stock Matrix to show focused peer cohort and relative status; update News Feed to show topic tags and `Uninterpreted context` without sentiment color.

- [ ] **Step 5: Export the unified payload and evaluation state**

Change dashboard export to merge the latest raw payload with the latest analysis evidence, source health, and `output/outcome_evaluation.json` when present. Update `update_web_data.sh` to copy the unified generated JSON and outcome evaluation. Tests assert the exported keys and null-safe behavior when no outcomes have matured.

- [ ] **Step 6: Correct documentation and secret ignores**

Document CSV storage and the legacy SQLite artifact, free-source fragility, evidence posture meanings, backtest limitations, source-health behavior, and exact `python main.py evaluate` usage. Add the research disclaimer to README, dashboard copy, report prompt, and generated report. Add `.env`, `.env.*`, `!.env.example`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `credentials*.json`, `secrets*.json`, and `.secrets/` to `.gitignore`.

- [ ] **Step 7: Pin GitHub Actions to resolved immutable SHAs**

Use these upstream tag resolutions and keep the readable tag as a comment:

```yaml
uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4
uses: actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b # v5
uses: actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda462b719fa # v3
uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e # v4
uses: stefanzweifel/git-auto-commit-action@b863ae1933cb653a53c021fe36dbb774e1fb9403 # v5
```

- [ ] **Step 8: Run web and workflow verification, then commit**

Run: `cd web && npm test && npm run lint && npm run build`

Expected: all tests pass, lint reports zero errors, and Vite exits successfully.

Run: `python -m unittest tests.test_github_workflows tests.test_dashboard_history -v`

Expected: PASS.

```bash
git add web/src/components/EvidenceAssessment.jsx web/src/utils/evidencePresentation.js web/src/utils/evidencePresentation.test.mjs web/src/App.jsx web/src/components/NewsFeed.jsx web/src/components/StockMatrix.jsx web/src/index.css extract_dashboard_data.py update_web_data.sh README.md docs/chatgpt_coworker_morning_prompt.md .gitignore .github/workflows/daily_macro.yml .github/workflows/chatgpt_coworker.yml tests/test_github_workflows.py tests/test_dashboard_history.py
git commit -m "feat: publish evidence dashboard and harden workflows"
```

---

### Task 9: Whole-System Migration Audit and Browser Verification

**Files:**
- Test: all Python and web tests

**Interfaces:**
- Produces: a generated report, unified `web/public/data.json`, built `web/dist`, and a browser-verified dashboard containing no deterministic trade directives.

- [ ] **Step 1: Search for stale architecture and directive language**

Run:

```bash
rg -n "DynamicMacroAnalyst|Gemini|SQLite database|\b(BUY|SELL|ACCUMULATE|TRIM)\b|conviction" --glob '!output/**' --glob '!web/public/reports/**' --glob '!docs/superpowers/**' .
```

Expected: no deterministic code or current consumer matches; historical reports and the design/plan are intentionally excluded.

- [ ] **Step 2: Run the complete Python test suite**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

- [ ] **Step 3: Generate fresh artifacts from available stored data**

Run: `python main.py report && python main.py evaluate && bash update_web_data.sh`

Expected: report, semantic sidecars, outcome evaluation, history, report manifest, and unified web data are generated without errors. The evaluation may correctly report `INSUFFICIENT_SAMPLE`.

- [ ] **Step 4: Run the complete web verification**

Run: `cd web && npm test && npm run lint && npm run build`

Expected: zero test failures, zero lint errors, and a successful production build.

- [ ] **Step 5: Inspect the production dashboard in a browser**

Serve `web/dist`, open it in the in-app browser, and verify at desktop and narrow viewport widths:

- Evidence Assessment appears and displays only `WATCH`, `NEUTRAL`, or `AVOID`.
- Score ranges, coverage, positive factors, negative factors, and missing evidence are readable.
- News is labeled uninterpreted context.
- Source freshness and research-only disclosure are visible.
- The report view renders the current Shiller value without falsely labeling same-classification numeric drift as changed.
- No console errors, broken links, horizontal overflow, or deterministic trade directives appear.

- [ ] **Step 6: Review the complete diff**

Run: `git diff --check && git status --short && git diff --stat origin/master...HEAD`

Expected: no whitespace errors and only scoped files.

If this step finds a defect, mark the originating task incomplete, dispatch a failing regression test and scoped fix for that task, re-run its review gate, and repeat Steps 1-6.

- [ ] **Step 7: Push and verify the remote branch**

Run: `git push origin HEAD:master`

Expected: push succeeds and `git ls-remote origin refs/heads/master` reports the local `HEAD` commit.
