---
name: defiant-gatekeeper-macro-news-analysis
description: Evaluate daily macro data, Fed policy stance, reserve-liquidity direction, yield curve risk, credit stress, valuations, and sector recommendations for a tax-aware 3M-1Y investment horizon.
---

# Defiant Gatekeeper Macro Sector Recommendation Skill

Use this skill when producing the morning macro report or refining the recommendation engine. The goal is a useful sector action posture for a 3-month to 1-year horizon, not a deterministic market forecast.

This framework is a **risk-liquidity heuristic**. It combines Fed policy-rate stance, reserve-liquidity direction, yield-curve risk, credit spreads, inflation/labor data, valuation, and sector-specific catalysts. Treat every recommendation as conditional on data quality and confidence.

## Non-Negotiable Guardrails

1. **Never force a quadrant when core data is missing.**
   If policy-rate trend or 30-day reserve-liquidity direction is unavailable, return `INSUFFICIENT DATA` and default broad sector actions to `HOLD` unless independent valuation or risk controls override.

2. **Do not confuse the yield curve with Fed policy.**
   Fed policy stance must come from the federal funds target/EFFR/DFF trend or explicit FOMC communication. A positive or negative yield curve is a recession/financial-conditions signal, not proof that the Fed is cutting or hiking.

3. **Do not label all liquidity expansion as QE.**
   QE means Fed asset purchases for accommodation, market functioning, or reserve management. The net-liquidity proxy can rise because Fed assets rise, TGA falls, or RRP falls. Call it `reserve liquidity expansion`, not QE, unless the source data confirms asset purchases.

4. **Report direction, not just level.**
   `Fed Assets - TGA - RRP` is a level. “Expanding” requires a positive change over a defined lookback, normally 30 calendar days or the nearest available weekly point.

5. **Separate macro tailwind from valuation discipline.**
   A favored macro quadrant does not automatically justify buying an expensive sector. Check forward P/E, EV/EBITDA, earnings yield vs Treasury yield, credit stress, and sector news before issuing `BUY`.

6. **Recommendations must include confidence.**
   Every sector output should include action, conviction, rationale, and the data that would invalidate the call.

## Core Data Inputs

Use these preferred U.S. sources when available:

- Fed assets: `WALCL`, FRED, millions of USD.
- Treasury General Account: `WDTGAL` preferred for Wednesday level, or `WTREGEN` for weekly average, FRED, millions of USD.
- Overnight Reverse Repo: `RRPONTSYD`, FRED, billions of USD.
- Policy rate: daily `DFF` or `EFFR`; use target-range/FOMC communication when available.
- Yield curve: use both `T10Y2Y` and `T10Y3M`; `T10Y3M` is the classic NY Fed recession-probability spread.
- Credit stress: high-yield OAS, investment-grade OAS, CCC OAS, and Chicago Fed NFCI.
- Labor/inflation: unemployment, Sahm Rule, payrolls, claims, CPI/PCE, breakevens.
- Market/sector: VIX, DXY, S&P 500, commodities, sector P/E, forward P/E, EV/EBITDA, and major bellwether news.

Normalize all balance-sheet components into billions before computing the liquidity proxy.

## Reserve-Liquidity Proxy

```
reserve_liquidity_b = Fed Assets_b - TGA_b - ON_RRP_b
reserve_liquidity_30d_change_b = current reserve_liquidity_b - nearest value on or before current_date - 30 days
```

Interpretation:

- Positive 30-day change: reserve liquidity expanding.
- Negative 30-day change: reserve liquidity contracting.
- Missing Fed assets, TGA, or RRP: insufficient data.

This proxy approximates reserve supply pressure. It is not the full monetary base, not broad money, and not a complete measure of global liquidity.

## Policy-Rate Stance

Classify policy-rate trend from actual policy-rate data:

- `CUTTING`: 30-day policy-rate change <= -10 bps, or explicit FOMC cut.
- `RAISING`: 30-day policy-rate change >= +10 bps, or explicit FOMC hike.
- `HOLDING`: change is between -10 bps and +10 bps.
- `HOLDING_RESTRICTIVE`: policy rate is flat, but real-yield evidence is restrictive. Use 10Y Treasury minus 10Y breakeven; a 10Y real yield around 1.50% or higher is restrictive enough to enter the restrictive quadrants unless stronger context says otherwise.
- `UNKNOWN`: insufficient policy-rate data.

For the 4-quadrant matrix, `CUTTING` is easing. `RAISING` and `HOLDING_RESTRICTIVE` are restrictive. Plain `HOLDING` is not an actionable quadrant by itself; fall back to valuation, credit, earnings, and tax constraints.

## 4 Macro Situations

Use the matrix as a starting hypothesis, not as the final recommendation.

```
                          RESERVE LIQUIDITY DIRECTION
                      EXPANDING                    CONTRACTING
                  +--------------------------+--------------------------+
 CUTTING/EASING   | Situation 1              | Situation 2              |
                  | Risk-liquidity tailwind  | Late-cycle caution       |
                  +--------------------------+--------------------------+
 RAISING/HAWKISH  | Situation 4              | Situation 3              |
 OR RESTRICTIVE   | Policy/liquidity conflict| Restrictive liquidity    |
 HOLDING          |                          |                          |
                  +--------------------------+--------------------------+
```

### Situation 1: Easing + Reserve Liquidity Expanding

Typical read: risk-liquidity tailwind.

Potentially favored:
- Profitable technology and AI infrastructure.
- Semiconductors and HBM memory.
- Downstream power, grid, cooling, and industrial electrification.
- Consumer discretionary only if labor and credit are not deteriorating.

Risk checks:
- Avoid chasing sectors with stretched valuation, negative equity risk premium, or deteriorating earnings revisions.
- If Sahm Rule or credit stress is flashing, downgrade from `BUY` to `HOLD / SELECTIVE`.

### Situation 2: Easing + Reserve Liquidity Contracting

Typical read: late-cycle or recession-risk caution. The Fed may be easing because growth/labor is weakening while reserve liquidity is still a headwind.

Potentially favored:
- Healthcare.
- Consumer staples.
- Quality dividend/low leverage.
- Gold or precious metals when real-rate or dollar context supports it.

Risk checks:
- Curve un-inversion can be a warning, but do not treat it as automatically bearish. Confirm with labor, credit, earnings, and volatility.
- High-beta unprofitable growth and high-debt small caps need extra scrutiny.

### Situation 3: Hawkish/Holding + Reserve Liquidity Contracting

Typical read: restrictive liquidity and higher multiple-compression risk.

Potentially favored:
- Cash and T-bills.
- Low-leverage, high-free-cash-flow companies.
- Energy only when commodity trend and valuation support it.
- Financials only when credit quality and deposit/funding conditions are stable.

Risk checks:
- Do not blanket-buy financials merely because rates are high. Credit stress, inverted/volatile funding curves, and deposit pressure can dominate net-interest-margin benefits.
- Long-duration growth needs valuation support and resilient earnings to avoid `SELL / TRIM`.

### Situation 4: Hawkish/Holding + Reserve Liquidity Expanding

Typical read: policy/liquidity conflict. This can be reserve management, TGA/RRP mechanics, market-functioning support, or emergency liquidity. It is not automatically stagflation or bailout.

Potentially favored:
- Hard assets and commodity producers if inflation is sticky.
- Energy, copper, gold, and inflation-linked cash flows when real-economy and commodity data confirm.
- Quality cyclicals only if credit stress is contained.

Risk checks:
- Confirm whether liquidity expansion is from Fed assets, TGA drawdown, or RRP runoff.
- Avoid calling it emergency support without evidence from Fed facilities or official communication.

## Recommendation Scoring

For each sector, combine:

- Macro quadrant: tailwind, neutral, or headwind.
- Data quality: OK, partial, insufficient.
- Valuation: forward P/E vs sector norm, EV/EBITDA vs norm, earnings yield vs 10Y Treasury.
- Credit/volatility: HY OAS, CCC OAS, NFCI, VIX.
- Rates and real yields: 10Y yield minus 10Y breakeven.
- Dollar/commodities: DXY, oil, gold, copper.
- Sector-specific catalysts: earnings, supply chain, regulation, credit contagion.
- Tax friction: prefer HOLD unless expected risk/reward clears a meaningful threshold.

Scoring discipline:

- Negative ERP is a rate/valuation headwind, not a standalone sell trigger.
- `SELL / TRIM` from ERP should require both meaningfully negative ERP and valuation stretch versus the sector norm.
- Restrictive real yields should downgrade long-duration growth to `HOLD / CAUTION` unless valuation is also stretched.
- Financials require credit-quality confirmation; do not buy them solely because the macro quadrant favors them.

Recommended action vocabulary:

- `BUY / ACCUMULATE`: macro, valuation, and risk controls align.
- `HOLD / SELECTIVE BUY`: sector ETF is not clearly attractive, but one or two constituents are unusually discounted with acceptable fundamentals.
- `HOLD`: default when signal is mixed or tax friction dominates.
- `HOLD / CAUTION`: stay invested but avoid adding; monitor named risks.
- `SELL / TRIM`: macro headwind plus valuation/risk deterioration.

## Single-Stock Lagging Opportunity Rule

Use single-stock lagging signals only after sector-level risk is acceptable.

A candidate can be flagged when:

- It trades at least 20% cheaper than relevant peers on forward P/E or EV/EBITDA, and
- It is not cheap because of obvious balance-sheet stress, broken earnings, severe litigation/regulatory risk, or structurally declining demand, and
- It belongs to a sector that is at least `HOLD`, not a clear macro `SELL / TRIM`.

Examples to monitor: `MU`, `WDC`, `C`, `BAC`, `MOD`, `EOG`, but do not hard-code them as buys.

## Bellwether News Rules

Track bellwethers as evidence, not as automatic contagion:

- `NVDA`, `AMD`, `AVGO`, `TSM`: AI compute and semiconductor demand.
- `MU`, `WDC`: memory pricing and HBM cycle.
- `JPM`, `BAC`, `C`: credit quality, deposits, capital markets.
- `XOM`, `CVX`, `EOG`: energy supply/demand and cash-flow discipline.
- `TSLA`, `SYM`, `TER`, `ROK`, `ISRG`: physical AI and robotics.

Upgrade conviction only when bellwether news confirms the macro/valuation signal. Downgrade when news contradicts it.

## Morning Workflow

1. Fetch/update data and log failures by source.
2. Verify freshness for all core macro inputs.
3. Compute reserve-liquidity level and 30-day direction.
4. Compute policy-rate stance from actual policy-rate data.
5. Classify macro situation, or return insufficient data.
6. Evaluate yield-curve, Sahm/labor, inflation, credit, volatility, and valuation risk.
7. Generate sector recommendations with action, conviction, rationale, and invalidation trigger.
8. Flag selective single-stock opportunities only after sector and balance-sheet risk checks.
9. In the report, explicitly list missing or stale inputs so the recommendation can be trusted at the right confidence level.

## Source Discipline

Prefer primary sources for macro mechanics: Federal Reserve Board, New York Fed, St. Louis Fed/FRED, Treasury, BLS, BEA, and official company filings. Use financial media for timely context, but do not let headlines override the quantitative framework without confirmation.
