# 2026-08-03 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Macro Read

### Evidence

- **Active quadrant: Situation 3 — restrictive policy + reserve-liquidity contraction.** DFF is `3.63%`, unchanged over 30 days, while the automated real-yield proxy is `2.40%`. Policy stance comes from policy-rate and real-yield evidence, not the yield curve.
- **Reserve liquidity:** `$5,765.60B`, down `$64.66B` over 30 days: Fed assets `$6,738.19B` minus TGA `$970.44B` minus RRP `$2.15B`, normalized to billions. This is reserve-liquidity contraction, not automatically QT.
- **Yield curve:** 10Y–2Y is `+47 bps`; 10Y–3M is `+92 bps`. Positive slopes remove the inversion signal but do not negate restrictive policy or contracting reserve liquidity.
- **Credit/volatility:** HY OAS `2.84%`, IG OAS `0.43%`, NFCI `-0.56`, and VIX `16.00` remain benign. The liquidity warning is not confirmed by broad credit or volatility stress.
- **Labor/inflation/valuation:** unemployment is `4.2%`; the automated report characterizes CPI inflation as `3.7%`. Shiller P/E is `40.91`, so broad valuation remains a major risk constraint.

### Inference

Situation 3 raises multiple-compression risk, but benign credit and volatility argue against indiscriminate selling. The appropriate posture is selective defense: avoid adding expensive duration, favor quality and liquidity, and require valuation plus earnings confirmation before acting.

## What Changed

- Core macro inputs are effectively unchanged from the August 1 report because most official series last updated July 29–31. The quadrant remains Situation 3 and the 30-day liquidity contraction remains near `-$65B`.
- WTI fell `$84.67 → $79.29` (about `6.4%`), weakening the prior selective Energy case. Gold rose `$4,049.10 → $4,093`; copper edged up `$6.44 → $6.46`.
- VIX stayed near `16`; DXY held near `99.79`; Fear & Greed improved `42.46 → 45.09` but remains neutral.
- The upgraded evidence engine reports every sector as `NEUTRAL`, with `85.7%` coverage and a `-10 to +10` uncertainty range because sector valuation percentiles are unavailable. Constituent screens now correctly disclose insufficient peer/history evidence rather than promoting weakly supported watchlist names.
- The prior LLM website file had been removed during the evidence-analysis upgrade; this note restores it.

## Sector Actions

| Sector / theme | Action | Confidence | Evidence and judgment |
|---|---|---:|---|
| Technology (XLK) | **HOLD / CAUTION** | Moderate-High | Evidence score `-4`; contracting liquidity and a `2.40%` real yield are headwinds, but credit and VIX do not confirm stress and valuation percentile is missing. |
| Financials (XLF) | **HOLD / CAUTION** | Moderate-Low | Score `+1` reflects Situation 3 tailwinds, but bank funding, deposits, capital, charge-offs, loan quality, and CCC credit evidence are absent. |
| Healthcare (XLV) | **HOLD** | Moderate | Score `-1`; defensive characteristics help, but current sector valuation percentile and company-quality confirmation are missing. |
| Energy (XLE) | **HOLD / CAUTION** | Moderate | Score `-1`; WTI's drop to `$79.29` weakens momentum, while producer valuations still require complete relative-history confirmation. |
| Industrials (XLI) | **HOLD / CAUTION** | Moderate-Low | Score `-1`; liquidity is a headwind, but the new engine does not provide a current sector valuation percentile sufficient for a high-conviction trim. |
| Consumer discretionary (XLY) | **HOLD / CAUTION** | Moderate | Score `-3`; Situation 3 and contracting liquidity are adverse, but missing valuation coverage caps conviction. |
| Consumer staples (XLP) | **HOLD** | Moderate | Score `-1`; defensive demand supports holding, while missing valuation percentile blocks accumulation. |
| AI compute | **HOLD / CAUTION** | Moderate-High | Score `-4`; average forward P/E is `22.14x`, but EV/EBITDA is `45.51x`, real yields are restrictive, and relative-history evidence is insufficient. |
| HBM / memory | **HOLD / CAUTION** | Moderate | Score `-1`; `17.48x` forward P/E exceeds the `16.0x` norm and peer/history coverage is insufficient. |
| Physical AI / robotics | **SELL / TRIM** | High | Macro score `-4` combines with clear absolute valuation stretch: `58.77x` forward P/E and `51.87x` EV/EBITDA versus a `30.0x` norm. |
| Power / grid / cooling | **HOLD / CAUTION** | Moderate-Low | Contracting liquidity and restrictive real yields offset structural demand; peer comparability and valuation history remain incomplete. |

### Mechanical Recommendation Overrides

1. AI Compute is labeled **“Undervalued / Discounted Super-Cycle”** while its sector evidence score is `-4`, valuation percentile is missing, EV/EBITDA is `45.51x`, and constituent histories are insufficient. Corrected view: **HOLD / CAUTION — Moderate-High**.
2. Physical AI / Robotics receives a `NEUTRAL` evidence posture despite `58.77x` forward P/E, `51.87x` EV/EBITDA, a `30.0x` norm, restrictive real yields, and contracting liquidity. Corrected view: **SELL / TRIM — High**.
3. Financials' positive macro factor is not enough for accumulation. The Defiant Gatekeeper framework requires bank-specific credit and funding confirmation, which remains absent. Corrected view: **HOLD / CAUTION — Moderate-Low**.

## Single-Stock Watchlist

**No names are promoted today.** The upgraded constituent engine reports insufficient relative history or insufficient comparable peers for every reviewed company. Most cohorts have only two valid historical observations versus the required 60.

Prior candidates `EOG` and `PFE` remain monitor-only despite low current multiples; their balance-sheet, earnings-quality, catalyst, and historical-relative gates are incomplete. `VLO`, `C`, `MU`, `TER`, and `SMCI` also fail the required evidence threshold.

## Invalidation Triggers

- **Further downgrade:** reserve-liquidity contraction deepens; HY OAS exceeds `4.5%` or widens rapidly; CCC stress broadens; NFCI turns positive; VIX sustains above `25`; labor deteriorates; or earnings revisions weaken while real yields remain high.
- **Upgrade:** the 30-day liquidity change turns positive; DFF falls at least `10 bps`; labor remains stable; CCC and bank credit evidence is benign; and current valuation/earnings data support risk taking.
- **Energy upgrade:** WTI stabilizes with demand confirmation and producer cash-flow revisions improve—not merely a geopolitical price spike.
- **Quadrant change:** DFF falls at least `10 bps` over 30 days or reserve liquidity returns to expansion.

## Freshness Check

- **GitHub Action:** [Daily Macro Analysis & Deploy](https://github.com/bronson113/macro_analysis/actions/runs/30817876113) completed successfully on `2026-08-03`; data validation, web tests, production build, commit, and Pages deployment all passed.
- **Automated state:** report date `2026-08-03`; raw payload date `2026-08-03`, generated `2026-08-03 13:28:24 UTC`; automated parent commit [`98481e4`](https://github.com/bronson113/macro_analysis/commit/98481e4f1243b8491e7e7ce9e29a73b18c54bd4e).
- **Core gate:** PASS. Fed assets and TGA are dated `2026-07-29`; RRP, curve spreads, and breakevens `2026-07-31`; Treasury yields and credit spreads `2026-07-30`; NFCI `2026-07-24`; market overlays `2026-08-03`. These lags are consistent with source frequencies and the weekend.
- **Missing/limited inputs:** public raw JSON still omits DFF, 10Y–3M, 10Y breakeven, CCC OAS, claims/payrolls, Sahm Rule, and the 30-day liquidity component decomposition. Sector valuation percentiles are unavailable, and constituent relative histories do not meet the 60-observation requirement.

## Repo Follow-Up

**Issue:** Evidence transparency improved materially, but sector factor explanations are generic rather than directional, absolute ecosystem valuations are not reconciled with sector postures, uncertainty ranges remain maximally wide, and the AI “discounted super-cycle” label conflicts with the evidence score. The LLM analysis file was also removed during the upgrade.

**Proposed Codex task:** generate factor explanations that state the actual favorable/adverse mapping; integrate absolute forward P/E and EV/EBITDA into sector evidence when valuation percentiles are missing; reconcile ecosystem labels with evidence scores and real yields; calibrate uncertainty ranges to coverage and missing-factor impact; accumulate and test the required constituent history; export the omitted macro/credit series and liquidity decomposition; and add a build/deployment test ensuring `web/public/llm_analysis.md` exists or the dashboard handles its absence explicitly.
