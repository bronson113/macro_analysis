export const descriptions = {
  // Stat Cards
  fed_total_assets: "The total value of assets held by the Federal Reserve. Expanding assets generally adds liquidity to the financial system (often referred to as QE), while shrinking assets removes liquidity (QT).",
  tga_balance: "The Treasury General Account. This is the US government's checking account at the Fed. When the TGA balance rises (tax collection/debt issuance), it drains liquidity from the banking system. When it falls (government spending), it adds liquidity.",
  treasury_10y: "The 10-Year Treasury Yield. Often considered the benchmark for global borrowing costs. Rising 10Y yields pressure valuations of long-duration assets like tech stocks.",
  spread_10y_2y: "The difference between 10-Year and 2-Year Treasury yields. A negative spread (inverted yield curve) is historically a reliable warning sign of tightening financial conditions and impending recession.",
  
  // Trend Graphs
  net_liquidity: "Net Liquidity is calculated as (Fed Total Assets) - (TGA Balance) - (Reverse Repo). It measures the actual cash available in the financial system to support risk assets. The S&P 500 tends to follow the trajectory of this liquidity proxy.",
  yield_curve: "Yield Curve Dynamics shows the relationship between short-term (2Y) and long-term (10Y) borrowing costs. When the 2Y is higher than the 10Y, the curve is 'inverted'. When it rapidly 'un-inverts' (steepens), it often signals the Fed is cutting rates because something in the economy broke.",
  market_stress: "Market Stress tracks the VIX (equity volatility / 'fear gauge') and the DXY (US Dollar Index). A soaring Dollar often tightens global financial conditions, while a spiking VIX indicates panic. Both rising together is a toxic combination for risk assets.",
  inflation_policy: "Inflation (CPI YoY) vs Fed Funds Rate. This tracks how restrictive the Fed's policy is relative to inflation. If the Fed Funds Rate is significantly above CPI, policy is 'restrictive'. If it's below, policy is 'accommodative'.",

  // Structured regime overview
  policy_level: "Current policy level is based on the real-policy gap: real policy rate minus the neutral real rate (r-star). A gap above +0.50 percentage points is restrictive; below -0.50 points is accommodative.",
  liquidity_level: "Current reserve-liquidity level is the normalized reserve-liquidity proxy as a share of GDP compared with a trailing historical sample. Below the 40th percentile is scarce; above the 60th percentile is abundant.",
  regime_momentum: "Policy and reserve-liquidity momentum are separate 30-day and 90-day overlays. Momentum describes change; it does not replace the current level or select the quadrant.",
  regime_consensus: "Market consensus is an optional, forward-looking overlay. It includes policy and, when available, Fed balance-sheet expectations; unavailable or stale consensus never changes the current state."
};
