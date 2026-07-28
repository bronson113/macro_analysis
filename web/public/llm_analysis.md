# 2026-07-28 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Freshness Check

- **GitHub Action:** [`Daily Macro Analysis & Deploy` run #21](https://github.com/bronson113/macro_analysis/actions/runs/30335854294) completed successfully on 2026-07-28. The resulting automated data commit is [`f51ba99`](https://github.com/bronson113/macro_analysis/commit/f51ba99bd8bf31123e8340c259725833d7d367b5).
- **Automated report date:** 2026-07-28.
- **Raw payload:** generated 2026-07-28 06:46 UTC; payload date 2026-07-28.
- **Core gate:** PASS. Fed assets and TGA are dated 2026-07-22; DFF, Treasury yields, and credit spreads are dated 2026-07-24; RRP, VIX, and curve spreads are dated 2026-07-27. These lags are consistent with source release frequencies and the core series have sufficient 30-day history.
- **Limitations:** the raw JSON summary omits DFF, 10Y–3M, CCC OAS, claims/payrolls, Sahm Rule, and the 30-day component decomposition, although most are present in repository observations or the automated report. The Sahm Rule is not explicitly calculated. Bank deposit, funding, capital, and charge-off details are absent.

## Macro Read

- **Active quadrant: Situation 4 — restrictive policy + reserve-liquidity expansion.** DFF is `3.63%`, unchanged over 30 days. The `4.69%` 10-year yield less the `2.21%` 10-year breakeven gives a `2.48%` real-yield proxy, above the framework's roughly `1.50%` restrictive threshold. The policy call comes from DFF and real-yield evidence, not the yield curve.
- **Reserve liquidity:** `$5,910.58B`, up `$134.58B` over 30 days, calculated as Fed assets `$6,747.38B` minus TGA `$835.42B` minus RRP `$1.38B`, normalized to billions. This is **reserve-liquidity expansion**, not QE; the evidence does not confirm a new Fed asset-purchase program.
- **Yield curve:** 10Y–2Y is `+34 bps` and 10Y–3M is `+69 bps`. Positive slopes reduce the immediate inversion signal but are not an all-clear. The `2.48%` real yield remains restrictive for long-duration assets.
- **Credit and volatility:** HY OAS is `2.79%`, IG OAS `0.45%`, NFCI `-0.55`, and VIX `18.67`, indicating calm broad conditions. However, CCC-and-below OAS is `9.96%`. Stress concentrated in the weakest borrowers is materially worse than the aggregate HY reading and limits cyclical and financial-sector conviction.
- **Labor, inflation, and valuation:** unemployment is `4.2%`; initial claims are `187,000` and continued claims `1.796M`, so labor does not confirm recession stress. The automated report characterizes CPI inflation as `3.7%`. Shiller P/E is `40.47`, making broad valuation the principal brake on adding index beta.

## What Changed

- The quadrant, policy stance, reserve-liquidity level, yield curve, credit spreads, VIX, and sector regime are unchanged from the immediately preceding data publication.
- The newest collection mainly refreshed intraday market prices: DXY `101.55 → 101.50`, WTI `$82.08 → $81.42`, gold `$4,037.40 → $4,049.40`, and copper `$6.3245 → $6.3430`.
- The small commodity moves do not change the research posture. Energy retains macro and valuation support, but the softer oil tape argues for staged accumulation.
- CCC OAS at `9.96%` is the key cross-check missing from the automated credit table. It prevents a blanket high-conviction Financials buy despite benign HY OAS and NFCI.

## Sector Actions

| Sector / theme | Action | Confidence | Judgment |
|---|---|---:|---|
| Energy (XLE) | **BUY / ACCUMULATE** | Moderate | Situation 4, WTI at `$81.42`, and `12.8x` group forward P/E align. Stage additions because oil is easing from its recent spike. |
| Healthcare (XLV) | **HOLD / SELECTIVE BUY** | Moderate | Defensive cash flows and `17.7x` forward P/E are acceptable under restrictive real yields; require company-specific earnings and policy checks. |
| Financials (XLF) | **HOLD / CAUTION** | Moderate-Low | Tight broad spreads are offset by `9.96%` CCC OAS and missing bank-specific deposit, funding, capital, and charge-off evidence. |
| Technology / AI compute | **HOLD / CAUTION** | Moderate | Profitable AI demand is supportive, but a `2.48%` real yield and Shiller P/E of `40.47` constrain multiple expansion. |
| HBM / memory | **HOLD / CAUTION** | Moderate | Structural demand remains, but memory-cycle volatility and incomplete historical-relative valuation checks argue against adding before earnings confirmation. |
| Consumer staples | **HOLD / CAUTION** | Moderate | Defensive demand is offset by `24.9x` forward P/E and a negative earnings-yield spread versus Treasuries. |
| Power / grid / cooling | **HOLD / CAUTION** | Moderate | Secular demand remains intact, but valuation dispersion and restrictive real yields require selective entry points. |
| Industrials (XLI) | **SELL / TRIM** | High | `29.9x` forward P/E versus a `19.0x` norm and a `-1.35%` earnings-yield spread outweigh the Situation 4 nominal-growth tailwind. |
| Consumer discretionary (XLY) | **SELL / TRIM** | High | `35.8x` forward P/E versus a `22.0x` norm and a `-1.90%` earnings-yield spread offer poor mid-term risk/reward. |
| Physical AI / robotics | **SELL / TRIM** | High | `58.2x` forward P/E versus a `30.0x` norm and a `-2.97%` earnings-yield spread fail valuation discipline under restrictive real yields. |

### Mechanical Recommendation Overrides

1. The automated report labels Financials **BUY / ACCUMULATE — HIGH** because of “macro quadrant tailwinds.” This violates the framework's financials guardrail: a favorable quadrant is insufficient without credit-quality and deposit/funding confirmation. With CCC OAS at `9.96%` and bank-specific evidence missing, the corrected judgment is **HOLD / CAUTION — Moderate-Low**.
2. The automated ecosystem table labels AI Compute **“Undervalued / Discounted Super-Cycle”** from a `22.37x` average forward P/E versus a `28.0x` norm. That wording is too strong when average EV/EBITDA is `46.20x`, constituent dispersion is wide, and real yields are restrictive. The corrected view is **HOLD / CAUTION — Moderate** pending earnings confirmation.

## Single-Stock Watchlist

- **EOG — selective review, Moderate confidence:** Energy sector risk is acceptable; forward P/E `9.55x` and EV/EBITDA `6.29x` are more than 20% below the energy-group averages. Confirm leverage, free-cash-flow sensitivity, reserve quality, and commodity assumptions before action.
- **PFE — selective review, Low-to-Moderate confidence:** Healthcare is acceptable at sector level; PFE's forward P/E `8.70x` and EV/EBITDA `7.56x` are materially below the healthcare-group averages. Confirm pipeline durability, patent exposure, earnings revisions, and balance-sheet quality.

`C`, `MU`, and `SMCI` are not promoted despite low multiples: required bank credit-quality, memory-cycle, accounting/earnings-quality, and balance-sheet checks are incomplete.

## Invalidation Triggers

- **Downgrade risk:** 30-day reserve liquidity turns negative; HY OAS rises above `4.5%` or widens rapidly; CCC stress broadens; NFCI turns positive; VIX sustains above `25`; Sahm/claims/payrolls confirm labor deterioration; real yields rise without earnings upgrades; or oil breaks lower alongside weaker demand indicators.
- **Upgrade risk:** explicit Fed easing plus continued reserve-liquidity expansion; stable labor; narrowing CCC spreads; firm earnings revisions; and valuation improvement driven by earnings rather than price declines alone.
- **Quadrant change:** a DFF decline of at least `10 bps` over 30 days would move policy toward easing; a negative 30-day reserve-liquidity change would move the liquidity axis to contraction.

## Repo Follow-Up

**Issue:** Financials receive a high-conviction mechanical buy without the framework's required credit-quality and deposit/funding confirmation. CCC OAS is available in repository observations but absent from the automated credit table and raw JSON summary. AI Compute also receives an overconfident “discounted super-cycle” label based mainly on forward P/E.

**Proposed Codex task:** add CCC OAS plus bank deposit/funding/asset-quality gates to financial-sector scoring and tests; prohibit Financials `BUY / ACCUMULATE` when those checks are missing or weakest-credit stress is elevated; export DFF, 10Y–3M, CCC OAS, labor inputs, and each 30-day liquidity component change to `data.json`; and require AI valuation labels to reconcile forward P/E, EV/EBITDA, real yields, and constituent dispersion.
