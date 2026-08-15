# Level-Based Macro Quadrants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace direction-only macro quadrants with current policy and reserve-liquidity level classifications, while preserving momentum as context and adding a non-blocking market-consensus overlay.

**Architecture:** Add a pure `macro_regime.py` calculation module that accepts dated observations and returns structured policy, liquidity, momentum, corroboration, consensus, and quality states. `MacroAnalyzer` owns storage access and orchestration, while `MacroMatrixEngine` only maps actionable policy/liquidity states into the four quadrants. Storage, reports, recommendations, exported dashboard data, the web UI, and the repo-local analysis skill consume the same structured state.

**Tech Stack:** Python 3, pandas, unittest/pytest, CSV persistence, React 19, Vite, Node test runner, Markdown Codex skills.

## Global Constraints

- Quadrants describe current levels; 30-day and 90-day changes are momentum context and never select the quadrant.
- Situation 1 = `ACCOMMODATIVE + ABUNDANT`; Situation 2 = `ACCOMMODATIVE + SCARCE`; Situation 3 = `RESTRICTIVE + SCARCE`; Situation 4 = `RESTRICTIVE + ABUNDANT`.
- Neutral, stale, missing, or conflicting load-bearing inputs produce Situation 0 and no actionable quadrant.
- Real policy rate is `DFF - core PCE YoY`; policy gap is `real policy rate - NY Fed HLW r-star`.
- Policy is `RESTRICTIVE` above `+0.50` percentage point, `ACCOMMODATIVE` below `-0.50`, and `NEUTRAL` at and between the boundaries.
- Policy freshness limits are DFF 7 days, core PCE 75 days, and r-star publication 180 days.
- The historical real-policy percentile uses the trailing 10 years, requires at least 5 years, and is context only.
- Reserve liquidity is `Fed assets - TGA - RRP`, in billions of dollars, normalized as `100 * reserve liquidity / nominal GDP`.
- Liquidity history is weekly-aligned, trailing 10 years excluding the current observation, and requires at least 5 years and 200 observations.
- Liquidity is `ABUNDANT` at or above the 60th percentile, `SCARCE` at or below the 40th percentile, and `NEUTRAL` between them.
- Liquidity output reports the current value, median, 40th and 60th percentiles, current percentile rank, sample start/end/count, and freshness.
- A 5-day mean `EFFR - IORB >= -0.02` percentage point is a reserve-pressure flag; `SOFR - IORB >= +0.10` percentage point is a funding-pressure flag.
- One corroboration flag sets quality to `PARTIAL`; two set quality to `INDETERMINATE_CONFLICT` and withhold the quadrant. Missing corroboration lowers confidence but does not change the core classification.
- Freshness limits are Fed assets 14 days, TGA 14 days, RRP 7 days, nominal GDP 120 days, EFFR 7 days, IORB 7 days, and SOFR 7 days.
- Normalized-liquidity 30/90-day momentum is `IMPROVING` above `+0.05` percentage point of GDP, `DETERIORATING` below `-0.05`, otherwise `STABLE`.
- Policy-gap 30/90-day momentum is `EASING` below `-0.10` percentage point, `TIGHTENING` above `+0.10`, otherwise `STABLE`.
- Consensus uses the NY Fed Survey of Market Expectations median path at the closest available horizon to 6 months, restricted to 3-9 months.
- Consensus policy is `EASING` when expected DFF is at least 0.10 percentage point below current, `TIGHTENING` when at least 0.10 above, otherwise `STABLE`.
- Consensus balance sheet is `EXPANDING` or `CONTRACTING` at changes of at least `+0.5%` or `-0.5%`, otherwise `STABLE`; label it balance-sheet consensus, not net-liquidity consensus.
- Consensus older than 120 days is stale; missing or stale consensus never blocks the current quadrant.
- Persisted snapshots remain backward-readable when old rows lack new columns.
- Reports and the web UI present sections in this order: Current State, Momentum, Consensus, Interpretation, Data Quality.
- Recommendations consume structured states and must not infer regimes by searching display strings.
- The repo-local skill stays under 500 lines, removes direction-only quadrant rules, and includes the “high but falling” example.
- Follow strict TDD: each production behavior is preceded by a focused failing test, the failure is observed, then the minimum implementation is added.
- Preserve unrelated work and do not implement the separate evidence-analysis redesign in this branch.

---

### Task 1: Pure Policy-Level Classification

**Files:**
- Create: `macro_regime.py`
- Create: `tests/test_macro_regime.py`

**Interfaces:**
- Consumes: pandas DataFrames with `date` and `value` columns plus an explicit `as_of: pd.Timestamp`.
- Produces: `classify_policy_level(dff, core_pce, rstar, as_of) -> dict` and `classify_delta(delta, positive_label, negative_label, stable_label, threshold) -> str`.

- [ ] **Step 1: Write failing policy-level tests**

```python
import pandas as pd
from macro_regime import classify_policy_level

def series(*pairs):
    return pd.DataFrame(pairs, columns=["date", "value"]).assign(date=lambda d: pd.to_datetime(d.date))

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

def test_policy_boundaries_are_neutral_and_stale_inputs_withhold():
    # Use precomputed inflation rates here so fixtures independently imply gaps of +/-0.50.
    restrictive_edge = classify_policy_level.from_rates(4.0, 3.0, 0.5)
    accommodative_edge = classify_policy_level.from_rates(2.0, 2.0, 0.5)
    assert restrictive_edge["state"] == "NEUTRAL"
    assert accommodative_edge["state"] == "NEUTRAL"
```

Replace the illustrative `.from_rates` calls with a public pure helper `classify_policy_gap(real_policy_rate, rstar)` if that keeps the production interface simpler; keep the literal boundary assertions.

- [ ] **Step 2: Run the focused tests and observe the missing-module/function failure**

Run: `.venv/bin/pytest tests/test_macro_regime.py -q`

Expected: FAIL because `macro_regime` does not exist.

- [ ] **Step 3: Implement policy calculation, freshness, percentile context, and momentum**

```python
POLICY_GAP_THRESHOLD_PP = 0.50

def classify_policy_gap(real_policy_rate: float, rstar: float) -> str:
    gap = real_policy_rate - rstar
    if gap > POLICY_GAP_THRESHOLD_PP:
        return "RESTRICTIVE"
    if gap < -POLICY_GAP_THRESHOLD_PP:
        return "ACCOMMODATIVE"
    return "NEUTRAL"
```

Calculate core-PCE YoY from the latest index and an observation 12 months earlier, reject stale/missing inputs, and return dates, ages, values, `real_policy_rate`, `rstar`, `policy_gap`, `historical_percentile`, `momentum_30d`, `momentum_90d`, `state`, `quality`, and `reasons`. Historical context must be `None` with an explicit reason when fewer than five years are present.

- [ ] **Step 4: Add and pass literal boundary, freshness, history, and momentum cases**

Run: `.venv/bin/pytest tests/test_macro_regime.py -q`

Expected: PASS for restrictive/accommodative/neutral boundaries, high-but-easing classification, stale data, insufficient history, and exact 30/90-day thresholds.

- [ ] **Step 5: Commit**

```bash
git add macro_regime.py tests/test_macro_regime.py
git commit -m "feat: classify policy by current real-rate level"
```

---

### Task 2: Pure Liquidity-Level Classification and Corroboration

**Files:**
- Modify: `macro_regime.py`
- Modify: `tests/test_macro_regime.py`

**Interfaces:**
- Consumes: dated Fed assets, TGA, RRP, nominal GDP, EFFR, IORB, and SOFR observations with each series kept in its documented source units.
- Produces: `classify_liquidity_level(fed_assets, tga, rrp, nominal_gdp, effr, iorb, sofr, as_of) -> dict`.

- [ ] **Step 1: Write failing liquidity tests with hand-derived fixtures**

```python
def dated(values, end, freq):
    dates = pd.date_range(end=pd.Timestamp(end), periods=len(values), freq=freq)
    return pd.DataFrame({"date": dates, "value": values})

def liquidity_fixture(effr=4.33, iorb=4.40, sofr=4.36):
    normalized_history = [10.0 + index * (10.0 / 268.0) for index in range(269)]
    normalized_values = normalized_history + [19.5]
    gdp = 30_000.0
    reserve_values = [value * gdp / 100.0 for value in normalized_values]
    return {
        "fed_assets": dated([(value + 1_000.0) * 1_000.0 for value in reserve_values], "2026-08-14", "7D"),
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
    out = classify_liquidity_level(**liquidity_fixture(effr=4.39, iorb=4.40, sofr=4.51))
    assert out["core_state"] in {"ABUNDANT", "SCARCE"}
    assert out["state"] is None
    assert out["quality"] == "INDETERMINATE_CONFLICT"
```

Expand the ellipsis before running: use 201 weekly historical observations with literal normalized values, and five daily EFFR/IORB/SOFR observations whose spreads are independently hand-checked.

- [ ] **Step 2: Run focused tests and observe failures for the absent classifier**

Run: `.venv/bin/pytest tests/test_macro_regime.py -q`

Expected: FAIL because `classify_liquidity_level` is undefined.

- [ ] **Step 3: Implement weekly alignment, normalization, percentiles, momentum, and corroboration**

```python
def reserve_liquidity_billions(fed_assets_millions, tga_millions, rrp_billions):
    return fed_assets_millions / 1000.0 - tga_millions / 1000.0 - rrp_billions

def classify_liquidity_percentile(rank: float) -> str:
    if rank >= 60.0:
        return "ABUNDANT"
    if rank <= 40.0:
        return "SCARCE"
    return "NEUTRAL"
```

Use backward-looking as-of joins, exclude the current observation from percentile thresholds, require both 200 weeks and five years, enforce series freshness, preserve `core_state`, and only null `state` for a two-flag conflict.

- [ ] **Step 4: Pass boundary, stale, missing, conflict, and high-but-falling tests**

Run: `.venv/bin/pytest tests/test_macro_regime.py -q`

Expected: PASS, including ranks exactly 40 and 60, one pressure flag yielding `PARTIAL`, missing corroboration lowering confidence without changing state, and GDP normalization.

- [ ] **Step 5: Commit**

```bash
git add macro_regime.py tests/test_macro_regime.py
git commit -m "feat: classify reserve liquidity by historical level"
```

---

### Task 3: Consensus Overlay and Source Configuration

**Files:**
- Modify: `config.py`
- Create: `consensus.py`
- Create: `tests/test_consensus.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- Consumes: survey records shaped as `{survey_date, horizon_months, expected_dff, expected_fed_assets}`.
- Produces: `interpret_consensus(records, current_dff, current_fed_assets, as_of) -> dict`; configured FRED keys `nominal_gdp`, `iorb`, and `sofr`.

- [ ] **Step 1: Write failing source and consensus tests**

```python
def test_consensus_selects_closest_horizon_to_six_months_and_is_non_blocking():
    records = [
        {"survey_date": "2026-07-01", "horizon_months": 3, "expected_dff": 4.3, "expected_fed_assets": 7000},
        {"survey_date": "2026-07-01", "horizon_months": 7, "expected_dff": 4.0, "expected_fed_assets": 7040},
    ]
    out = interpret_consensus(records, 4.25, 7000, pd.Timestamp("2026-08-15"))
    assert out["selected_horizon_months"] == 7
    assert out["policy_direction"] == "EASING"
    assert out["balance_sheet_direction"] == "EXPANDING"
    assert out["blocks_quadrant"] is False

def test_consensus_older_than_120_days_is_stale():
    records = [{"survey_date": "2026-03-01", "horizon_months": 6, "expected_dff": 4.0, "expected_fed_assets": 7000}]
    out = interpret_consensus(records, 4.25, 7000, pd.Timestamp("2026-08-15"))
    assert out["quality"] == "STALE"
    assert out["blocks_quadrant"] is False
```

- [ ] **Step 2: Run focused tests and observe failures**

Run: `.venv/bin/pytest tests/test_consensus.py tests/test_macro_pipeline.py -q`

Expected: FAIL for missing module and absent active FRED series.

- [ ] **Step 3: Configure sources and implement consensus interpretation**

Add `GDP` as nominal GDP in billions, `IORB`, and `SOFR` to `FRED_SERIES` and `ACTIVE_FRED_SERIES_KEYS`. Keep existing `GDPC1` under a distinct real-GDP key if other consumers need it. In `consensus.py`, filter horizons to 3-9 months, select minimum absolute distance from six months with the nearer/lower horizon as deterministic tie-break, apply the exact policy and balance-sheet thresholds, and return `UNAVAILABLE`/`STALE` without blocking.

- [ ] **Step 4: Run source and consensus tests to green**

Run: `.venv/bin/pytest tests/test_consensus.py tests/test_macro_pipeline.py -q`

Expected: PASS for horizon selection, threshold boundaries, stale/missing inputs, units, and active source enumeration.

- [ ] **Step 5: Commit**

```bash
git add config.py consensus.py tests/test_consensus.py tests/test_macro_pipeline.py
git commit -m "feat: add market consensus and regime data sources"
```

---

### Task 4: Analyzer, Matrix, and Backward-Compatible Snapshot Integration

**Files:**
- Modify: `analyzer.py`
- Modify: `macro_matrix.py`
- Modify: `storage.py`
- Modify: `raw_data_engine.py`
- Modify: `tests/test_macro_pipeline.py`

**Interfaces:**
- Consumes: Task 1/2 regime dictionaries and Task 3 consensus dictionary.
- Produces: `MacroAnalyzer.analyze_macro_regime() -> dict`; `MacroMatrixEngine.classify_situation(policy_state, liquidity_state, *, quality, context) -> dict`; expanded snapshot columns and structured result keys `current_state`, `momentum`, `consensus`, `data_quality`.

- [ ] **Step 1: Replace direction-only matrix tests with failing level-state tests**

```python
def test_matrix_maps_level_states_and_never_uses_momentum():
    matrix = MacroMatrixEngine()
    assert matrix.classify_situation("ACCOMMODATIVE", "ABUNDANT", quality="OK", context={})["situation_id"] == 1
    assert matrix.classify_situation("ACCOMMODATIVE", "SCARCE", quality="OK", context={})["situation_id"] == 2
    assert matrix.classify_situation("RESTRICTIVE", "SCARCE", quality="OK", context={})["situation_id"] == 3
    assert matrix.classify_situation("RESTRICTIVE", "ABUNDANT", quality="OK", context={})["situation_id"] == 4

def test_matrix_withholds_neutral_or_conflicted_inputs():
    assert MacroMatrixEngine().classify_situation("NEUTRAL", "ABUNDANT", quality="OK", context={})["situation_id"] == 0
    assert MacroMatrixEngine().classify_situation("RESTRICTIVE", None, quality="INDETERMINATE_CONFLICT", context={})["situation_id"] == 0
```

Add an analyzer fixture where liquidity is above its 60th percentile but its 30-day momentum is deteriorating; assert Situation 4 when policy is restrictive.

- [ ] **Step 2: Run focused integration tests and observe signature/assertion failures**

Run: `.venv/bin/pytest tests/test_macro_pipeline.py -q`

Expected: FAIL because the old matrix accepts rate direction and 30-day liquidity change.

- [ ] **Step 3: Integrate the pure regime module and rewrite the matrix boundary**

`analyze_macro_regime` loads the complete required series, calls the pure classifiers, loads optional consensus from a storage-backed/configurable provider, derives combined quality, then passes only `policy["state"]` and `liquidity["state"]` to the matrix. Keep CPI, Sahm, yield curve, M2, and sector lists as interpretation context, never as axis classifiers.

- [ ] **Step 4: Expand snapshot persistence without breaking old rows**

Add columns for policy state/gap/r-star, liquidity state/normalized value/percentile/thresholds, 30/90-day momentum, consensus directions/date/quality, quadrant quality, and input ages. When saving, union existing and new columns; when reading, tolerate absent columns and return `None`/empty values rather than raising.

- [ ] **Step 5: Pass matrix, analyzer, raw-payload, and old-snapshot tests**

Run: `.venv/bin/pytest tests/test_macro_pipeline.py tests/test_dashboard_history.py -q`

Expected: PASS, including all four quadrants, Situation 0 paths, high-but-falling, conflict withholding, optional consensus, and a legacy snapshot CSV containing only the old header.

- [ ] **Step 6: Commit**

```bash
git add analyzer.py macro_matrix.py storage.py raw_data_engine.py tests/test_macro_pipeline.py tests/test_dashboard_history.py
git commit -m "refactor: drive macro quadrants from current levels"
```

---

### Task 5: Structured Recommendations and Ordered Report Output

**Files:**
- Modify: `recommendations.py`
- Modify: `reporter.py`
- Modify: `extract_dashboard_data.py`
- Modify: `tests/test_macro_pipeline.py`
- Modify: `tests/test_dashboard_history.py`

**Interfaces:**
- Consumes: `analysis["macro_regime"]` plus matrix sector metadata.
- Produces: recommendations based on `policy.state`, `liquidity.state`, and `quadrant.situation_id`; report/export sections in the required order.

- [ ] **Step 1: Write failing recommendation and report behavior tests**

```python
def test_recommendations_do_not_treat_abundant_but_falling_as_scarce():
    regime = {"policy": {"state": "RESTRICTIVE"}, "liquidity": {"state": "ABUNDANT", "momentum_30d": "DETERIORATING"}}
    recs = engine.generate_recommendations(summary, credit, valuations, ai, news, quadrant, regime)
    assert any(rec["sector_group"] == "Energy (XLE)" for rec in recs)

def test_report_sections_are_in_decision_order():
    report = self.reporter.generate_markdown_report(analysis)
    headings = [report.index(name) for name in ["Current State", "Momentum", "Consensus", "Interpretation", "Data Quality"]]
    assert headings == sorted(headings)
```

- [ ] **Step 2: Run focused tests and observe failures from old string/direction behavior**

Run: `.venv/bin/pytest tests/test_macro_pipeline.py tests/test_dashboard_history.py -q`

Expected: FAIL because recommendations/reporting do not accept or render the structured regime.

- [ ] **Step 3: Update recommendations, Markdown/console reporting, and dashboard export**

Render exact current values, thresholds, dates, sample window/count, 30/90-day momentum, consensus with a “balance-sheet consensus” label, interpretation, and quality/reasons. Remove all decisions based on substring checks such as `"expanding" in liquidity_regime.lower()`; branch on structured enum values instead.

- [ ] **Step 4: Pass focused and full Python tests**

Run: `.venv/bin/pytest -q`

Expected: PASS with the ordered report and backward-compatible dashboard history.

- [ ] **Step 5: Commit**

```bash
git add recommendations.py reporter.py extract_dashboard_data.py tests/test_macro_pipeline.py tests/test_dashboard_history.py
git commit -m "feat: report level regime with momentum and consensus"
```

---

### Task 6: Web Dashboard and Framework Explanation

**Files:**
- Modify: `web/src/components/CheatSheet.jsx`
- Modify: `web/src/components/BigUpdate.jsx`
- Modify: `web/src/utils/descriptions.js`
- Modify: `web/src/utils/dashboardPresentation.js`
- Modify: `web/src/utils/dashboardPresentation.test.mjs`
- Modify: `web/src/index.css` only if the five ordered groups need layout support.

**Interfaces:**
- Consumes: exported `macro_regime` and `macro_situation` JSON.
- Produces: a dashboard card ordered Current State, Momentum, Consensus, Interpretation, Data Quality; level-based cheat sheet copy.

- [ ] **Step 1: Add a failing presentation test for the five ordered groups**

```javascript
test('presents level state separately from momentum and consensus', () => {
  const view = buildRegimePresentation(fixture)
  assert.deepEqual(view.sections.map(section => section.label), [
    'Current State', 'Momentum', 'Consensus', 'Interpretation', 'Data Quality'
  ])
  assert.equal(view.sections[0].value.includes('Restrictive + Abundant'), true)
  assert.equal(view.sections[1].value.includes('Deteriorating'), true)
})
```

- [ ] **Step 2: Run web tests and observe the missing presenter failure**

Run: `cd web && npm test`

Expected: FAIL because `buildRegimePresentation` is absent.

- [ ] **Step 3: Implement the presenter and dashboard card**

Keep numeric formatting in the pure presentation utility. Show unavailable/stale consensus explicitly without changing the Current State. Include threshold/tooltips that explain history-relative levels and update `CheatSheet.jsx` from “cutting/raising × expanding/contracting” to “accommodative/restrictive × abundant/scarce.”

- [ ] **Step 4: Run web test, lint, and production build**

Run: `cd web && npm test && npm run lint && npm run build`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add web/src
git commit -m "feat: show level-based macro regime on dashboard"
```

---

### Task 7: Update and Pressure-Test the Repo-Local Analysis Skill

**Files:**
- Modify: `.agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md`
- Modify: `README.md`
- Modify: `docs/chatgpt_coworker_morning_prompt.md`
- Create: `.agents/skills/defiant-gatekeeper-macro-news-analysis/evals/high-but-falling.md`

**Interfaces:**
- Consumes: the production regime schema and thresholds implemented in Tasks 1-6.
- Produces: skill instructions under 500 lines that cause an agent to classify current level first, momentum second, and consensus as a non-blocking overlay.

- [ ] **Step 1: Record a RED baseline skill evaluation**

Run a fresh Luna-max subagent without the revised skill on this scenario and save its response in the SDD report: “Policy gap is +0.80 pp and falling; normalized reserve liquidity is at the 75th historical percentile and fell 0.10 pp of GDP over 30 days; survey consensus expects lower DFF and a stable Fed balance sheet. Classify the current quadrant and describe the outlook.”

Expected RED behavior: it selects a quadrant from “falling/easing” directions, conflates consensus with current state, or fails to state Situation 4 as current while separately describing easing/deteriorating momentum.

- [ ] **Step 2: Rewrite the skill with the production rules and example**

The skill must say, in operational order:

```markdown
1. Classify current policy level from the real-policy gap.
2. Classify current reserve-liquidity level from its historical percentile.
3. Select the quadrant only from those two current states.
4. Report 30-day and 90-day momentum separately.
5. Report NY Fed SME consensus separately; it never changes the current quadrant.
```

Add the high-but-falling example with the expected result: `RESTRICTIVE + ABUNDANT = Situation 4`, policy momentum easing, liquidity momentum deteriorating, consensus easing/stable.

- [ ] **Step 3: Run a GREEN skill evaluation with a fresh Luna-max subagent**

Give the same scenario to a fresh agent with access to the revised skill. Require it to name Situation 4, separate both momentum signals, separate consensus, and mention data-quality gating. Append the response and pass/fail rubric to the SDD report.

- [ ] **Step 4: Validate skill structure and documentation consistency**

Run:

```bash
python /Users/bronson/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/defiant-gatekeeper-macro-news-analysis
wc -l .agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md
rg -n "Cutting vs Raising|Expanding vs Contracting|30-day.*quadrant" README.md docs .agents/skills/defiant-gatekeeper-macro-news-analysis
```

Expected: validator exits 0; skill is below 500 lines; no prose still defines direction as a quadrant axis.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/defiant-gatekeeper-macro-news-analysis README.md docs/chatgpt_coworker_morning_prompt.md
git commit -m "docs: align macro skill with level-based quadrants"
```

---

### Task 8: End-to-End Verification and Controlled Pipeline Run

**Files:**
- Modify only files needed to fix failures directly caused by Tasks 1-7.
- Verify: `output/latest_report.md`, `output/latest_raw_payload.json`, `web/public/data.json` or the repository's generated dashboard-data location.

**Interfaces:**
- Consumes: the complete implementation.
- Produces: passing suites and one inspected report/dashboard payload that preserve the quadrant/momentum/consensus separation.

- [ ] **Step 1: Run the complete automated verification set**

Run:

```bash
.venv/bin/pytest -q
cd web && npm test && npm run lint && npm run build
```

Expected: all commands exit 0.

- [ ] **Step 2: Run the controlled local pipeline with cached fixtures/data**

Use the repository's existing non-network entry point or test fixture to generate one analysis result. Do not overwrite user-owned historical output unless the existing command is explicitly designed to refresh generated artifacts.

- [ ] **Step 3: Inspect semantic invariants in the generated result**

Assert or manually verify:

```text
quadrant depends only on policy.state + liquidity.state
30d/90d momentum is displayed but cannot change situation_id
missing/stale consensus leaves situation_id unchanged
two corroboration flags produce situation_id 0
report groups appear as Current State, Momentum, Consensus, Interpretation, Data Quality
```

- [ ] **Step 4: Commit any verification-driven fixes**

```bash
git add analyzer.py macro_matrix.py storage.py raw_data_engine.py recommendations.py reporter.py extract_dashboard_data.py web/src
git commit -m "fix: complete level-regime integration"
```

If no fixes are required, do not create an empty commit.
