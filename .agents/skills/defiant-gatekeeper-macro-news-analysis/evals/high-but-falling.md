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
4. Applies the data-quality gate: calls out that freshness, five-year/200-week
   history, units, and corroboration/conflict checks must pass, and withholds
   or conditions the result if a required core check fails.
5. Describes the outlook conditionally and does not turn the scenario into a
   deterministic trade instruction or claim unavailable evidence.

## Fail conditions

Fail if the response selects Situation 3 because liquidity momentum is falling,
calls the current liquidity level scarce/contracting, conflates consensus with
the current state, omits data-quality gating, or invents missing 90-day,
freshness, corroboration, or consensus details.
