# 2026-08-20 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice.*

## Macro Read

- **Current State:** **Situation 2 — accommodative policy + scarce reserve liquidity.** The policy classification comes from the real-policy gap, not the yield curve: DFF is `3.63%`, core PCE YoY is `3.287%`, r-star is `1.057%`, and the resulting policy gap is `-0.714 pp` (accommodative). Normalized reserve liquidity is `17.859% of GDP`, at the `13.8th` historical percentile versus P40 `20.260` and P60 `21.420`, so the level is scarce.
- **Momentum:** Policy is `STABLE` over 30 days (`0.000 pp`) but `TIGHTENING` over 90 days (`+0.145 pp`). Normalized liquidity is `DETERIORATING` over both 30 days (`-0.453 pp of GDP`) and 90 days (`-0.329 pp`). The latest dollar proxy is about `$5,800.23B`, down `$185.34B` over 30 days. Fed assets are `$6,759.95B`, TGA `$959.40B`, and latest RRP `$0.32B`; this is reserve-liquidity contraction, not QE.
- **Market Consensus:** The June 3 NY Fed SME survey expects DFF at `3.63%` around six months ahead (`STABLE`) and Fed assets at `$6,824B` (`EXPANDING`). That is a Fed balance-sheet forecast, not a net-liquidity forecast; it does not change Situation 2.
- **Interpretation:** The 10Y–2Y curve is positive at `+46 bp` and 10Y–3M at `+79 bp`. Un-inversion removes the inversion signal but can mark a cycle transition; it is not evidence that current policy is restrictive or easy. Credit remains benign—HY OAS `2.75%`, IG OAS `0.42%`, NFCI `-0.59`—and VIX is low at `15.15`. Unemployment is `4.1%`, core PCE YoY `3.287%`, and the 5Y breakeven `2.28%`: no acute credit/labor break, but inflation and a `2.41%` real-yield proxy still constrain duration. Shiller P/E `42.15` and Fear & Greed `57` argue against chasing broad beta.
- **Data Quality:** Overall `PARTIAL`. Core level inputs pass their freshness/history gates, but EFFR–IORB averages `-2 bp` and triggers one reserve-pressure flag; SOFR–IORB at `-1.6 bp` does not. One flag lowers confidence without withholding the quadrant. Sector valuation percentiles are missing for all 11 sectors, and most constituent histories have only 5 valid relative observations versus 60 required.

**Research posture:** selective defense and quality, not broad risk-on. Accommodative policy is offset by scarce and deteriorating reserve liquidity, high real yields, and expensive broad valuation.

## What Changed

- Versus August 19, the quadrant and momentum labels are unchanged. The latest proxy slipped about `$0.17B` as RRP rose from roughly `$0.15B` to `$0.32B`; the 30-day contraction deepened marginally from `-$185.18B` to `-$185.34B`.
- The 10Y yield eased `1 bp` to `4.71%`; the 2Y held at `4.19%`. The 10Y–2Y spread narrowed `6 bp` to `+46 bp`, and 10Y–3M narrowed `6 bp` to `+79 bp`.
- HY OAS widened `5 bp` to `2.75%`; IG OAS was unchanged and NFCI loosened slightly. This is not a credit-stress signal.
- VIX fell from `15.82` to `15.15`, while Fear & Greed rose from `53.57` to `57`. WTI rose from `$84.93` to `$86.67`; Shiller P/E increased from `42.06` to `42.15`.
- AI/HBM/cooling headline P/E multiples fell, but EV/EBITDA remains high and the valuation/history gates remain incomplete; the evidence did not improve enough to promote an action.

## Sector Actions

| Sector / theme | Research action | Confidence | Judgment |
|---|---|---:|---|
| Healthcare (XLV) | **HOLD / SELECTIVE BUY** | Moderate | Situation 2 favors defensive cash flow, but missing valuation percentiles and company-quality confirmation block a broad BUY. |
| Consumer Staples (XLP) | **HOLD / SELECTIVE BUY** | Moderate | Defensive demand and low volatility fit; stretched broad valuation caps conviction. |
| Energy (XLE) | **HOLD / SELECTIVE BUY** | Moderate-Low | WTI at `$86.67` supports review, but demand, producer FCF, and sector valuation evidence are incomplete. |
| Financials (XLF) | **HOLD** | Moderate-Low | Benign spreads help, but bank funding, deposit, capital, and credit-quality evidence are not sufficient for accumulation. |
| Technology (XLK) | **HOLD / CAUTION** | High | Scarce/deteriorating liquidity, `2.41%` real yield, and missing sector valuation percentiles outweigh accommodative policy. |
| Consumer Discretionary (XLY) | **HOLD / CAUTION** | Moderate-High | Expensive broad valuation and weak liquidity support make incremental beta unattractive. |
| Industrials (XLI) | **HOLD / CAUTION** | Moderate | Positive curve and commodities are not enough without valuation and earnings-revision confirmation. |
| AI Compute / HBM / Cooling | **HOLD / CAUTION** | High | Lower forward P/E conflicts with EV/EBITDA of roughly `24x–39x`; “discounted super-cycle” is not established. |
| Physical AI / Robotics | **SELL / TRIM** | Moderate-High | `37.32x` forward P/E and `59.25x` EV/EBITDA are poor compensation for the liquidity and real-yield backdrop; apply tax friction before any realization. |
| Critical Materials / Magnets | **HOLD / CAUTION** | Moderate | Commodity support exists, but `41.03x` forward P/E and incomplete quality evidence limit upside confidence. |

### Mechanical Recommendation Overrides

1. The yield table labels the `3.63%` policy rate as **“HOLDING_RESTRICTIVE.”** That conflicts with the framework rule that current policy must be classified from the real-policy gap, which is `-0.714 pp`. **Corrected view: ACCOMMODATIVE current policy; the `2.41%` 10Y real yield is a separate duration-risk diagnostic.**
2. AI Compute, HBM, and Datacenter Cooling are labeled **“Undervalued / Discounted Super-Cycle”** even though EV/EBITDA remains high and sector valuation percentiles, long histories, balance-sheet quality, and earnings confirmation are missing. That violates the evidence gate against treating missing evidence as favorable. **Corrected view: HOLD / CAUTION pending multiple consistency and quality confirmation.**
3. The report simultaneously says **“No meaningful sector differentiation”** while publishing favored/disfavored sector lists. Those lists are quadrant hypotheses, not validated sector conclusions. **Corrected view: use them only to prioritize research; no broad BUY / ACCUMULATE call is supported.**

## Single-Stock Watchlist

**No single-stock names qualify for promotion.** The sector-risk and valuation/quality gates are not complete, and most cohorts have only 5 valid relative-history observations versus 60 required. Existing bellwethers remain research inputs, not an actionable watchlist.

## Invalidation Triggers

- **Upgrade risk posture** if normalized liquidity turns `IMPROVING` over 30 days, the scarce level moves above P40, the reserve-pressure flag clears, credit remains benign, and sector valuation/earnings evidence improves.
- **Downgrade risk posture** if HY OAS moves above `4.5%` or widens rapidly, NFCI turns positive, VIX sustains above `25`, unemployment/claims weaken materially, or liquidity deterioration accelerates.
- **Policy reclassification** requires the real-policy gap to move above `-0.50 pp`; nominal-rate or yield-curve moves alone do not change the current state.
- **Defensive-sector upgrade** requires acceptable valuation percentiles plus constituent balance-sheet, earnings-quality, and catalyst confirmation.
- **Energy upgrade** requires continued oil strength with demand and producer free-cash-flow confirmation; a decisive loss of the `$80` area weakens the selective-buy hypothesis.
- **AI/HBM/cooling upgrade** requires consistent forward P/E and EV/EBITDA evidence, sufficient history, strong balance sheets, and improving revisions/catalysts.

## Freshness Check

- **Daily GitHub Action:** successful through the August 20 automated data commit and fresh report publication; the connector did not expose a run ID.
- **Report date:** `2026-08-20`.
- **Raw payload:** date `2026-08-20`; generated `2026-08-20 11:03:09 UTC`.
- **Automated data commit:** `55ed047c6527fbee433b4ea57c58e39c57d50cca`.
- **Known gaps/conflicts:** one EFFR–IORB pressure flag; missing sector valuation percentiles; insufficient constituent history; duplicated EFFR–IORB reason text; and inconsistent RRP dates/values between the normalized level record (`0.725B` on August 12) and the latest proxy table (`0.317B` on August 19).

## Repo Follow-Up

**Issue:** deterministic presentation can contradict the controlling state and overstate valuation confidence.

**Proposed Codex task:** make the yield-table stance reuse `current_state.policy`; gate “Undervalued / Discounted Super-Cycle” on consistent forward P/E and EV/EBITDA, valuation-percentile/history, balance-sheet, and earnings-quality checks; label favored/disfavored lists as unvalidated quadrant hypotheses when the sector evidence gate says no differentiation; deduplicate data-quality reasons; and align the RRP observation used in the normalized level with the latest proxy table or disclose the mixed-date basis.
