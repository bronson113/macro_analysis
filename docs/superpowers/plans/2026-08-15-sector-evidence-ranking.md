# Sector Evidence Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Daily Brief's non-discriminating evidence tables with a selective sector ranking and concise no-signal/coverage conclusions.

**Architecture:** Keep scoring, payloads, storage, and evaluation unchanged. Add defensive Markdown-presentation helpers to `MacroReporter`, route `generate_markdown_report` through them, and collapse neutral constituent output without changing differentiated constituent tables. Update the repository macro-analysis skill so future report generation follows the same presentation gate.

**Tech Stack:** Python 3, `unittest`/pytest, Markdown report generation, Codex skill Markdown

## Global Constraints

- A usable sector assessment has a non-empty `sector_group`, finite numeric `score`, two finite numeric `score_range` bounds with `low <= high`, and finite `coverage_pct` in `[0, 100]`.
- Sector differentiation requires at least one usable `WATCH` or `AVOID` posture and a highest-minus-lowest score spread of at least `4.0` points.
- When the gate fails, render `No meaningful sector differentiation from current evidence.` and no sector ranking table.
- When the gate passes, render at most three stronger and three weaker sectors, never duplicate a sector, preserve stable input order for ties, and disclose additional boundary ties.
- Render at most two current non-zero leading factors using observed value, unit, signed weighted contribution, and date; do not substitute generic methodology prose.
- Keep all evidence calculations, posture thresholds, payloads, storage, prospective ledgers, and outcome evaluation unchanged.
- Keep the removed React Evidence Assessments section removed; terminal output is out of scope.
- Use only research language. Do not add `best`, `worst`, `buy`, `sell`, `overweight`, `underweight`, forecasts, allocations, or personalized investment advice.
- Do not regenerate, stage, or commit daily files under `data/`, `output/`, or `web/public/`.
- Work directly on `master` as explicitly requested by the user; do not create a feature branch or worktree.

---

### Task 1: Render a selective sector evidence ranking

**Files:**
- Create: `tests/test_reporter_evidence_ranking.py`
- Modify: `reporter.py`

**Interfaces:**
- Consumes: `analysis["evidence_assessments"]`, preserving the existing assessment dictionaries.
- Produces: `MacroReporter._sector_evidence_section(assessments: Any) -> str`, a complete `## 5. Sector Evidence Ranking` Markdown section or an empty string when the input list is empty.
- Produces: focused private helpers for defensive normalization, dominant missing-reason selection, leading-factor formatting, and stable strongest/weakest selection.

- [ ] **Step 1: Write failing no-signal and malformed-input tests**

Create `tests/test_reporter_evidence_ranking.py`. Build a minimal `analysis` fixture accepted by `MacroReporter.generate_markdown_report`, use a temporary output directory, and add tests with these assertions:

```python
assert "## 5. Sector Evidence Ranking" in content
assert "No meaningful sector differentiation from current evidence." in content
assert "Usable assessments: `2`" in content
assert "Score spread: `5.0` points" in content
assert "Valuation percentile is unavailable. (`2` of `2` sectors)" in content
assert "| Relative evidence |" not in content
assert "Sector Evidence Assessments" not in content
```

Use two valid all-neutral inputs with scores `1.0` and `-4.0`, ranges `[-10.0, 10.0]`, coverage `85.7`, and the same missing valuation reason. Include malformed non-dict entries and assessments with invalid score/range/coverage fields; assert report generation succeeds and counts only the two valid assessments.

- [ ] **Step 2: Run the focused no-signal test and verify RED**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_reporter_evidence_ranking.py`

Expected: FAIL because the report still renders `## 5. Sector Evidence Assessments` and its full table.

- [ ] **Step 3: Write failing differentiated-ranking and factor-format tests**

Add a fixture with at least seven usable sectors:

- two sectors scoring `6.0` with `WATCH`, including current `real_yield` and `macro_quadrant` factors;
- two middle neutral sectors;
- three sectors scoring `-3.0`, `-5.0`, and `-5.0`, with at least one `AVOID`;
- one additional sector tied at the stronger or weaker selection boundary so the selection cap produces the exact phrase `Additional sectors tied at this score: 1`.

Assert:

```python
assert "| Relative evidence | Sector / Group | Instrument | Posture | Score | Coverage | Leading observed factors | Primary missing input |" in content
assert content.count("Stronger evidence") <= 3
assert content.count("Weaker evidence") <= 3
assert "10Y real yield: 2.44% (-1.0; 2026-08-14)" in content
assert "Additional sectors tied at this score: `1`" in content
assert "relative research evidence, not an allocation recommendation" in content
assert "score is not a forecast return" in content
assert "Macro quadrant is favorable, unfavorable, or neutral" not in content
```

Also assert each selected sector name appears exactly once in the ranking section and equal-score rows contain `(tied)` in the relative-evidence label.

- [ ] **Step 4: Implement defensive sector-ranking helpers**

In `reporter.py`, import `Counter` from `collections` and `isfinite` from `math`.

Add private `MacroReporter` helpers with these responsibilities:

```python
@staticmethod
def _finite_float(value: Any) -> Optional[float]:
    """Return a finite float, excluding booleans and malformed values."""

@classmethod
def _usable_sector_assessments(cls, assessments: Any) -> List[Dict[str, Any]]:
    """Return copied, normalized assessments with `_input_index` and numeric fields."""

@staticmethod
def _missing_reason(item: Any) -> Optional[str]:
    """Return a non-empty missing reason from a string or factor dictionary."""

@classmethod
def _dominant_missing_reason(cls, assessments: Iterable[Dict[str, Any]]) -> tuple[Optional[str], int, int]:
    """Return reason, number of assessments containing it, and assessment count."""

@classmethod
def _format_leading_factors(cls, assessment: Dict[str, Any]) -> str:
    """Format at most two current non-zero factors by absolute weighted contribution."""

@classmethod
def _sector_evidence_section(cls, assessments: Any) -> str:
    """Render the gated sector evidence section without changing assessment data."""
```

`_finite_float` must reject `True`/`False` and values for which `math.isfinite(float(value))` is false.

`_usable_sector_assessments` must require the exact usable-assessment contract from Global Constraints. Normalize posture to uppercase, retain a stable `_input_index`, and never mutate the supplied dictionaries.

`_dominant_missing_reason` counts a reason at most once per assessment. Resolve equal counts by first appearance in the input. Return `(None, 0, assessment_count)` when no reason exists.

For `_format_leading_factors`, combine factor dictionaries from `assessment["factors"]` when present; otherwise combine `positive_factors` and `negative_factors`. Keep only `quality == "current"` factors with finite non-zero `contribution` and positive finite `weight`. Sort by descending `abs(contribution * weight)` and stable factor order. Render no more than two, separated by `<br>`. Use these labels when present, otherwise title-case `factor_id`:

```python
{
    "macro_quadrant": "Macro quadrant",
    "liquidity": "Reserve liquidity",
    "credit": "High-yield credit spread",
    "valuation_percentile": "Valuation percentile",
    "real_yield": "10Y real yield",
    "housing": "Housing growth",
    "data_quality": "Data quality",
}
```

Format `percent` as `%`, `percent_yoy` as `% YoY`, and otherwise append a non-empty unit separated by a space unless the unit is `regime`, `quality`, `unknown`, or `None`. Format the weighted contribution with a sign and one decimal place. Add `; YYYY-MM-DD` when `observed_at` is present. Return `No differentiating observed factor` when none qualifies.

`_sector_evidence_section` must:

1. Return `""` for an empty/non-list input to preserve current behavior.
2. Compute usable assessments and score spread.
3. Apply both meaningful-differentiation conditions from Global Constraints.
4. On failure, render the exact conclusion plus usable count, score spread (`Unavailable` with fewer than two usable assessments), and dominant missing reason/count when present, followed by `RESEARCH_DISCLOSURE`.
5. On success, sort stronger candidates by `(-score, _input_index)` and weaker candidates by `(score, _input_index)`. Select up to three stronger, then up to three weaker excluding already selected `sector_group` values.
6. Mark a row label `(tied)` when more than one usable assessment has that row's score.
7. When unselected candidates share a selected side's boundary score, append `Additional sectors tied at this score: \`N\`` for that side. Emit the phrase once per side that has overflow.
8. Render instrument, normalized posture, signed one-decimal score, one-decimal coverage percentage, leading-factor summary, and primary missing reason (`None identified` fallback) through `md_cell`.
9. End with: `This ordering is relative research evidence, not an allocation recommendation; the score is not a forecast return.` and `RESEARCH_DISCLOSURE`.

Replace the inline sector evidence table builder in `generate_markdown_report` with:

```python
evidence_section_md = self._sector_evidence_section(evidence_assessments)
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_reporter_evidence_ranking.py`

Expected: all Task 1 tests PASS.

- [ ] **Step 6: Run reporter regression tests**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_macro_pipeline.py -k "report or notable"`

Expected: PASS. If an existing assertion names `Sector Evidence Assessments`, update it only when its tested fixture now reaches the new no-signal output; retain assertions that differentiated fixtures include their sector names and research disclosure.

- [ ] **Step 7: Commit Task 1**

```bash
git add reporter.py tests/test_reporter_evidence_ranking.py tests/test_macro_pipeline.py
git commit -m "feat: present meaningful sector evidence rankings"
```

---

### Task 2: Collapse non-differentiated constituent evidence

**Files:**
- Modify: `tests/test_reporter_evidence_ranking.py`
- Modify: `reporter.py`

**Interfaces:**
- Consumes: `analysis["constituent_assessments"]`, preserving its dictionaries.
- Produces: `MacroReporter._constituent_evidence_section(assessments: Any) -> str`, either the existing differentiated table, a concise neutral coverage section, or an empty string.

- [ ] **Step 1: Write failing constituent coverage tests**

Add a test containing three all-neutral constituent assessments with empty `evidence`, missing-history strings, and no directional factor lists. Assert:

```python
assert "## 6. Constituent Evidence Coverage" in content
assert "Constituents evaluated: `3`" in content
assert "no company-level differentiation is supported yet" in content
assert "Only 11 valid historical relative observations are available; 60 are required. (`3` of `3` constituents)" in content
assert "| Ticker | Peer Cohort |" not in content
```

Add a second test with one `WATCH` constituent and non-empty `evidence`; assert the existing `## 6. Constituent Evidence Assessments` table, ticker, relative valuation status, evidence, and missing evidence remain present.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_reporter_evidence_ranking.py`

Expected: the neutral-coverage test FAILS because the full constituent table is still rendered.

- [ ] **Step 3: Implement constituent presentation helper**

Add:

```python
@classmethod
def _constituent_evidence_section(cls, assessments: Any) -> str:
    """Collapse non-differentiated constituent evidence to a coverage note."""
```

Return `""` for empty/non-list input. Treat the set as differentiated when any dictionary assessment has posture `WATCH` or `AVOID`, a non-empty `evidence`, a non-empty `positive_factors`, or a non-empty `negative_factors`.

When no differentiation exists, render `## 6. Constituent Evidence Coverage`, the exact evaluated count, the dominant missing reason/count using the same reason semantics as Task 1, and `Current inputs do not support company-level differentiation yet.` Do not render a table.

When differentiation exists, render the current `## 6. Constituent Evidence Assessments` introduction and table defensively, skipping non-dictionary entries and preserving all current columns and research language.

Replace the inline constituent section builder in `generate_markdown_report` with:

```python
constituent_section_md = self._constituent_evidence_section(constituent_assessments)
```

- [ ] **Step 4: Run focused and existing constituent tests and verify GREEN**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_reporter_evidence_ranking.py tests/test_macro_pipeline.py -k "constituent or evidence"`

Expected: PASS.

- [ ] **Step 5: Run the complete Python suite**

Run: `PYTHONPATH=. .venv/bin/pytest -q`

Expected: all tests PASS. Existing pandas fragmentation warnings are permitted; new failures or warnings from this change are not.

- [ ] **Step 6: Commit Task 2**

```bash
git add reporter.py tests/test_reporter_evidence_ranking.py tests/test_macro_pipeline.py
git commit -m "fix: collapse neutral constituent evidence"
```

---

### Task 3: Align and validate the macro-analysis skill

**Files:**
- Modify: `.agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md`

**Interfaces:**
- Consumes: the approved selective-ranking presentation contract.
- Produces: skill instructions that preserve full evidence records while preventing non-discriminating report tables.

- [ ] **Step 1: Record the red validation baseline**

Run the skill validator before editing:

```bash
python /Users/bronson/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/defiant-gatekeeper-macro-news-analysis
```

Expected: PASS. Record the output in the task report; this is a documentation behavior change, so the red condition is a repository search showing that the skill does not yet contain the exact phrase `No meaningful sector differentiation from current evidence.`.

Run:

```bash
rg -n "No meaningful sector differentiation from current evidence|Sector Evidence Ranking" .agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md
```

Expected: no matches and exit status 1.

- [ ] **Step 2: Add the report-presentation contract**

Under `## Data-quality gate and evidence assessments`, add a concise subsection named `### Evidence presentation gate` that states:

- preserve and emit the complete underlying evidence contract for storage and audit;
- show a report ranking only when at least one usable posture is `WATCH`/`AVOID` and sector score spread is at least `4.0`;
- otherwise say exactly `No meaningful sector differentiation from current evidence.` and summarize coverage/missing evidence instead of printing repeated neutral rows;
- show at most three stronger and three weaker research hypotheses with no duplicates, observed factor values/contributions/dates, coverage, and primary missing input;
- collapse all-neutral/no-evidence constituent rows into a coverage limitation;
- rankings are research priority only, never forecasts or allocation instructions.

Do not change the skill's evidence engine, quadrant, momentum, consensus, or data-quality rules.

- [ ] **Step 3: Verify the skill text and validator**

Run:

```bash
rg -n "No meaningful sector differentiation from current evidence|Sector Evidence Ranking|three stronger|three weaker" .agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md
python /Users/bronson/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/defiant-gatekeeper-macro-news-analysis
```

Expected: the search finds the new subsection requirements and validation passes.

- [ ] **Step 4: Commit Task 3**

```bash
git add .agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md
git commit -m "docs: gate sector evidence presentation"
```

---

### Task 4: Final integrated verification

**Files:**
- Modify only if a verification failure demonstrates a requirement gap: `reporter.py`, `tests/test_reporter_evidence_ranking.py`, `tests/test_macro_pipeline.py`, `.agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: verified report behavior with no generated daily artifacts committed.

- [ ] **Step 1: Run complete Python verification**

Run: `PYTHONPATH=. .venv/bin/pytest -q`

Expected: all tests PASS; existing warnings are permitted.

- [ ] **Step 2: Run web regression verification**

Run: `cd web && npm test && npm run lint && npm run build`

Expected: all web tests PASS, lint exits 0, and the production build succeeds. The existing large-chunk warning is permitted.

- [ ] **Step 3: Validate the skill and scope**

Run:

```bash
python /Users/bronson/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/defiant-gatekeeper-macro-news-analysis
git diff --check
git status --short
```

Expected: skill validation passes; `git diff --check` has no errors; only the user's pre-existing generated files remain unstaged. No files under `data/`, `output/`, or `web/public/` are included in implementation commits.

- [ ] **Step 4: Commit only if verification required a code correction**

If a verification failure required a scoped correction, write a failing regression test first when applicable, fix it, rerun the affected and complete suites, then commit only the implementation files:

```bash
git add reporter.py tests/test_reporter_evidence_ranking.py tests/test_macro_pipeline.py .agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md
git commit -m "fix: complete evidence ranking verification"
```

If no correction was required, create no empty commit.
