# Level-Based Macro Quadrants Design

## Purpose

Replace the current direction-only macro matrix with a level-based regime matrix. The quadrant must describe whether monetary policy is restrictive or accommodative and whether reserve liquidity is abundant or scarce. Recent direction and market expectations remain visible as separate overlays.

This change fixes the failure case that motivated the work: liquidity can remain historically abundant while declining for several weeks. A negative 30-day change must describe deteriorating momentum, not redefine abundant liquidity as scarce.

The design applies consistently to the Python analyzer, stored snapshots, recommendation inputs, terminal and Markdown reports, the React dashboard, documentation, tests, and the repository-local `defiant-gatekeeper-macro-news-analysis` skill.

## Source-Framework Interpretation

The Defiant Gatekeeper video [How to Get Rich by Just Looking at Federal Reserve Policies](https://www.youtube.com/watch?v=I5mEnDCDCxA) presents the matrix with balance-sheet level (`High`/`Low`) and interest-rate level (`Low`/`High`) axes. It does not present a 30-day-change matrix. [Macro Investing 101 for Beginners](https://www.youtube.com/watch?v=cZN__KbCVsM) similarly evaluates macro indicators against high, normal, and low ranges before inferring likely Federal Reserve behavior.

The existing repository implementation changed those level concepts into `cutting/raising` and `expanding/contracting`. The new implementation restores level-based axes while improving on the videos by defining reproducible benchmarks, neutral bands, point-in-time calculations, data-quality rules, and separate momentum and expectations layers.

## Analytical Contract

The public regime result has four distinct layers:

1. **State:** the level-based policy and liquidity classifications that determine the quadrant.
2. **Momentum:** 30- and 90-day changes that describe whether each state is improving, stable, or deteriorating.
3. **Consensus:** timestamped market expectations for the future policy-rate and Federal Reserve balance-sheet path.
4. **Quality:** observation dates, freshness, historical coverage, conflicts, missing inputs, and confidence.

Momentum and consensus must never silently change the quadrant. They may change its description, confidence, and downstream evidence, but the quadrant remains a function of the two state classifications.

## Four Situations

| Situation | Policy state | Liquidity state | Default interpretation |
|---|---|---|---|
| 1 | Accommodative | Abundant | Strongest risk-liquidity tailwind |
| 2 | Accommodative | Scarce | Easing response with limited liquidity support; late-cycle caution |
| 3 | Restrictive | Scarce | Strongest liquidity and valuation headwind |
| 4 | Restrictive | Abundant | Policy/liquidity conflict; abundant liquidity offsets some policy restraint |

If policy is neutral, liquidity is neutral, either core state is unavailable, or core evidence is materially contradictory, return situation `0` with a precise non-actionable reason. Do not force one of the four situations.

## Policy State

### Inputs

- Daily effective federal funds rate (`DFF`).
- Core PCE price index (`PCEPILFE`) converted to trailing 12-month inflation.
- Latest New York Fed Holston-Laubach-Williams U.S. natural real-rate estimate whose publication date is on or before the analysis date.

### Calculation

```text
real_policy_rate_pct = effective_federal_funds_rate_pct - core_pce_yoy_pct
policy_gap_pct = real_policy_rate_pct - neutral_real_rate_pct
```

Classify the policy state as:

- `RESTRICTIVE` when `policy_gap_pct > +0.50` percentage points.
- `ACCOMMODATIVE` when `policy_gap_pct < -0.50` percentage points.
- `NEUTRAL` when `-0.50 <= policy_gap_pct <= +0.50`.
- `INSUFFICIENT_DATA` when any required input is unavailable or stale.

The half-percentage-point neutral band acknowledges that the neutral rate is estimated imprecisely and prevents small revisions from flipping quadrants.

### Historical context

Report the current real policy rate's percentile within the trailing ten calendar years, excluding the current observation. Require at least five years of observations. This percentile is context and a diagnostic cross-check; the economically meaningful neutral-rate gap remains the policy-state classifier.

### Freshness

- `DFF`: no more than 7 calendar days old.
- Core PCE: no more than 75 calendar days old.
- Neutral-rate estimate: no more than 180 calendar days since publication.

Do not substitute the Treasury yield curve, nominal policy-rate direction, or the 10-year real yield for the policy state. Those remain separate financial-condition diagnostics.

## Liquidity State

### Inputs and normalization

Continue calculating the reserve-liquidity proxy in billions of dollars:

```text
reserve_liquidity_b = Fed total assets_b - TGA_b - ON RRP_b
```

Normalize it by nominal GDP (`GDP`, billions of dollars at a seasonally adjusted annual rate):

```text
normalized_liquidity_pct_gdp = 100 * reserve_liquidity_b / nominal_gdp_b
```

Quarterly nominal GDP is carried forward only until the next release and for no more than 120 calendar days. The normalized series is evaluated weekly using the latest observation available on or before each weekly date. No future observation may be backfilled into an earlier date.

### Historical distribution

For each analysis date, build a trailing ten-calendar-year distribution that excludes the current observation. Require at least five years and 200 aligned weekly observations.

Classify liquidity as:

- `ABUNDANT` at or above the historical 60th percentile.
- `SCARCE` at or below the historical 40th percentile.
- `NEUTRAL` between the 40th and 60th percentiles.
- `INSUFFICIENT_DATA` when history, freshness, or a required component is inadequate.

Use percentile ranks rather than a raw-dollar average because nominal economic size and the Federal Reserve's operating regime have changed. Report the trailing median, 40th percentile, 60th percentile, current percentile, sample start, sample end, and observation count so the threshold is auditable.

### Money-market corroboration

Add `IORB` and `SOFR` as corroborating reserve-pressure inputs. Compute five-business-day mean spreads:

```text
effr_iorb_spread_bp = 100 * (EFFR - IORB)
sofr_iorb_spread_bp = 100 * (SOFR - IORB)
```

Flag pressure when the five-day mean `EFFR-IORB` spread is at least `-2` basis points or the five-day mean `SOFR-IORB` spread is at least `+10` basis points.

- One pressure flag reduces liquidity confidence to `PARTIAL` but does not change the level classification.
- Both pressure flags make liquidity `INDETERMINATE_CONFLICT` and withhold the quadrant.
- Missing corroborating inputs are disclosed and reduce confidence, but do not make the core historical classification unavailable.

These diagnostics recognize that reserve scarcity is ultimately expressed in money-market pricing, not just the size of a balance-sheet proxy.

### Freshness

- Fed total assets and TGA: no more than 14 calendar days old.
- ON RRP: no more than 7 calendar days old.
- Nominal GDP: no more than 120 calendar days old.
- EFFR, IORB, and SOFR corroboration: no more than 7 calendar days old.

## Momentum Overlay

Calculate changes in the normalized liquidity ratio and the policy gap using the nearest observations on or before 30 and 90 calendar days earlier.

For normalized liquidity:

- `IMPROVING` when the change is greater than `+0.05` percentage points of GDP.
- `DETERIORATING` when the change is less than `-0.05` percentage points of GDP.
- `STABLE` otherwise.

For the policy gap, lower values are more accommodative:

- `EASING` when the change is less than `-0.10` percentage points.
- `TIGHTENING` when the change is greater than `+0.10` percentage points.
- `STABLE` otherwise.

Publish both horizons independently. A state can therefore read `ABUNDANT; 30-day deteriorating; 90-day stable` or `RESTRICTIVE; 30-day easing; 90-day easing`.

## Consensus Overlay

### Meaning and source

Consensus means the median future path reported by the New York Fed Survey of Market Expectations. Use the survey of primary dealers and active market participants, not the FOMC Summary of Economic Projections and not an inferred Treasury-yield proxy.

Store consensus observations point in time with:

- survey reference date;
- publication date;
- target/horizon date;
- metric (`FED_FUNDS_RATE` or `FED_BALANCE_SHEET_ASSETS`);
- median value and unit;
- source URL;
- freshness and parsing status.

Prefer the available target closest to six months ahead, limited to horizons from three through nine months.

### Interpretation

Compare the consensus path with the current corresponding level:

- Expected policy `EASING` when the median expected rate is at least 10 basis points below current DFF.
- Expected policy `TIGHTENING` when it is at least 10 basis points above current DFF.
- Expected policy `STABLE` otherwise.
- Expected balance sheet `EXPANDING` when expected assets are at least 0.5% above current assets.
- Expected balance sheet `CONTRACTING` when expected assets are at least 0.5% below current assets.
- Expected balance sheet `STABLE` otherwise.

The balance-sheet survey does not forecast TGA or ON RRP. Label it `Fed balance-sheet consensus`, not `net-liquidity consensus`.

Consensus is `UNAVAILABLE` if the survey omits the metric, uses an unsupported question format, has no three-to-nine-month horizon, or was published more than 120 calendar days before the analysis date. An unavailable consensus never blocks the quadrant.

## Data Model and Component Boundaries

Create a focused regime-signal module containing immutable data structures and pure calculations for:

- policy-state measurement;
- liquidity-state measurement;
- historical percentile calculations;
- momentum calculations;
- consensus interpretation;
- freshness and confidence composition.

`MacroAnalyzer` remains responsible for loading source observations and assembling the regime inputs. It must not contain quadrant threshold logic.

`MacroMatrixEngine` becomes a pure combination layer. It accepts the policy and liquidity state results, returns situation `0` or `1` through `4`, and attaches the existing sector hypotheses and contextual risk checks. It must not recalculate rates, liquidity, history, or consensus.

The structured public result contains:

```text
policy_state
liquidity_state
situation_id
name
description
policy_measurement
liquidity_measurement
momentum_30d
momentum_90d
consensus
quality
missing_inputs
conflicts
favored_sectors
favored_company_types
disfavored_sectors
```

Each measurement includes current value, benchmark values, classification, observation dates, history window, and source metadata. Consumers render this structure rather than reconstructing regime logic from labels.

## Storage and Point-in-Time Integrity

Add the following fields to daily snapshots:

- normalized liquidity as percent of GDP;
- liquidity historical percentile and threshold values;
- real policy rate, neutral real rate, and policy gap;
- policy historical percentile;
- policy and liquidity state;
- 30- and 90-day momentum values and labels;
- consensus policy and balance-sheet directions, values, survey date, target date, and quality;
- situation identifier and overall regime quality.

Old snapshot rows remain readable with the new fields absent. Do not retroactively manufacture historical quadrant, neutral-rate, or consensus values from information that was unavailable at the time. Newly generated snapshots use the new schema; existing published dated reports are historical artifacts and are not rewritten.

Historical baselines, neutral-rate inputs, and consensus observations must use release/publication dates when available. Evaluation for an earlier date must never access a later vintage or revision.

## Reporting and Dashboard

Update terminal output, Markdown reports, raw/static dashboard data, and React components to show the same ordered information:

1. `Current State`: for example, `Situation 4 — Restrictive policy + abundant liquidity`.
2. `Momentum`: separate 30- and 90-day policy and liquidity readings.
3. `Market Consensus`: expected path, source survey date, target date, or explicit unavailability.
4. `Interpretation`: sector hypotheses and named risk checks.
5. `Data Quality`: freshness, history coverage, conflicts, and missing inputs.

Replace UI and documentation language that defines the axes as cutting/raising and expanding/contracting. The dashboard cheat sheet must explain the level-based axes and the separate overlays.

The motivating example must render as:

```text
Current State: Reserve liquidity abundant (75th historical percentile)
Momentum: Deteriorating over 30 days
Interpretation: Liquidity remains abundant, but the tailwind is weakening
```

## Recommendation Integration

Existing sector hypotheses continue to map from situation identifiers, but recommendation logic consumes the structured state and quality fields rather than matching words such as `Expanding` or `Contracting` in rendered labels.

- Situation `0`, `INSUFFICIENT_DATA`, or `INDETERMINATE_CONFLICT` defaults broad sector actions to `HOLD` under the current contract.
- Momentum can downgrade conviction or add caution, but cannot change favored/disfavored membership by itself.
- Consensus can add forward-looking confirmation or contradiction, but cannot create a buy or sell action by itself.
- Existing valuation, credit, labor, and tax guardrails remain in force.

This quadrant refactor does not implement the separate evidence-oriented recommendation redesign already specified elsewhere in the repository.

## Error Handling

- Reject invalid units, non-finite values, dates after the analysis date, and non-positive nominal GDP at the calculation boundary.
- Treat source or parsing failures as structured missing evidence, not as zero.
- Preserve the last valid observation only with its actual date and stale status.
- Never fall back from normalized liquidity to raw-dollar historical classification.
- Never fall back from the neutral-rate policy gap to 30-day rate direction.
- Never use market consensus without its publication and target dates.
- Return deterministic results for identical point-in-time inputs.

## Skill Update

Update `.agents/skills/defiant-gatekeeper-macro-news-analysis/SKILL.md` in the same release.

The revised skill must:

- define the core matrix as policy level by liquidity level;
- include the exact state, neutral-band, freshness, and insufficient-data rules from this specification;
- require momentum and consensus to be reported as overlays;
- preserve the distinction between reserve-liquidity expansion and QE;
- prohibit classifying policy from the yield curve or recent rate direction alone;
- prohibit classifying liquidity from a raw-dollar historical average or recent direction alone;
- add a concise high-but-falling example;
- update the four situation descriptions and morning workflow;
- keep valuation, credit, labor, source-discipline, confidence, and tax guardrails that remain applicable;
- remain under 500 lines and contain no redundant auxiliary documentation.

Before editing the skill, run a baseline application scenario against the current skill in which liquidity is at the 75th historical percentile but has fallen over 30 days. Record whether the current instructions misclassify it. After editing, rerun equivalent application scenarios and verify that the skill identifies the level as abundant, reports deteriorating momentum separately, and does not invent unavailable consensus.

Validate the final skill folder with the skill-authoring validator. No `agents/openai.yaml` is required because the existing repository-local skill does not contain agent metadata and this change does not introduce UI metadata.

## Testing

Implementation follows test-first red/green cycles. Required automated coverage includes:

- all four combinations of accommodative/restrictive and abundant/scarce;
- neutral policy and neutral liquidity returning situation `0`;
- policy-gap boundaries at exactly `-0.50` and `+0.50`;
- liquidity boundaries at exactly the 40th and 60th percentiles;
- the 75th-percentile high-but-falling regression case;
- low-but-rising liquidity remaining scarce with improving momentum;
- independent and mixed 30/90-day momentum;
- trailing historical windows excluding the current observation and all future observations;
- minimum-history and minimum-observation requirements;
- unit normalization for Fed assets, TGA, RRP, and nominal GDP;
- DFF, core PCE, neutral-rate, GDP, and liquidity-component freshness;
- one versus two money-market pressure flags;
- missing corroboration reducing confidence without erasing a valid level classification;
- consensus horizon selection, direction thresholds, staleness, unsupported formats, and explicit unavailability;
- consensus and momentum being unable to change the quadrant;
- old snapshot rows remaining readable;
- analyzer-to-storage-to-report-to-dashboard consistency;
- recommendation logic using structured states rather than label substring matching;
- skill validation and before/after skill application scenarios.

Final verification requires the complete Python test suite, web unit tests, web lint, production build, controlled pipeline generation, generated-report inspection, dashboard inspection at supported breakpoints, and validation of the updated skill.

## Documentation

Update the README, morning editorial prompt, dashboard cheat sheet, report methodology text, and relevant module docstrings. Documentation must state that:

- quadrants describe current normalized levels;
- momentum describes recent direction;
- consensus describes the expected future path and may be unavailable;
- the reserve-liquidity proxy is a heuristic, not broad money or proof of QE;
- neutral and insufficient-data outcomes are intentional safeguards;
- sector mappings are research hypotheses, not deterministic forecasts.

## Out of Scope

- Paid futures, Bloomberg, or other commercial consensus feeds.
- Estimating statistical factor weights or claiming strategy validation.
- Rewriting previously published dated reports.
- Replacing the broader recommendation engine with the separate evidence-oriented design.
- Treating the New York Fed balance-sheet survey as a forecast of TGA, ON RRP, or the complete reserve-liquidity proxy.
