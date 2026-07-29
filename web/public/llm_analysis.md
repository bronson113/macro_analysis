# 2026-07-29 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Freshness Check

- **GitHub Action:** [`Daily Macro Analysis & Deploy` run #24](https://github.com/bronson113/macro_analysis/actions/runs/30451888124) completed successfully on 2026-07-29 at 5:30 AM PDT (1m 31s).
- **Automated state:** report date `2026-07-29`; raw payload date `2026-07-29`, generated `2026-07-29 12:31:42 UTC`; automated parent commit [`9f48e23`](https://github.com/bronson113/macro_analysis/commit/9f48e23ac2dc7535fea8788c2184b8ab106dddd5).
- **Core gate:** PASS. Fed assets and TGA are dated 2026-07-22; RRP and curve spreads 2026-07-28; Treasury yields and credit spreads 2026-07-27; VIX 2026-07-29. These lags are consistent with source frequencies.
- **Missing/limited inputs:** current `data.json` omits DFF, 10Y–3M, 10Y breakeven, CCC OAS, claims/payrolls, Sahm Rule, and the 30-day liquidity component decomposition. Bank deposit, funding, capital, and charge-off evidence is also absent. The automated report supplies DFF and 10Y–3M but not the remaining gaps.

## Macro Read

- **Active quadrant: Situation 4 — restrictive policy + reserve-liquidity expansion.** DFF is `3.63%`, unchanged over 30 days. The automated real-yield proxy is `2.45%`, above the framework's roughly `1.50%` restrictive threshold. Policy stance is therefore based on policy-rate and real-yield evidence, not the yield curve.
- **Reserve liquidity:** `$5,910.83B`, up `$134.84B` over 30 days: Fed assets `$6,747.38B` minus TGA `$835.42B` minus RRP `$1.13B`, all normalized to billions. This is **reserve-liquidity expansion**, not QE; the payload does not confirm a Fed asset-purchase program or expose enough history to attribute the 30-day increase by component.
- **Yield curve:** 10Y–2Y is `+35 bps`; 10Y–3M is `+71 bps`. Positive slopes remove the immediate inversion signal but are not an all-clear, especially with restrictive real yields.
- **Credit/volatility:** HY OAS `2.81%`, IG OAS `0.46%`, NFCI `-0.55`, and VIX `18.54` show benign broad conditions. Conviction is capped because current CCC OAS and bank-specific credit/funding inputs are missing.
- **Labor/inflation/valuation:** unemployment is `4.2%`; the automated report characterizes CPI inflation as `3.7%`. Shiller P/E is `40.57`, so broad valuation remains the main brake on adding index beta.

## What Changed

- The quadrant, DFF stance, reserve-liquidity level/change, yield curve, broad credit conditions, and sector regime are effectively unchanged from the prior report.
- Market overlays moved modestly: VIX `18.21 → 18.54`, DXY `101.39 → 101.46`, WTI `$82.60 → $84.19`, gold `$4,019.90 → $4,077.50`, and copper `$6.34 → $6.29`.
- Higher oil and gold marginally reinforce the Situation 4 hard-asset posture; softer copper and the elevated Shiller P/E argue against broad cyclical expansion.
- New semiconductor selloff headlines and wide constituent valuation dispersion reinforce selectivity rather than a blanket AI/technology upgrade.

## Sector Actions

| Sector / theme | Action | Confidence | Judgment |
|---|---|---:|---|
| Energy (XLE) | **BUY / ACCUMULATE** | Moderate | Situation 4, WTI at `$84.19`, and `12.6x` forward P/E align; stage exposure because geopolitics may be inflating the oil signal. |
| Healthcare (XLV) | **HOLD / SELECTIVE BUY** | Moderate | Defensive cash flows and `18.1x` forward P/E are acceptable under restrictive real yields; require company-level policy and earnings checks. |
| Financials (XLF) | **HOLD / CAUTION** | Moderate-Low | `13.8x` valuation and tight broad spreads are insufficient without CCC, deposit/funding, capital, and charge-off confirmation. |
| Technology / AI compute | **HOLD / CAUTION** | Moderate | `2.45%` real yield, semiconductor volatility, and broad valuation stretch offset profitable AI demand. |
| HBM / memory | **HOLD / CAUTION** | Moderate-Low | Low multiples are attractive, but the current chip selloff and incomplete earnings-quality/history checks block an upgrade. |
| Consumer staples | **HOLD / CAUTION** | Moderate | Defensive demand is offset by `25.3x` forward P/E and a negative earnings-yield spread. |
| Power / grid / cooling | **HOLD / CAUTION** | Moderate | Secular demand remains, but valuation dispersion and restrictive real yields require selective entries. |
| Industrials (XLI) | **SELL / TRIM** | High | `30.1x` forward P/E versus `19.0x` norm and `-1.33%` ERP outweigh the nominal-growth tailwind; CAT risk headlines add caution. |
| Consumer discretionary (XLY) | **SELL / TRIM** | High | `36.0x` versus `22.0x` norm and `-1.87%` ERP offer poor mid-term risk/reward. |
| Physical AI / robotics | **SELL / TRIM** | High | `58.0x` versus `30.0x` norm and `-2.93%` ERP fail valuation discipline under restrictive real yields. |

### Mechanical Recommendation Overrides

1. The automated report calls Financials **BUY / ACCUMULATE — HIGH** solely from “macro quadrant tailwinds.” That conflicts with the framework rule that Financials require credit-quality and deposit/funding confirmation. With current CCC and bank-specific inputs missing, the corrected view is **HOLD / CAUTION — Moderate-Low**.
2. The ecosystem table calls AI Compute **“Undervalued / Discounted Super-Cycle”** from `21.5x` average forward P/E versus a `28.0x` norm. Average EV/EBITDA is still `43.92x`, constituent dispersion is wide, real yields are restrictive, and chip stress headlines are active. Corrected view: **HOLD / CAUTION — Moderate** pending earnings confirmation.

## Single-Stock Watchlist

- **EOG — selective review, Moderate confidence:** Energy sector risk is acceptable; forward P/E `9.50x` and EV/EBITDA `6.26x` support valuation review. Confirm leverage, free-cash-flow sensitivity, reserve quality, and commodity assumptions.
- **PFE — selective review, Low-to-Moderate confidence:** Healthcare is acceptable at sector level; forward P/E `8.92x` and EV/EBITDA `7.69x` are materially below group levels. Confirm pipeline durability, patent exposure, revisions, and balance-sheet quality.

`C`, `MU`, and `SMCI` are not promoted despite low multiples: required bank credit-quality, memory-cycle, accounting/earnings-quality, and balance-sheet checks remain incomplete.

## Invalidation Triggers

- **Downgrade:** 30-day reserve liquidity turns negative; HY OAS exceeds `4.5%` or widens rapidly; CCC stress broadens; NFCI turns positive; VIX sustains above `25`; Sahm/claims/payrolls confirm labor deterioration; real yields rise without earnings upgrades; or oil/copper weaken together on demand deterioration.
- **Upgrade:** explicit Fed easing with continued reserve-liquidity expansion; stable labor; confirmed benign CCC and bank credit data; firm earnings revisions; and valuation improvement driven by earnings rather than price decline alone.
- **Quadrant change:** DFF falls at least `10 bps` over 30 days, or the 30-day reserve-liquidity change turns negative.

## Repo Follow-Up

**Issue:** Financials still receive a high-conviction mechanical buy without mandatory credit-quality and deposit/funding gates. Current public JSON also omits DFF, 10Y–3M, 10Y breakeven, CCC OAS, labor checks, and the liquidity-change decomposition. AI Compute's “discounted super-cycle” label remains overconfident when EV/EBITDA, real yields, and dispersion disagree.

**Proposed Codex task:** add CCC OAS and bank deposit/funding/asset-quality gates plus tests; prohibit Financials `BUY / ACCUMULATE` when those checks are absent or stressed; export DFF, 10Y–3M, 10Y breakeven, CCC OAS, claims/payrolls/Sahm, and each 30-day liquidity component change to `data.json`; and require ecosystem valuation labels to reconcile forward P/E, EV/EBITDA, real yields, and constituent dispersion.
