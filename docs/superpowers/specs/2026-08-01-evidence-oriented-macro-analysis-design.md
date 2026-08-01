# Evidence-Oriented Macro Analysis Design

## Purpose

Replace the deterministic trade-call engine with an analytically honest evidence system. The new system must expose factor contributions, missing evidence, data quality, uncertainty, and research postures without presenting heuristic rules as validated buy or sell recommendations. It must also introduce point-in-time outcome evaluation, improve valuation and peer methodology, stop keyword headlines from acting as directional signals, harden prototype storage and source reporting, and update every report and dashboard consumer.

This release deliberately retains free public data sources and CSV storage. Commercial data contracts and a database migration remain future work.

## Product Contract

The deterministic layer must not emit `BUY`, `SELL`, `ACCUMULATE`, `TRIM`, or conviction labels. Its public result for each sector or cohort contains:

- a bounded total score;
- immutable factor contributions;
- positive, negative, and neutral evidence;
- missing evidence with an explicit reason;
- evidence coverage;
- an uncertainty interval;
- one research posture: `WATCH`, `NEUTRAL`, or `AVOID`;
- the effective observation date and source-quality summary.

`WATCH` means the evidence is favorable enough to merit editorial or human review. `AVOID` means the evidence is unfavorable enough to warrant caution or exclusion from further research. Neither is an execution instruction. The ChatGPT editorial workflow may discuss possible actions, but must identify its conclusions as editorial interpretation rather than deterministic engine output.

All existing Python reports, raw JSON payloads, static web data, React views, and tests must migrate to this contract in the same release. Deprecated trade-action or conviction compatibility fields will not be emitted in newly generated output.

## Architecture and Data Flow

### Evidence collection

Each macro, credit, valuation, earnings, and structured-event input becomes an immutable factor record containing:

- stable factor identifier and category;
- direction (`positive`, `negative`, or `neutral`);
- bounded score contribution;
- observed value and unit;
- observation and fetch timestamps;
- source and provenance;
- freshness and quality state;
- concise explanation;
- missing-evidence reason when no usable observation exists.

Keyword-tagged news is context only and does not create a directional factor.

### Evidence aggregation

A pure aggregation component combines factor records without mutable last-match-wins overrides. It returns the contribution breakdown, bounded score, coverage, uncertainty interval, factor disagreement, and posture. Missing or stale evidence widens uncertainty instead of silently defaulting to confidence. Conflicting evidence remains visible rather than being overwritten.

### Presentation

The analyzer exposes the structured evidence result to the reporter and raw payload. The reporter and React dashboard render the same contract: posture first, followed by score range, coverage, positive and negative evidence, and missing inputs. Copy throughout the application describes outputs as research heuristics, not a tested strategy or investment advice.

### Semantic daily changes

Daily change detection compares structured semantic fingerprints rather than complete rendered Markdown strings. A fingerprint contains the state that matters analytically: regime, posture, classification, material threshold bucket, or evidence-set change. Numeric drift within the same semantic state updates the current displayed observation but remains `Unchanged`.

For example, a Shiller P/E move from 39.93 to 40.62 remains unchanged while both observations are `Very Expensive`. A transition between `Very Expensive` and `Expensive`, or another explicitly configured material boundary, is `Changed`. Previous prose is shown only for a genuine analytical change.

## Valuation Methodology

Sector valuation uses aggregate fundamentals rather than an arithmetic mean of company ratios:

- trailing P/E equals total eligible market capitalization divided by total eligible positive trailing earnings;
- forward P/E uses total market capitalization divided by total eligible implied forward earnings;
- EV/EBITDA equals total eligible enterprise value divided by total eligible positive EBITDA.

Negative, zero, missing, and implausible denominators are excluded from a ratio calculation but remain part of the coverage denominator. Every aggregate publishes total constituents, eligible constituents, eligible market-cap coverage, missing or excluded share, dispersion, and methodology.

Hard-coded fair-value constants no longer decide cheap, fair, or expensive classifications. Each aggregate is compared with its stored point-in-time historical distribution using robust medians and percentile bands. Until the configured minimum history exists, the result is `Insufficient History`. Historical raw observations remain available for later evaluation.

## Peer Cohorts

Broad mixed peer sets are replaced with declared business-model cohorts. Initial cohorts distinguish at least memory, fabless accelerators, foundries, semiconductor equipment, software/cloud, consumer hardware/platforms, banks, capital markets, managed care, pharmaceuticals, energy producers, refiners, industrial machinery, retailers, and the existing specialized physical-AI and infrastructure baskets where constituents are genuinely comparable.

A company is compared only with its declared cohort. Relative valuation requires a configured minimum count and coverage. Otherwise the result is `Insufficient Comparable Peers`. The engine retains historical company-to-cohort relative multiples and removes the fallback that calls a stock cheap solely because its multiple is below a broad current average.

## News Handling

The mechanical news component becomes a retrieval and provenance layer. It may attach topic tags derived from keywords, but those tags are explicitly `uninterpreted`, carry no positive or negative impact score, and never trigger sector stress or recommendation logic.

Stored news includes headline, available summary, source, link, publication or retrieval time, topic tags, and interpretation status. Raw context is passed to the editorial workflow. Only explicitly structured events with declared provenance may become deterministic evidence.

## Outcome Evaluation

The release adds a point-in-time signal ledger. Every generated sector posture records date, score, uncertainty interval, coverage, factor snapshot, and benchmark. An evaluator calculates matured outcomes at 1-, 3-, 6-, and 12-month horizons:

- total and benchmark-relative return;
- hit rate by posture;
- average and median excess return;
- maximum drawdown;
- results by score band;
- stated transaction-cost assumptions for portfolio-style summaries.

The evaluator must align observations and prices without look-ahead. Retrospective macro evaluation is allowed only for factors whose historical point-in-time inputs exist. The system must not reconstruct historical valuation or news signals from current information. Those components accumulate prospective evidence from this release onward.

All output publishes sample size and labels results insufficient until configured minimum sample and elapsed-time requirements are met. Passing tests or a positive early sample must not be described as strategy validation.

## Source Resilience and Observability

Fetch adapters expose normalized source metadata: source name, observation time, fetch time, status, staleness, record count, and a machine-readable error category. Each run records source-health observations.

When a source fails, the last valid observation may remain available but must be marked stale; stale inputs widen evidence uncertainty. A failure must never silently appear current. The README documents that Yahoo Finance, scraped Shiller P/E data, CNN endpoints, Google News RSS, and the FRED workaround are unofficial or operationally fragile.

## Storage Quick Wins

CSV remains the persistence format in this release. Writes use a per-file lock, a temporary file in the destination directory, flush and durability handling appropriate to the platform, and atomic replacement. This prevents partial files and reduces lost updates among cooperating writers without claiming full database transaction semantics.

CSV schemas have explicit versions and centralized column definitions. Documentation describes CSV as current storage and the SQLite file/path as legacy. A future database migration remains out of scope.

## Naming, Security, and Documentation

- Rename `DynamicMacroAnalyst` to `MechanicalMacroAnalyst` and update imports and consumers.
- Remove Gemini-specific naming from raw-data code in favor of provider-neutral editorial-analysis terms.
- Extend `.gitignore` for `.env`, environment overrides, credentials, private keys, and common secret-file patterns.
- Pin third-party GitHub Actions to immutable commit SHAs and retain readable version comments.
- Add research-heuristic and not-validated-strategy language to the README, generated report, editorial prompt, and dashboard.
- Do not choose or add a software license without owner direction.

## Error Handling

Invalid factors are rejected at their boundary with a clear error during development and test execution. Runtime source failures become missing or stale evidence rather than crashes where safe. Aggregation must remain deterministic for identical inputs. A sector with insufficient coverage returns `NEUTRAL` with widened uncertainty and explicit missing evidence; it must not manufacture a directional posture.

## Testing and Verification

Implementation follows test-first red/green cycles. Required automated coverage includes:

- factor contribution bounds and deterministic aggregation;
- positive, negative, neutral, missing, and stale evidence;
- uncertainty widening and coverage calculation;
- posture boundaries without trade directives;
- aggregate valuation math, negative denominators, weighting, coverage, and insufficient history;
- peer eligibility and minimum-comparable behavior;
- uninterpreted news tags that cannot affect scores;
- semantic change detection, including the 39.93-to-40.62 Shiller example;
- point-in-time horizon alignment, benchmark excess return, transaction costs, drawdown, small-sample labels, and look-ahead prevention;
- atomic CSV writes, schema handling, and source-health persistence;
- analysis-to-payload-to-report-to-dashboard integration with no deterministic `BUY`, `SELL`, or conviction fields.

Final verification requires the full Python suite, web unit tests, web lint, production build, pipeline generation from controlled or available data, and interactive browser inspection of the built dashboard. The branch is committed and pushed only after those gates pass.

## Deferred Work

- Paid or contract-backed market and news providers.
- Full database migration, multi-host transactions, and high-volume query architecture.
- Statistical estimation of factor weights before sufficient clean point-in-time history exists.
- Claims of strategy validation before minimum samples and horizons mature.
- A repository license, pending an explicit owner choice.
