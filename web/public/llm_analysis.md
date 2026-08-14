# 2026-08-14 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Macro Read

### Evidence

- **Active quadrant: Situation 3 — restrictive policy + reserve-liquidity contraction.** DFF is `3.63%`, up `1 bp` over 30 days and classified `HOLDING_RESTRICTIVE`; the real-yield proxy is `2.44%`. Policy stance comes from policy-rate evidence, not the yield curve.
- **Reserve liquidity:** `$5,800.10B`, down `$185.47B` over 30 days: Fed assets `$6,759.95B` minus TGA `$959.40B` minus RRP `$0.45B`, normalized to billions. The weekly Fed-asset increase was more than offset by the TGA build. This is reserve-liquidity contraction, not QE.
- **Yield curve:** 10Y–2Y is `+48 bps`; 10Y–3M is `+76 bps`. Positive slopes remove the inversion signal but do not override restrictive policy or the negative 30-day liquidity direction.
- **Credit/volatility:** HY OAS is `2.71%`, IG OAS `0.40%`, NFCI `-0.58`, and VIX `14.50`. Credit and volatility remain benign; systemic stress does not confirm the liquidity warning.
- **Labor/inflation/valuation:** unemployment is `4.1%`, the 5-year breakeven is `2.21%`, Shiller P/E is `42.65`, and Fear & Greed is `66.74`. Labor is stable and inflation expectations are contained, but broad valuation and risk appetite leave little margin for error.

### Inference

Situation 3 favors liquidity, high free cash flow, low leverage, and valuation discipline. The sharp deterioration in the 30-day reserve-liquidity signal raises the multiple-compression risk even though tight credit spreads and low VIX argue against an immediate systemic-stress call. The actionable posture remains selective holding rather than adding broad index beta or expensive long-duration exposure.

## What Changed

- Versus August 13, reserve liquidity fell `$18.42B`: Fed assets rose about `$11.39B`, TGA increased about `$30.08B`, and RRP fell about `$0.27B`. The TGA build dominated. The 30-day contraction deepened from `$95.97B` to `$185.47B` as both the current level and rolling comparison changed.
- The 10Y and 2Y yields each fell `2 bps`, to `4.68%` and `4.20%`; the real-yield proxy stayed `2.44%`. The 10Y–3M spread narrowed `5 bps` to `+76 bps`.
- HY OAS tightened `1 bp`, IG OAS tightened `1 bp`, NFCI held near `-0.58`, and VIX edged down to `14.50`. Financial stress remains unconfirmed.
- Fear & Greed rose from `62` to `66.74` and Shiller P/E increased from `42.34` to `42.65`, strengthening the anti-chasing valuation warning.
- WTI recovered `$0.39` to `$81.81`; copper was essentially flat near `$6.58`. Energy retains limited trend support, but not enough for a broad-sector buy.
- HBM multiples rose to `10.75x` forward P/E and `24.81x` EV/EBITDA. Physical AI remains expensive at `38.19x` and `59.17x`; AI compute is `22.49x` and `41.85x`. Constituent history improved to 11 observations versus the required 60.

## Sector Actions

| Sector / theme | Action | Confidence | Evidence, risk, and actionable conclusion |
|---|---|---:|---|
| Technology (XLK) | **HOLD / CAUTION** | High | Score `-4`; contracting liquidity, a `2.44%` real yield, extreme broad valuation, and missing valuation percentile argue against adding. |
| Financials (XLF) | **HOLD / CAUTION** | Moderate-Low | Score `+1` and benign broad credit help, but bank funding, deposits, capital, charge-offs, loan quality, and CCC evidence remain absent. |
| Healthcare (XLV) | **HOLD** | Moderate | Defensive demand and stable labor support holding; valuation and company-quality gates remain incomplete. |
| Energy (XLE) | **HOLD / SELECTIVE BUY** | Moderate-Low | WTI is above `$80`, but contracting liquidity and incomplete demand, valuation, and producer cash-flow evidence block a broad buy. Review only low-leverage, high-free-cash-flow producers. |
| Industrials (XLI) | **HOLD / CAUTION** | Moderate | Liquidity contraction and flat copper outweigh structural themes until valuation and earnings revisions confirm. |
| Consumer discretionary (XLY) | **HOLD / CAUTION** | Moderate-High | Score `-3`; restrictive liquidity, greed sentiment, and broad valuation argue against adding. |
| Consumer staples (XLP) | **HOLD** | Moderate | Defensive demand supports holding; missing valuation evidence blocks accumulation. |
| AI compute | **HOLD / CAUTION** | High | Score `-4`; below-norm forward P/E is offset by `41.85x` EV/EBITDA, restrictive real yields, and incomplete histories. |
| HBM / memory | **HOLD / CAUTION** | Moderate | Forward P/E is about 33% below the `16.0x` norm, but `24.81x` EV/EBITDA and failed peer, history, balance-sheet, and earnings-quality gates prevent promotion. |
| Physical AI / robotics | **SELL / TRIM** | High | Score `-4`, restrictive liquidity, `38.19x` forward P/E, and `59.17x` EV/EBITDA support trimming. |
| Power / grid / cooling | **HOLD / CAUTION** | Moderate | Structural demand is offset by restrictive conditions and mixed multiples; constituent peer/history evidence is insufficient. |

### Mechanical Recommendation Overrides

1. The automated quadrant table calls Financials “favored,” but the sector evidence is `NEUTRAL`. Broad spreads cannot replace bank-specific funding and credit-quality evidence. Corrected view: **HOLD / CAUTION — Moderate-Low**.
2. Physical AI / Robotics remains mechanically `NEUTRAL` despite score `-4`, restrictive real yields, and `59.17x` EV/EBITDA. Corrected view: **SELL / TRIM — High**.
3. HBM and Datacenter Cooling are labeled “Undervalued / Discounted Super-Cycle,” but headline P/E discounts conflict with elevated EV/EBITDA and insufficient peer/history evidence. Corrected view: **HOLD / CAUTION — Moderate** for both.

## Single-Stock Watchlist

**No names are promoted.** `MU`, `WDC`, and `EOG` remain research priorities only. The engine has 11 historical relative observations versus the required 60, and peer, balance-sheet, earnings-quality, and catalyst checks remain incomplete.

## Invalidation Triggers

- **Further downgrade:** reserve contraction persists or deepens; HY OAS exceeds `4.5%` or widens rapidly; CCC or bank stress broadens; NFCI turns positive; VIX sustains above `25`; labor weakens; or earnings revisions deteriorate while real yields stay restrictive.
- **Upgrade:** the 30-day liquidity change turns positive; DFF falls at least `10 bps`; labor remains stable; CCC and bank-credit evidence stays benign; and current valuation/earnings data support risk taking.
- **Energy upgrade:** WTI holds above `$80` with demand and producer free-cash-flow confirmation. Revert to plain **HOLD / CAUTION** if oil loses that level without supportive demand evidence.
- **HBM upgrade:** constituent evidence confirms the discount with acceptable balance sheets, earnings revisions, catalysts, comparable peers, and sufficient history.

## Freshness Check

- **GitHub Action:** [Daily Macro Analysis & Deploy](https://github.com/bronson113/macro_analysis/actions/runs/31795798888) completed successfully on `2026-08-14`; collection, freshness validation, web tests, production build, data commit, and Pages deployment passed.
- **Automated state:** report date `2026-08-14`; raw payload date `2026-08-14`, generated `2026-08-14 11:23:28 UTC`; automated parent commit [`afb1539`](https://github.com/bronson113/macro_analysis/commit/afb1539b404ad084a67fd238dd66fae92a175321).
- **Core gate:** PASS. All source-health records are `CURRENT` and non-stale. Fed assets and TGA are dated `2026-08-12`; DFF, Treasury yields, and credit spreads `2026-08-11` to `2026-08-12`; RRP and curve spreads `2026-08-13`; NFCI `2026-08-07`; market overlays `2026-08-13` to `2026-08-14`. These lags match source frequencies.
- **Missing/limited inputs:** the public raw JSON omits DFF, 10Y–3M, 10Y breakeven, CCC OAS, Sahm Rule, and the 30-day liquidity decomposition. Sector valuation percentiles and bank-specific credit/funding evidence remain unavailable; constituent histories do not meet the 60-observation requirement.

## Repo Follow-Up

**Issue:** ecosystem labels can outrun multiple-consistency, history, and quality gates; Financials can appear “favored” without bank evidence; and several decision fields are absent from the public raw JSON.

**Proposed Codex task:** require stable constituent coverage plus multiple-consistency, minimum-history, and quality gates before “Discounted Super-Cycle”; gate Financials wording on bank-specific evidence; and export the omitted policy-rate, curve, credit, and liquidity-decomposition fields.
