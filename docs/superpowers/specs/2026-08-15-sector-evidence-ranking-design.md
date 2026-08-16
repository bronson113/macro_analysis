# Sector Evidence Ranking Design

## Problem

The Daily Brief currently publishes every sector assessment in a large table. In the current payload, every posture is `NEUTRAL`, every uncertainty range is `-10.00` to `10.00`, and most descriptions repeat generic methodology text. The table implies precision and differentiation that the evidence does not support. The constituent table has the same problem when every company is neutral because its relative-history requirement is unmet.

The underlying factor records and prospective ledger remain useful for auditability and later evaluation. The problem is presentation, not the existence of the evidence contract.

## Decision

Replace the Markdown report's **Sector Evidence Assessments** table with a compact **Sector Evidence Ranking** section. Preserve all evidence calculations, payload fields, storage, and outcome-evaluation behavior.

The report must prefer an honest no-signal conclusion over forced ranking. It may show relative leaders and laggards only when the supplied assessments contain meaningful differentiation under the rules below. The output is a research-priority summary, never an execution instruction.

## Meaningful-differentiation gate

Normalize each assessment defensively. A usable assessment has a non-empty `sector_group`, a finite numeric `score`, a two-element finite numeric `score_range` with `low <= high`, and a finite `coverage_pct` between 0 and 100.

The sector set is meaningfully differentiated when both conditions hold:

1. At least one usable assessment has posture `WATCH` or `AVOID`.
2. The highest and lowest usable scores differ by at least `4.0` points.

If either condition fails, render no ranking table. Render this conclusion instead:

> **No meaningful sector differentiation from current evidence.** All sector views remain research-neutral or the score dispersion is too small to support a useful ranking.

The no-signal block must also state the usable assessment count, score spread, and the most common missing-evidence reason when available. It must not print the repeated per-sector uncertainty table.

This gate intentionally prevents today's all-neutral `-10` to `+10` assessments from being repackaged as a false league table. A `WATCH` or `AVOID` posture already incorporates uncertainty through the evidence engine's bounds; score dispersion adds a cross-sector materiality check.

## Ranking output

When the gate passes:

- Sort strongest sectors by descending score and weakest sectors by ascending score. Use the original input order as the stable final tie-breaker.
- Select at most three strongest and three weakest assessments. Do not repeat a sector on both sides.
- Preserve equal-score groups at a selection boundary in the copy by labeling them as tied; do not claim that one tied sector outranks another. The table remains capped at six total sectors, so a tie that exceeds the remaining capacity is summarized as `Additional sectors tied at this score: N` rather than selected arbitrarily.
- Label the two sides **Stronger evidence** and **Weaker evidence**. Do not use `best`, `worst`, `buy`, `sell`, `overweight`, or `underweight`.
- Show sector/group, instrument, posture, signed score, coverage, up to two leading observed factors, and one primary missing input.
- Add a disclosure that the ordering is relative research evidence, not an allocation recommendation, and that the score is not a forecast return.

## Factor presentation

For each selected sector, rank current non-zero factors by absolute weighted contribution (`abs(contribution * weight)`), then retain at most two. Use stable input order to break ties.

Render facts rather than generic rule descriptions. Each factor summary contains:

- a readable label derived from `factor_id`;
- the observed value and unit when present;
- the signed weighted contribution; and
- the observation date when present.

Example: `10Y real yield: 2.44% (-1.0; 2026-08-14)`.

For missing evidence, select the first factor after sorting by descending weight and stable input order. Render its `missing_reason` first, falling back to `explanation`, then a readable factor label. When none is missing, render `None identified`.

Malformed factor entries are ignored. Missing or malformed presentation details must never make report generation fail.

## Constituent evidence

Keep the underlying constituent assessments unchanged.

If every constituent assessment is `NEUTRAL` and has no positive or negative evidence, omit the full constituent table. Render a concise **Constituent Evidence Coverage** note containing:

- the number of constituents evaluated;
- the dominant missing-evidence reason; and
- an explicit statement that no company-level differentiation is supported yet.

If at least one constituent has posture `WATCH` or `AVOID`, or contains positive/negative evidence, retain the existing constituent table for now. This change does not redesign company-level ranking.

## Surfaces and data flow

The change applies to `Reporter.generate_markdown_report` and the generated Daily Brief Markdown consumed by the web application. The React dashboard's previously removed Evidence Assessments card remains removed. Terminal output is out of scope because the reported issue is the Daily Brief section and changing a second presentation surface would broaden this correction.

Presentation logic should live in focused, deterministic helper methods in `reporter.py`; it must not alter the evidence engine's scoring or posture rules.

## Testing

Tests must be written before production changes and must cover:

- the current all-neutral/full-range shape producing the no-differentiation conclusion and no sector table;
- a materially dispersed set with a `WATCH` or `AVOID` posture producing stronger/weaker rows;
- stable tie behavior without arbitrary superiority claims or duplicated sectors;
- factor summaries using observed values, units, signed contributions, and dates instead of generic explanations;
- malformed assessment/factor fields being skipped safely;
- all-neutral constituent assessments collapsing to one coverage note;
- differentiated constituent evidence retaining the existing table;
- the complete Python suite after focused tests pass.

## Scope boundaries

- Do not change factor contributions, score bounds, posture thresholds, or coverage calculations.
- Do not remove `evidence_assessments` or `constituent_assessments` from payloads, storage, reports' input contract, or outcome evaluation.
- Do not add market-price forecasts, allocations, execution language, or personalized investment advice.
- Do not restore the removed React Evidence Assessments section.
- Do not regenerate or commit daily data/output artifacts as part of this implementation.
