# 2026-11-20 — FRESH

*LLM macro risk review for a tax-aware 3-month to 1-year horizon. Research posture only; not personalized financial advice. The controlling Defiant Gatekeeper framework uses WATCH/NEUTRAL/AVOID research states and forbids execution-style BUY/SELL/ACCUMULATE/TRIM outputs.*

## Macro Read

### Current State

- **Situation 0 — NO ACTIONABLE MACRO QUADRANT.** Policy is **NEUTRAL** and reserve liquidity is **SCARCE**. The policy gap is **-0.250 pp**, inside the inclusive ±0.50 pp neutral band, so the framework withholds Situations 1–4.
- **Policy level:** DFF **3.88%**, core PCE YoY **3.121%**, r-star **1.009%**, real policy rate **0.759%**. This classification comes from policy-rate evidence, not the yield curve.
- **Reserve-liquidity level:** Fed assets **$6,741.452B** minus TGA **$892.310B** minus ON RRP of roughly **$0.4B** gives about **$5,848.74B**. Normalized liquidity is **17.718% of GDP**, at the **14.8th percentile**, below the **20.026% P40** scarcity threshold.
- **Liquidity source:** versus the prior weekly inputs, Fed assets fell while TGA also fell materially; the net proxy rose only about **$2.34B** from the prior report. That is a small reserve-liquidity improvement, **not QE**.
- **Yield curve:** 10Y **5.07%**, 2Y **4.80%**, 10Y–2Y **+28 bp**, 10Y–3M **+70 bp**, with a **2.91%** 10Y real-yield proxy. The curve is positive, but absolute real and nominal yields remain a valuation/duration headwind.
- **Credit / volatility:** HY OAS **3.52%**, IG OAS **0.47%**, NFCI **-0.50**. Credit is not signaling systemic stress, but **VIX is 32.08**, which is a materially defensive volatility regime rather than complacency.
- **Broad valuation / sentiment:** Shiller P/E is **37.86** (very expensive) while CNN Fear & Greed is **11.10** (extreme fear). Cheap sentiment does not offset stretched broad valuation without stronger liquidity, credit, and earnings confirmation.

### Momentum

- **Policy 30d:** **STABLE**, change **+0.000 pp**.
- **Policy 90d:** **TIGHTENING**, change **+0.163 pp**.
- **Liquidity 30d:** **IMPROVING**, change **+0.123 pp of GDP**.
- **Liquidity 90d:** **IMPROVING**, change **+0.121 pp of GDP**.
- The momentum improvement is an overlay only; it does not change the current **SCARCE** liquidity level or Situation 0.

### Market Consensus

- **Policy consensus:** **TIGHTENING**, expected DFF **4.38%**.
- **Fed balance-sheet consensus:** **EXPANDING**, expected Fed assets **$6,802B**.
- Survey reference/publication: **2026-10-14**, target **2027-04-28**, six-month horizon, quality **OK**.
- This is a Fed-assets expectation only; it does not forecast TGA or RRP and therefore does not reclassify reserve liquidity.

### Interpretation

The 3–12 month posture remains cautious. Current-state liquidity is still scarce, policy is neutral rather than accommodative, and broad valuation is expensive. The positive change is the flip in 30-day liquidity momentum from deteriorating to improving after refreshed weekly inputs. The offset is a sharp deterioration in risk appetite: VIX is above 30 and Fear & Greed is in extreme fear. Credit spreads remain below stress thresholds, so this is not yet a credit-crisis signal. Prefer evidence quality, balance-sheet resilience, and valuation discipline over broad-beta extrapolation.

### Data Quality

Overall quality is **PARTIAL**. Policy evidence is valid; liquidity level is valid but money-market corroboration flags pressure through EFFR–IORB. Core inputs are within the skill's freshness limits by observation date. The automated age display remains misleading for slower-frequency series: core PCE is dated **2026-09-01** and r-star **2026-04-01**, yet the report prints age 0 days for both. Momentum labels are also published with prior date/value shown as N/A, which weakens auditability.

## What Changed

- **Liquidity momentum improved:** 30-day normalized liquidity flipped from **DETERIORATING (-0.070 pp)** on November 19 to **IMPROVING (+0.123 pp)** on November 20; 90-day liquidity remained improving and edged from **+0.114 pp** to **+0.121 pp**.
- **Current liquidity level barely changed:** normalized liquidity moved from **17.712%** to **17.718% of GDP**, still deeply scarce; the reserve-liquidity proxy increased by only about **$2.34B**.
- **Risk appetite worsened:** Fear & Greed fell from **20.63** to **11.10** (both extreme fear), while current VIX is **32.08**.
- **Credit softened but remains non-stressed:** HY OAS widened from **3.47%** to **3.52%**; IG OAS stayed **0.47%**.
- **Valuation eased only marginally:** Shiller P/E fell from **38.63** to **37.86**, still very expensive.
- **Rates eased slightly:** 10Y fell from **5.10%** to **5.07%**; the curve remains positively sloped.

## Sector Actions

The controlling repo skill does not permit BUY / SELL / ACCUMULATE / TRIM execution labels. Using the required evidence contract instead:

- **All 11 sectors: NEUTRAL research posture; confidence low-to-moderate.**
- **No meaningful sector differentiation from current evidence.**
- Situation 0 removes the macro-quadrant contribution, and current dispersion does not support a robust sector ranking despite isolated constituent valuation signals.

## Single-Stock Watchlist

**No name is promoted to the LLM watchlist today.** The automated constituent screen flags **NVDA** and **CAT** as valuation WATCH candidates because relative FPE/EVE discounts exceed 20%, but the Defiant Gatekeeper requires the full stock gate: no obvious balance-sheet, earnings, legal, or structural break, plus an acceptable sector posture. The published evidence does not complete those quality checks, so promotion is withheld.

## Invalidation Triggers

- **Bullish reclassification:** policy gap moves below **-0.50 pp** and/or normalized reserve liquidity rises out of the scarce band, with improving money-market corroboration and no credit deterioration.
- **Risk-off escalation:** HY OAS approaches/exceeds **5%**, NFCI turns materially positive, or reserve liquidity resumes a sustained deterioration while VIX remains elevated.
- **Valuation confirmation:** broad multiples compress materially or earnings revisions improve enough to offset the current real-yield burden.
- **Liquidity thesis failure:** the 30-day improvement reverses below **-0.05 pp of GDP** or is shown to be only a timing artifact from TGA/RRP alignment.

## Freshness Check

- **Latest scheduled GitHub Action:** Daily Macro Analysis & Deploy run **44795540328**, completed **successfully**.
- **Automated report date:** **2026-11-20**.
- **Raw payload date:** **2026-11-20**; generated **2026-11-20T18:45:20Z**.
- **Latest automated data commit before this note:** ee7b4e661dd242b76ee334f4e3e48cfe39afcb65.
- Core level inputs remain within framework freshness limits. Overall quality remains **PARTIAL** because of reserve-pressure corroboration and report-audit issues described above.

## Repo Follow-Up

1. **Policy wording bug:** the detailed rates table still labels DFF stance as HOLDING_RESTRICTIVE even though the controlling framework classifies the real-policy gap as **NEUTRAL**. **Codex task:** derive display wording from the same real-policy-gap classification used by Current State, and add a regression test that prevents restrictive wording when the gap is inside ±0.50 pp.
2. **Input-age bug:** the report prints core PCE and r-star ages as 0 days despite observation dates of **2026-09-01** and **2026-04-01**. **Codex task:** compute displayed ages from selected observation dates, with tests for slow-frequency series.
3. **Momentum auditability:** 30/90-day labels show prior date/value as N/A despite numeric changes being emitted. **Codex task:** persist and render the actual prior observation date/value used for each momentum calculation, and fail presentation tests when a classified momentum reading lacks its prior anchor.
4. **Constituent gate completeness:** valuation WATCH states can appear without explicit balance-sheet/earnings/legal/structural-break evidence. **Codex task:** add explicit stock-gate evidence fields so LLM and deterministic outputs can distinguish a valuation screen from a fully cleared single-stock review.
