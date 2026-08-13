# 2026-08-13 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Macro Read

### Evidence

- **Active quadrant: Situation 3 — restrictive policy + reserve-liquidity contraction.** DFF is `3.63%`, up `1 bp` over 30 days and classified `HOLDING_RESTRICTIVE`; the real-yield proxy is `2.44%`. Policy stance comes from policy-rate evidence, not the yield curve.
- **Reserve liquidity:** `$5,818.52B`, down `$95.97B` over 30 days: Fed assets `$6,748.57B` minus TGA `$929.33B` minus RRP `$0.72B`, normalized to billions. The small daily improvement came from lower RRP, not Fed asset purchases, so this is not QE.
- **Yield curve:** 10Y–2Y is `+48 bps`; 10Y–3M is `+81 bps`. Positive slopes remove the inversion signal but do not override restrictive policy or the negative 30-day liquidity direction.
- **Credit/volatility:** HY OAS is `2.72%`, IG OAS `0.41%`, NFCI `-0.58`, and VIX `14.59`. Credit and volatility remain benign; systemic stress does not confirm the liquidity warning.
- **Labor/inflation/valuation:** unemployment is `4.1%`, the 5-year breakeven is `2.24%`, Shiller P/E is `42.34`, and Fear & Greed is `62`. Labor is stable and inflation expectations are contained, but broad valuation remains extreme.

### Inference

Situation 3 still favors liquidity, high free cash flow, low leverage, and valuation discipline. Tight credit spreads and low volatility reduce immediate crash risk, but they do not create a broad buy signal while reserve liquidity contracts and real yields remain restrictive. The actionable posture is selective holding rather than adding index beta or expensive long-duration exposure.

## What Changed

- Versus August 12, reserve liquidity rose only `$0.53B` and the 30-day contraction narrowed by `$0.52B`, entirely because RRP fell from `$1.25B` to `$0.72B`; Fed assets and TGA were unchanged.
- The 10Y yield fell `2 bps` to `4.70%`, the 2Y fell `3 bps` to `4.22%`, and the real-yield proxy eased `1 bp` to `2.44%`. Duration pressure remains restrictive.
- HY OAS widened `2 bps` and IG OAS `1 bp`, while NFCI improved to `-0.58` and VIX fell `0.78` to `14.59`. The net risk signal remains benign but complacent.
- WTI fell `$2.00` to `$81.42` and copper declined about `1.5%` to `$6.58`, weakening yesterday's commodity confirmation without breaking it.
- AI compute is `22.43x` forward P/E and `41.74x` EV/EBITDA; HBM is `10.10x` and `23.32x`. Physical AI's forward P/E fell to `37.93x` because TSLA lacks a valid current multiple, not because the whole group became cheaper; EV/EBITDA remains `57.87x`. Constituent history improved from nine to ten observations, still far below the required 60.

## Sector Actions

| Sector / theme | Action | Confidence | Evidence, risk, and actionable conclusion |
|---|---|---:|---|
| Technology (XLK) | **HOLD / CAUTION** | High | Score `-4`; contracting liquidity, a `2.44%` real yield, and missing valuation percentile argue against adding. |
| Financials (XLF) | **HOLD / CAUTION** | Moderate-Low | Score `+1` and benign broad credit help, but bank funding, deposits, capital, charge-offs, loan quality, and CCC evidence are absent. |
| Healthcare (XLV) | **HOLD** | Moderate | Defensive demand and stable labor support holding; valuation and company-quality gates remain incomplete. |
| Energy (XLE) | **HOLD / SELECTIVE BUY** | Moderate-Low | WTI remains above `$80`, but today's oil and copper declines reduce confirmation. Review only low-leverage, high-free-cash-flow producers pending valuation and demand evidence. |
| Industrials (XLI) | **HOLD / CAUTION** | Moderate | Contracting liquidity and weaker copper outweigh structural themes until valuation and earnings revisions confirm. |
| Consumer discretionary (XLY) | **HOLD / CAUTION** | Moderate-High | Score `-3`; restrictive liquidity, greed sentiment, and broad valuation argue against adding. |
| Consumer staples (XLP) | **HOLD** | Moderate | Defensive demand supports holding; missing valuation evidence blocks accumulation. |
| AI compute | **HOLD / CAUTION** | High | Score `-4`; below-norm forward P/E is offset by `41.74x` EV/EBITDA, restrictive real yields, and incomplete histories. |
| HBM / memory | **HOLD / CAUTION** | Moderate | `10.10x` forward P/E is about 37% below the `16.0x` norm, but peer, history, balance-sheet, and earnings-quality gates fail. |
| Physical AI / robotics | **SELL / TRIM** | High | Score `-4`, restrictive liquidity, and `57.87x` EV/EBITDA support trimming; the lower group P/E is distorted by missing TSLA data. |
| Power / grid / cooling | **HOLD / CAUTION** | Moderate | Structural demand is offset by restrictive conditions and mixed multiples; constituent peer/history evidence is insufficient. |

### Mechanical Recommendation Overrides

1. The automated quadrant table calls Financials “favored,” but the sector evidence is `NEUTRAL`. Broad spreads cannot replace bank-specific funding and credit-quality evidence. Corrected view: **HOLD / CAUTION — Moderate-Low**.
2. Physical AI / Robotics remains mechanically `NEUTRAL` despite score `-4`, restrictive real yields, and `57.87x` EV/EBITDA. Its lower forward P/E reflects missing TSLA data, so it is not clean evidence of de-rating. Corrected view: **SELL / TRIM — High**.
3. HBM and Datacenter Cooling are labeled “Undervalued / Discounted Super-Cycle,” but current P/E discounts conflict with elevated EV/EBITDA and insufficient peer/history evidence. Corrected view: **HOLD / CAUTION — Moderate** for both.

## Single-Stock Watchlist

**No names are promoted.** `MU`, `WDC`, and `EOG` remain research priorities only. The engine has ten historical relative observations versus the required 60, and peer, balance-sheet, earnings-quality, and catalyst checks remain incomplete.

## Invalidation Triggers

- **Further downgrade:** reserve contraction deepens; HY OAS exceeds `4.5%` or widens rapidly; CCC or bank stress broadens; NFCI turns positive; VIX sustains above `25`; labor weakens; or earnings revisions deteriorate while real yields stay restrictive.
- **Upgrade:** the 30-day liquidity change turns positive; DFF falls at least `10 bps`; labor remains stable; CCC and bank-credit evidence stays benign; and current valuation/earnings data support risk taking.
- **Energy upgrade:** WTI holds above `$80` with demand and producer free-cash-flow confirmation. Revert to plain **HOLD / CAUTION** if oil loses that level without supportive demand evidence.
- **HBM upgrade:** constituent evidence confirms the discount with acceptable balance sheets, earnings revisions, catalysts, comparable peers, and sufficient history.

## Freshness Check

- **GitHub Action:** [Daily Macro Analysis & Deploy](https://github.com/bronson113/macro_analysis/actions/runs/31695131137) completed successfully on `2026-08-13`; collection, freshness validation, web tests, production build, data commit, and Pages deployment passed.
- **Automated state:** report date `2026-08-13`; raw payload date `2026-08-13`, generated `2026-08-13 11:24:42 UTC`; automated parent commit [`464894c`](https://github.com/bronson113/macro_analysis/commit/464894c07d109deeb4e2a9e331920bcf74080987).
- **Core gate:** PASS. All source-health records are `CURRENT` and non-stale. Fed assets and TGA are dated `2026-08-05`; DFF, Treasury yields, and credit spreads `2026-08-10` to `2026-08-11`; RRP and curve spreads `2026-08-12`; NFCI `2026-08-07`; market overlays `2026-08-12` to `2026-08-13`. These lags match source frequencies.
- **Missing/limited inputs:** the public raw JSON omits DFF, 10Y–3M, 10Y breakeven, CCC OAS, Sahm Rule, and the 30-day liquidity decomposition. Sector valuation percentiles and bank-specific credit/funding evidence remain unavailable; constituent histories do not meet the 60-observation requirement.

## Repo Follow-Up

**Issue:** ecosystem labels can outrun multiple-consistency, history, and quality gates; missing multiples can materially shift group averages; Financials can appear “favored” without bank evidence; and the August 12 Pages run failed to retrieve an artifact that the run itself listed.

**Proposed Codex task:** require stable constituent coverage plus multiple-consistency, minimum-history, and quality gates before “Discounted Super-Cycle”; surface missing-multiple composition changes; gate Financials wording on bank-specific evidence; export omitted macro/credit fields; and split Pages artifact creation from deployment with a deployment-only retry path.
