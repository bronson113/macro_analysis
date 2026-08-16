---
name: defiant-gatekeeper-macro-news-analysis
description: Use when producing the daily macro report or evaluating a 3M-1Y, tax-aware sector research posture from policy, reserve liquidity, markets, and news.
---

# Defiant Gatekeeper Macro Analysis

Use this skill for a conditional research note, not a deterministic forecast or
personalized investment advice. The macro quadrant is a level-based state:
current policy level × current normalized reserve-liquidity level. Recent
changes and survey expectations are overlays.

## Operating contract

Always produce these sections in this order:

1. **Current State** — policy level, liquidity level, and the situation (or
   Situation 0 when the level gate withholds it).
2. **Momentum** — policy and liquidity separately at both 30 and 90 days.
3. **Market Consensus** — the New York Fed survey path, or explicit
   `UNAVAILABLE`/`STALE`.
4. **Interpretation** — the situation hypothesis and named risk checks.
5. **Data Quality** — freshness, history coverage, missing inputs, conflicts,
   corroboration, and confidence.

Do not infer a missing value, backfill a future observation, or turn an overlay
into a current-state classification.

## Classify in this exact order

1. **Classify current policy level from the real-policy gap.**
2. **Classify current reserve-liquidity level from its historical percentile.**
3. **Select the quadrant only from those two current states.**
4. **Report 30-day and 90-day momentum separately.**
5. **Report NY Fed SME consensus separately; it never changes the current
   quadrant.**

If a step lacks required or sufficiently fresh evidence, preserve the missing
state and apply the data-quality gate; do not substitute a different signal.

## 1. Current policy level

Use point-in-time observations of daily effective fed funds (`DFF`), the core
PCE price index (`PCEPILFE`), and the latest Holston-Laubach-Williams natural
real-rate estimate (`r-star`) published on or before the analysis date:

```text
core_pce_yoy_pct = 100 * (core_pce_latest / core_pce_same_period_one_year_ago - 1)
real_policy_rate_pct = DFF_pct - core_pce_yoy_pct
policy_gap_pct = real_policy_rate_pct - rstar_pct
```

Classify only the gap:

- `RESTRICTIVE` when `policy_gap_pct > +0.50 pp`.
- `ACCOMMODATIVE` when `policy_gap_pct < -0.50 pp`.
- `NEUTRAL` when `-0.50 <= policy_gap_pct <= +0.50 pp`.
- `INSUFFICIENT_DATA` when no valid selected observation exists on or before
  `as_of`, the selected core input is malformed/stale, or core PCE YoY cannot
  be formed. Exclude every row dated after `as_of` before selecting the latest
  valid row; future rows are never current and do not invalidate an older
  valid selected observation. Disclose future-row exclusion when relevant.

The exact `-0.50` and `+0.50` boundaries are neutral. Required freshness is
`DFF <= 7` calendar days, core PCE `<= 75` days, and r-star `<= 180` days.
Report the real-policy-rate percentile over the trailing ten calendar years,
excluding the current observation, only as context; require at least five
years. Never classify policy from the yield curve, a recent nominal-rate move,
or the 10-year real yield alone. Those are separate financial-condition
diagnostics.

## 2. Current reserve-liquidity level

Normalize source units before computing the proxy:

```text
reserve_liquidity_b = Fed_assets_b - TGA_b - ON_RRP_b
normalized_liquidity_pct_gdp = 100 * reserve_liquidity_b / nominal_GDP_b
```

Use `WALCL` for Fed assets, `WDTGAL` (or `WTREGEN`) for TGA, `RRPONTSYD` for
ON RRP, and `GDP` for nominal GDP. Fed assets and TGA are commonly millions;
RRP and GDP are billions. The proxy is a reserve-supply heuristic, not broad
money and not proof of QE. If it rises, identify whether the cause is Fed
assets, TGA, or RRP before calling it support; use `reserve-liquidity
expansion`, not QE, unless official data confirms asset purchases.

Build the history point-in-time: align weekly observations using the latest
input on or before each weekly date; carry nominal GDP forward for no more
than 120 days and never use a later release. For the trailing ten calendar
years, exclude the current observation and require at least five years and 200
aligned weekly observations. Classify the current percentile as:

- `ABUNDANT` at-or-above P60 (the historical 60th percentile, inclusive).
- `SCARCE` at-or-below P40 (the historical 40th percentile, inclusive).
- `NEUTRAL` between P40 and P60.
- `INSUFFICIENT_DATA` when a required component, freshness limit, history
  window, or observation count fails.

Required freshness is Fed assets/TGA `<= 14` days, ON RRP `<= 7` days, and
nominal GDP `<= 120` days. Report current percentile, median, p40, p60,
sample start/end, and count so the level is auditable. Never classify from a
raw-dollar historical average or a recent change alone.

Use five-business-day money-market corroboration when available:

```text
effr_iorb_spread_bp = 100 * (EFFR - IORB)
sofr_iorb_spread_bp = 100 * (SOFR - IORB)
```

Flag pressure when the five-day mean `EFFR-IORB >= -2 bp` or
`SOFR-IORB >= +10 bp`. One flag makes quality `PARTIAL` but does not change a
valid level. Both flags make quality `INDETERMINATE_CONFLICT` and withhold the
quadrant. Missing corroboration is disclosed and lowers confidence; it does
not erase an otherwise valid historical level. EFFR, IORB, and SOFR each have
`<= 7`-day freshness limits.

## 3. Select the current quadrant

Only the two current-level states select a situation:

| Situation | Current policy | Current liquidity | Default read |
|---|---|---|---|
| 1 | `ACCOMMODATIVE` | `ABUNDANT` | Strongest risk-liquidity tailwind |
| 2 | `ACCOMMODATIVE` | `SCARCE` | Easing response with limited liquidity support; late-cycle caution |
| 3 | `RESTRICTIVE` | `SCARCE` | Strongest liquidity and valuation headwind |
| 4 | `RESTRICTIVE` | `ABUNDANT` | Policy restraint offset by abundant liquidity; inspect the source |

Momentum, consensus, CPI, labor data, the yield curve, credit, valuation,
news, and sentiment may change the explanation or confidence, but never the
`situation_id`. If either level is `NEUTRAL` or `INSUFFICIENT_DATA`, if a
required **core level** source is absent/stale, or if core evidence is
materially contradictory, return Situation `0: NO ACTIONABLE MACRO QUADRANT`.
Core level sources are DFF, core PCE, r-star, Fed assets, TGA, ON RRP, and
nominal GDP/history inputs. Missing or stale EFFR/IORB/SOFR corroboration alone
keeps a valid level quadrant and makes liquidity quality `PARTIAL`; one
pressure flag also remains `PARTIAL`, while two pressure flags make
`INDETERMINATE_CONFLICT` and withhold it.

Situation-specific starting hypotheses (not automatic actions):

- **Situation 1:** favor profitable duration, technology/AI infrastructure,
  semiconductors, grid/power, and discretionary only when labor and credit are
  sound. Sahm or credit warnings downgrade confidence.
- **Situation 2:** favor healthcare, staples, quality dividends, and low
  leverage when real-rate and dollar context support them; scrutinize high-beta
  or highly indebted growth.
- **Situation 3:** emphasize cash/T-bills and low-leverage free-cash-flow
  businesses. Financials need credit, deposit, and funding confirmation; high
  real yields raise duration risk.
- **Situation 4:** inspect whether abundant liquidity comes from assets, TGA,
  RRP, reserve management, or emergency facilities. Consider energy, copper,
  gold, inflation-linked cash flows, and quality cyclicals only when inflation,
  commodities, and credit confirm the hypothesis.

## 4. Report momentum as an overlay

Calculate changes from the nearest observation on or before 30 and 90 calendar
days before the analysis date. Publish all four readings independently:

- Policy gap: lower is more accommodative; change `< -0.10 pp` is `EASING`,
  change `> +0.10 pp` is `TIGHTENING`, otherwise `STABLE`.
- Normalized liquidity: change `> +0.05 pp of GDP` is `IMPROVING`, change
  `< -0.05 pp` is `DETERIORATING`, otherwise `STABLE`.

At exactly a threshold, report `STABLE`. A high current level can therefore
coexist with easing policy momentum or deteriorating liquidity momentum. State
the prior date/value when available and say `UNAVAILABLE` when it is not;
never let a momentum label replace a level.

## 5. Report NY Fed SME consensus as a non-blocking overlay

Use the New York Fed Survey of Market Expectations for primary dealers and
active market participants, not the FOMC Summary of Economic Projections and
not an inferred Treasury-yield path. Select the supported target closest to
six months ahead among horizons from three through nine months, using the
lower horizon for an exact tie. Store survey reference/publication date,
target date, metric, median value/unit, source URL, and parsing status.

Compare the selected median with the current level:

- Expected DFF at least `10 bp` below current DFF: policy consensus `EASING`.
- At least `10 bp` above: `TIGHTENING`; otherwise `STABLE`.
- Expected Fed assets at least `0.5%` above current assets: balance-sheet
  consensus `EXPANDING`; at least `0.5%` below: `CONTRACTING`; otherwise
  `STABLE`.

Call the second signal **Fed balance-sheet consensus**, not net-liquidity
consensus: the survey does not forecast TGA or ON RRP. Mark consensus
`UNAVAILABLE` when the metric or supported format/horizon is absent; mark it
`STALE` when the selected survey is more than 120 days old. Consensus is
non-blocking and never changes the current quadrant. Do not invent a consensus
path from market prices.

## High-but-falling regression example

Given a policy gap of `+0.80 pp` and falling, normalized reserve liquidity at
the `75th historical percentile` and down `0.10 pp of GDP` over 30 days, and
NY Fed SME consensus for lower DFF with a stable Fed balance sheet, report:

```text
Current State: RESTRICTIVE policy + ABUNDANT reserve liquidity (Situation 4;
75th percentile).
Momentum: policy EASING; liquidity DETERIORATING over 30 days. Report 90-day
values separately and do not invent them if absent.
Market Consensus: policy EASING; Fed balance-sheet consensus STABLE.
```

The current state is Situation 4 because `+0.80 pp` is restrictive and the
75th percentile is abundant. Falling momentum does not make liquidity scarce,
and consensus does not alter the quadrant. Apply the data-quality gate: verify
freshness, the five-year/200-week history requirements, units, and money-market
conflict flags; disclose missing checks and withhold the state if a required
gate fails.

## Data-quality gate and evidence assessments

Before interpreting a sector assessment, list every missing or stale core input,
history shortfall, unit problem, future-date exclusion, corroboration flag,
consensus limitation, and source failure. Missing evidence lowers coverage and
widenes the score range; it is not favorable evidence. Situation 0 or
`INSUFFICIENT_DATA` contributes missing evidence rather than a trade signal.

For each sector or instrument, emit only the evidence contract: posture
`WATCH`, `NEUTRAL`, or `AVOID`; numeric `score`; `score_range`; `coverage_pct`;
and the `positive_factors`, `negative_factors`, `neutral_factors`,
`missing_evidence`, and complete `factors` lists. Preserve factor dates,
sources, observed values, quality, explanations, and missing reasons. These
are research-review states, not execution instructions: do not emit
`BUY`, `SELL`, `ACCUMULATE`, `TRIM`, action, conviction, allocation, entry, or
exit fields. A macro hypothesis never overrides valuation, credit, labor,
inflation, tax friction, or sector-specific evidence:

- Compare forward P/E, EV/EBITDA, earnings yield versus the 10Y Treasury, and
  sector norms as visible valuation factors. Negative ERP is a rate/valuation
  headwind factor, not a standalone execution signal.
- Use HY/CCC/IG OAS, NFCI, VIX, real yields, DXY, commodities, earnings
  revisions, and bellwether filings/news as separate evidence.
- Restrictive real yields can be a negative duration factor unless valuation
  and earnings justify it. Financials require credit and funding evidence, not
  merely high rates or a favorable situation.
- Tax friction is a factor and a research limitation, not permission to emit
  an allocation instruction. A single-stock laggard can be flagged for review
  only when it is at least 20% cheaper than peers on forward P/E or EV/EBITDA,
  has no obvious balance-sheet/earnings/legal/structural break, and belongs to
  a sector whose evidence posture is not `AVOID`.

## Morning workflow

1. Fetch preferred primary sources and log failures; normalize units.
2. Check point-in-time dates and freshness for all core inputs.
3. Run the five classification steps in order and apply the data-quality gate.
4. Evaluate yield curve, labor/inflation, credit, volatility, valuation,
   dollar/commodity, and bellwether context without feeding them into the
   quadrant axes.
5. Render Current State, Momentum, Market Consensus, Interpretation, and Data
   Quality in that order.
6. Produce evidence postures with score ranges, coverage, factors, and missing
   evidence; disclose stale/missing inputs and never claim strategy validation.

## Preferred sources

Prefer Federal Reserve Board, New York Fed, FRED/St. Louis Fed, Treasury, BLS,
BEA, and official company filings for mechanics. Financial media can add timely
context, but headlines do not override quantitative evidence without
confirmation. The reserve-liquidity proxy remains a heuristic and is not a
complete measure of global liquidity.
