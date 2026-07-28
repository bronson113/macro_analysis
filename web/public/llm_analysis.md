# 2026-07-28 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Freshness Check

- **GitHub Action:** `Daily Macro Analysis & Deploy` run #16 completed successfully on 2026-07-27 at approximately 21:49 PDT. The resulting automated data commit is `cfaab4d16e7f53d6c3789d09e66774d556036fb1` (2026-07-28 04:49 UTC).
- **Automated report date:** 2026-07-28.
- **Raw payload:** generated 2026-07-28 04:49; payload date 2026-07-28.
- **Core input dates:** Fed assets and TGA 2026-07-22; RRP and VIX 2026-07-27; Treasury yields and credit spreads 2026-07-24; NFCI 2026-07-17; unemployment and CPI observations 2026-06-01. These lags are consistent with source release frequencies, but the payload does not expose DFF, the 10Y–3M series, Sahm Rule, claims/payrolls, CCC OAS, or sector historical valuation series.

## Macro Read

- **Active quadrant: Situation 4 — restrictive policy + reserve-liquidity expansion.** Policy is `HOLDING_RESTRICTIVE`: DFF is 3.63%, unchanged over 30 days, while the reported 10Y real-yield proxy is 2.48%. This classification comes from policy-rate data and real-yield evidence, not the yield curve.
- **Reserve liquidity:** `$5,910.58B`, up `$134.58B` over 30 days, calculated as Fed assets `$6,747.38B` minus TGA `$835.42B` minus RRP `$1.38B`, all normalized to billions. Call this **reserve-liquidity expansion**, not QE: the published payload does not show Fed asset purchases or a 30-day component decomposition.
- **Yield curve:** 10Y–2Y is `+34 bps` and the report gives 10Y–3M at `+69 bps`; both are positive. Un-inversion lowers the immediate inversion signal but is not an all-clear without labor confirmation. The 10Y yield at 4.69% and real-yield proxy at 2.48% remain restrictive for long-duration assets.
- **Credit and volatility:** HY OAS `2.79%`, IG OAS `0.45%`, NFCI `-0.55`, and VIX `18.67` show contained stress and loose broad financial conditions. HY and IG spreads widened only 2 bps day over day, while VIX rose 1.09 points—still calm, but marginally less benign.
- **Labor/inflation/valuation:** unemployment is 4.2% (June); the automated report characterizes CPI inflation as 3.7%. Shiller P/E is `40.47`, a broad valuation constraint. This combination favors selectivity over adding broad index beta.

## What Changed

- The quadrant and core sector regime did not change.
- Reserve liquidity slipped `$0.71B` from the prior report because RRP rose from `$0.68B` to `$1.38B`; the 30-day expansion eased from `+$135.29B` to `+$134.58B`.
- Rates fell modestly: 10Y `4.71% → 4.69%`, 2Y `4.37% → 4.33%`; 10Y–2Y narrowed `36 → 34 bps`. The real-yield proxy nevertheless rose `2.45% → 2.48%` as the 5Y breakeven fell to 2.18%.
- Risk tone weakened at the margin: S&P 500 `7,452.12 → 7,413.18`, VIX `17.58 → 18.67`, HY OAS `2.77% → 2.79%`, and IG OAS `0.43% → 0.45%`.
- WTI fell `$83.94 → $81.70`; gold fell `$4,099.10 → $4,046.00`. HBM moved from `HOLD` to `HOLD / CAUTION` amid memory-cycle headline risk. MU and MSFT dropped from the mechanical lagging-value list.

## Sector Actions

| Sector / theme | Action | Confidence | Judgment |
|---|---|---:|---|
| Energy (XLE) | **BUY / ACCUMULATE** | Moderate | Situation 4, WTI at $81.70, and 12.8x average forward P/E align, but falling oil and geopolitical-premium reversal argue for staged additions, not a high-conviction chase. |
| Financials (XLF) | **HOLD / SELECTIVE BUY** | Moderate | Tight spreads and NFCI support sector risk, but the payload lacks deposit, funding, charge-off, and capital evidence required for a blanket buy. Prefer discounted, well-capitalized banks after company-level review. |
| Healthcare (XLV) | **HOLD / SELECTIVE BUY** | Moderate | Defensive cash flows and 17.7x forward P/E are acceptable under restrictive real yields; use company-specific earnings and policy checks. |
| Technology / AI compute | **HOLD / CAUTION** | Moderate | Earnings durability is supportive, but a 2.48% real yield and very expensive broad market limit multiple expansion. |
| HBM / memory | **HOLD / CAUTION** | Moderate | Structural demand remains, but current headline and price volatility weaken the case for adding before earnings confirmation. |
| Consumer staples | **HOLD / CAUTION** | Moderate | Defensive demand is offset by a 24.9x forward P/E and negative earnings-yield spread versus Treasuries. |
| Power / grid / cooling | **HOLD / CAUTION** | Moderate | Secular demand is intact, but aggregate valuation and restrictive real yields require selective entry points. |
| Industrials (XLI) | **SELL / TRIM** | High | 29.9x forward P/E versus a 19.0x norm and a `-1.35%` earnings-yield spread justify trimming expensive exposure despite the Situation 4 nominal-growth tailwind. |
| Consumer discretionary (XLY) | **SELL / TRIM** | High | 35.8x forward P/E versus a 22.0x norm, `-1.90%` earnings-yield spread, and softer labor breadth create poor mid-term risk/reward. |
| Physical AI / robotics | **SELL / TRIM** | High | 58.2x forward P/E versus a 30.0x norm and a `-2.97%` earnings-yield spread fail valuation discipline under restrictive real yields. |

### Mechanical Recommendation Override

The automated report labels Financials (XLF) **BUY / ACCUMULATE — HIGH** because of “macro quadrant tailwinds.” That is too mechanical. The framework explicitly says not to buy financials solely because the quadrant favors them and requires credit-quality plus deposit/funding confirmation. Credit is contained, but bank-specific funding and asset-quality inputs are missing. The corrected judgment is **HOLD / SELECTIVE BUY — Moderate**.

## Single-Stock Watchlist

- **EOG — selective review, Moderate confidence:** Energy sector risk is acceptable; forward P/E `9.55x` and EV/EBITDA `6.29x` are more than 20% below the energy-group averages, with no balance-sheet break identified in this payload. Confirm leverage, free-cash-flow sensitivity, reserve quality, and commodity assumptions before action.
- **C — selective review, Low-to-Moderate confidence:** Financials are only selective, but C trades at `10.39x` forward earnings and `1.16x` book, materially below the banking group. Confirm CET1, deposit beta, net charge-offs, reserves, and transformation execution; valuation alone is not enough.

No technology name is promoted: XLK is `HOLD / CAUTION`, and the payload does not establish that apparent discounts are free of earnings-cycle or data-quality risk.

## Invalidation Triggers

- **Downgrade risk:** reserve liquidity turns negative over 30 days; HY OAS rises above 4.5% or accelerates sharply; NFCI turns positive; VIX sustains above 25; unemployment/claims and Sahm Rule confirm deterioration; real yields rise further without earnings upgrades; or oil breaks lower with weakening demand.
- **Upgrade risk:** explicit Fed easing plus continued reserve-liquidity expansion; broader labor stabilization; stable/tightening credit spreads; and sector valuations that improve through earnings growth rather than price alone.
- **Situation 4 change:** a ≥10 bp 30-day DFF decline would move policy toward easing; a negative 30-day reserve-liquidity change would move the liquidity axis to contraction.

## Repo Follow-Up

**Issue:** the report assigns Financials a high-conviction buy from the quadrant without displaying the required deposit/funding/credit-quality confirmation. The raw payload also omits the DFF, 10Y–3M, Sahm/claims/payrolls, CCC OAS, and 30-day Fed-assets/TGA/RRP component changes used by the narrative.

**Proposed Codex task:** add explicit financial-sector gating tests (deposit/funding and asset-quality availability required for `BUY / ACCUMULATE`); export all policy, curve, labor, credit, and 30-day liquidity-component inputs to `web/public/data.json`; add tests that reserve-liquidity expansion is never labeled QE without confirmed Fed asset purchases; and show per-input observation dates plus missing-data confidence downgrades in the report.