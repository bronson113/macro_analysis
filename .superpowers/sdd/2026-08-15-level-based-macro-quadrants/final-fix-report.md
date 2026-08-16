# Final fix wave — level-based macro quadrants

Date: 2026-08-15
Base: `46d72eb`
Implementation commit: `80201b5` (`feat: complete level-based macro quadrant fix wave`)

## Outcome

The final-review fix list is implemented and verified. The normal configured
fetch path now includes active core PCE, official NY Fed HLW r-star, daily DFF
for EFFR corroboration, and the optional NY Fed Survey of Market Expectations.
Observation and consensus storage retain point-in-time metadata and revisions;
the analyzer, matrix, reporter, raw payload, ordered dashboard export, and UI
carry the resulting quality and provenance fields.

## Source decisions and live format checks

- Core PCE uses FRED `PCEPILFE` (index units) and is in
  `ACTIVE_FRED_SERIES_KEYS`.
- Policy and five-business-day corroboration use the official daily FRED
  `DFF` series. The monthly `FEDFUNDS` series is no longer configured as
  `effr`.
- Fed assets/TGA/RRP/GDP remain `WALCL`/`WDTGAL`/`RRPONTSYD`/`GDP`, with
  explicit millions/billions units and source URLs.
- R-star uses the official NY Fed HLW current-estimates workbook and landing
  page. The live workbook was fetched successfully and inspected: sheet
  `HLW Estimates`, two header rows, `Date`, and grouped `Natural Rate (r*) / US`
  columns. The parser records publication and vintage dates, source URL, and
  percent units.
- Consensus uses the official NY Fed SME landing page and its current linked
  workbook. The live workbook was fetched successfully and inspected: release
  date, panel type, subject, horizon, target date, aggregation, and aggregation
  value fields. The parser selects the Combined panel, accepts median/P50,
  converts decimal rate fractions to percentage points, and combines the
  policy and total-assets six-month targets into one optional overlay.
- Offline fixtures inject bytes/readers/providers; unit tests do not make
  fragile network calls.

## TDD evidence

Each behavior was driven by a focused failing test before implementation and a
focused green run. The final wave included these RED/GREEN checks:

- Revision storage and strict `as_of` vintage selection: storage tests first
  exposed overwrite/future-vintage behavior, then 20 storage tests passed.
- Publication-date freshness for r-star: the targeted policy test first
  returned no state when observation and publication dates differed, then
  passed using source availability age.
- Latest consensus publication revision: the targeted test initially selected
  the older publication, then passed after publication-vintage tie-breaking.
- GDP mis-scale rejection: macro-regime and validator tests first accepted a
  positive but million-scaled GDP value, then passed with structured scale
  reasons.
- FRED wrong-unit rejection: the targeted ingestion test initially persisted
  a wrong-regime unit, then passed after the configured-unit guard.
- Legacy latest-observation shape: the targeted storage test initially exposed
  an internal timestamp column/type regression, then passed while retaining
  the legacy string-date API shape.
- Official SME layout and Combined-panel selection: targeted parser tests
  initially missed release/horizon fields and selected a non-Combined row,
  then passed with the official layout adapter.
- Official HLW two-row header parsing: the targeted parser test initially
  missed the pandas MultiIndex Date column, then passed with the grouped-header
  adapter.
- Duplicate selected consensus metrics: the canonical fixture first produced
  four metrics instead of two when policy/assets shared one candidate, then
  passed after identity-based de-duplication.
- Source-health schema validation: a file without `fetch_key` records first
  passed silently, then passed the new negative test after explicit rejection.

The final targeted consensus/source run was `18 passed`; storage was `20
passed`; validator was `7 passed`; report and exporter/presenter targeted
checks passed. The full suite below is the final evidence after all edits.

## Implemented areas

- `config.py`, `fetcher.py`, and `hlw_rstar.py`: active core PCE, official
  HLW provider, optional SME provider boundary, daily DFF, source URLs, source
  units, and non-blocking optional-source health outcomes.
- `storage.py`: backward-compatible observation metadata columns
  (`release_date`, `publication_date`, `vintage_date`, `source_url`, `unit`),
  revision-preserving keys, conservative legacy-row handling, strict point-in-
  time reads, consensus CSV persistence, and snapshot consensus metadata.
- `macro_regime.py` and `validate_fresh_macro_data.py`: availability-date
  freshness, source-unit checks, non-finite/malformed input reasons, positive
  and plausibly scaled GDP checks, and required source-health validation.
- `consensus.py`: publication-aware selection, official SME parsing, panel and
  horizon normalization, metric/unit/source/parsing metadata, malformed-row
  isolation, and optional/non-blocking failure behavior.
- `macro_matrix.py` and `analyzer.py`: `MISSING`/`CONFLICT` aliases,
  actionability quality/reasons/conflicts, and public data-quality propagation
  for neutral and conflict outcomes.
- `reporter.py`, `extract_dashboard_data.py`, and web presentation code:
  level-versus-overlay wording, consensus provenance and stale/unavailable
  reasons, ordered exporter data, and actionability/age/reason presentation.
- `.agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md`, web copy,
  and descriptions: exact `scarce at-or-below P40` and `abundant at-or-above
  P60` wording, plus the reserve-liquidity/QE and CPI policy caveats.

## Verification

- Python: `PYTHONPATH=. .venv/bin/pytest -q` → **192 passed, 57 warnings**.
- Python syntax: `python -m compileall -q` over changed modules/tests → pass.
- Web tests: `npm test` → **25 passed**.
- Web lint: `npm run lint` → pass.
- Web production build: `npm run build` → pass. Vite emitted only the
  existing large-chunk advisory (the main JS chunk is over 500 kB).
- Skill validation: `quick_validate.py` → **Skill is valid!**; skill file is
  268 lines, below the 500-line limit.
- Controlled offline integration: a clean temporary configured-source fixture
  with DFF, core PCE, HLW r-star publication/vintage metadata, six years of
  weekly liquidity/GDP inputs, five common corroboration days, and an SME
  fixture produced `RESTRICTIVE` policy, `ABUNDANT` liquidity, Situation 4,
  and `OK` consensus with publication date `2026-07-10`. Policy quality was
  `PARTIAL` only because the intentionally small fixture lacked full momentum
  history; the policy state was produced correctly.
- Production validator against the current generated workspace data remains
  non-green because that data is stale/incomplete (including missing r-star,
  daily corroboration, and source-health records). This is reported as a
  residual data-refresh concern below, not a code-test failure.

## Generated artifacts and residual concerns

The generated CSV/JSON/lock artifacts were intentionally not staged, restored,
deleted, or edited as part of the fix commit. They remain workspace-dirty for
the separately merged evidence architecture and current data refresh state.
The full Python suite also exercised a production-default storage path, so the
workspace generated CSVs may show schema-refresh timestamps; none are in the
commit.

Remaining operational concerns:

1. A production run must refresh the active FRED series and official HLW/SME
   sources before the standalone validator can pass. Optional SME/HLW fetch
   failures are visible in source health but do not block a report by design;
   core level inputs still withhold the quadrant when missing or stale.
2. The NY Fed publishes workbook layouts over time. The current live layouts
   were verified and covered by fixtures, but future layout changes should be
   handled by adding a fixture before changing parser assumptions.
3. The Vite build retains its pre-existing chunk-size advisory; no build or
   lint failure remains.
