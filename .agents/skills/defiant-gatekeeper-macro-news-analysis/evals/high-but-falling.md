# High-but-falling reserve-liquidity evaluation

## Scenario

> Policy gap is +0.80 percentage point and falling; normalized reserve liquidity
> is at the 75th historical percentile and fell 0.10 percentage point of GDP
> over 30 days; survey consensus expects lower DFF and a stable Fed balance
> sheet. Classify the current quadrant and describe the outlook.

## Required response contract

The response passes only if it:

1. Names current `RESTRICTIVE + ABUNDANT` and **Situation 4**. The 75th
   percentile is the current liquidity level; its fall is not a level change.
2. Reports policy momentum as `EASING` and liquidity momentum as
   `DETERIORATING` separately. It must not use either momentum label as a
   quadrant axis. If 90-day observations are not supplied, it says so rather
   than inventing them.
3. Reports consensus separately as policy `EASING` and Fed balance-sheet
   consensus `STABLE`; consensus does not alter the current situation.
4. Applies the data-quality gate: distinguishes required core level inputs
   (DFF, core PCE, r-star, Fed assets, TGA, ON RRP, nominal GDP/history) from
   optional EFFR/IORB/SOFR corroboration. It calls out freshness,
   five-year/200-week history, units, and pressure-conflict checks; missing or
   stale corroboration alone is `PARTIAL` and does not withhold a valid level,
   while two pressure flags withhold it.
5. Describes the outlook conditionally, does not turn the scenario into a
   deterministic trade instruction, and uses evidence-only sector outputs:
   `WATCH`/`NEUTRAL`/`AVOID` with score, range, coverage, factors, and missing
   evidence—not BUY/SELL/action/conviction fields.

## Fail conditions

Fail if the response selects Situation 3 because liquidity momentum is falling,
calls the current liquidity level scarce/contracting, conflates consensus with
the current state, treats missing/stale EFFR/IORB/SOFR corroboration as an
automatic Situation 0, prescribes trade actions, omits data-quality gating, or
invents missing 90-day, freshness, corroboration, or consensus details.
