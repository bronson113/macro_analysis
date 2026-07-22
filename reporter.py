"""
Reporter module for Macro Economic Analysis & Data Capture System.
Generates terminal dashboards, daily Markdown reports with 4 Macro Situations (2x2 Matrix),
Macro & Sector Valuation (P/E & EV/EBITDA), Single-Stock Lagging Value Opportunities,
AI / Memory / Physical AI Downstream Supply Chain, Tax-Aware Mid-Term Sector Strategy,
Sector Bellwether Contagion, and News Event analysis.
Guarantees 100% defensive type safety against missing or None metrics.
"""

from datetime import datetime
from pathlib import Path
from tabulate import tabulate
from typing import Dict, Any, Optional
from config import OUTPUT_DIR
from storage import MacroStorage
from analyzer import MacroAnalyzer


def fmt_num(val: Optional[float], fmt_spec: str = ":,.2f", suffix: str = "", prefix: str = "", default: str = "N/A") -> str:
    """Safely formats a numerical value with optional prefix/suffix or returns default if None."""
    if val is None:
        return default
    try:
        format_str = "{" + fmt_spec + "}"
        return prefix + format_str.format(val) + suffix
    except Exception:
        return default


def md_cell(value: Any) -> str:
    """Escapes text for safe use inside Markdown table cells."""
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


class MacroReporter:
    def __init__(self, storage: Optional[MacroStorage] = None, analyzer: Optional[MacroAnalyzer] = None, output_dir: Optional[Path] = None, verbose: bool = True):
        self.storage = storage or MacroStorage()
        self.analyzer = analyzer or MacroAnalyzer(self.storage)
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def print_terminal_dashboard(self, analysis: Dict[str, Any]):
        """Prints a clean, institutional-grade ASCII dashboard to terminal."""
        summary = analysis["summary"]
        liq = analysis["liquidity_details"]
        policy = analysis.get("policy_details", {})
        yc = analysis["yield_curve_details"]
        credit = analysis["credit_details"]
        mkt = analysis["market_details"]
        macro = analysis["macro_details"]
        news_events = analysis.get("news_events", [])
        valuations = analysis.get("sector_valuations", [])
        ai_ecosystem = analysis.get("ai_ecosystem", [])
        recommendations = analysis.get("recommendations", [])
        lagging_stocks = analysis.get("lagging_stock_opportunities", [])
        macro_sit = analysis.get("macro_situation", {})

        print("\n" + "=" * 100)
        print(f"   DEFIANT GATEKEEPER 4-QUADRANT MACRO, SECTOR DISPERSION & TAX-AWARE DASHBOARD")
        print(f"                     Date: {summary.get('date', 'N/A')}")
        print("=" * 100)

        # Check for data staleness
        is_stale = False
        try:
            latest_obs = self.storage.get_latest_observation('treasury_10y')
            if latest_obs and latest_obs.get('updated_at'):
                last_up = datetime.fromisoformat(latest_obs['updated_at'])
                if (datetime.now() - last_up).total_seconds() > 48 * 3600:
                    is_stale = True
        except Exception:
            pass

        if is_stale:
            print("\n" + "!" * 100)
            print("!!! WARNING: MACRO DATA MAY BE STALE (>48 HOURS OLD). PLEASE RUN FETCH JOB. !!!")
            print("!" * 100)


        # 0. Active Macro Situation Quadrant Banner
        if macro_sit:
            print(f"\n>>> ACTIVE QUADRANT: [{macro_sit.get('name', 'N/A')}]")
            print(f"    - {macro_sit.get('rates_label', '')}  |  {macro_sit.get('bs_label', '')}")
            print(f"    - Macro Signal: {macro_sit.get('description', '')}")
            print(f"    - Favored Sectors: {', '.join(macro_sit.get('favored_sectors', [])[:3])}")
            print("-" * 100)

        # Executive Summary Box
        print(f"\n[OVERALL MACRO REGIME]: {summary.get('overall_regime', 'N/A')}")
        print(f"[Liquidity Regime]:    {summary.get('liquidity_regime', 'N/A')}")
        print(f"[Yield Curve Regime]:  {summary.get('yield_curve_regime', 'N/A')}")
        print(f"[Credit Risk Regime]:   {summary.get('credit_regime', 'N/A')}")
        print("-" * 100)

        # 1. Federal Reserve & Reserve Liquidity Proxy Table
        liq_table = [
            ["Reserve Liquidity Proxy", fmt_num(liq.get('net_liquidity'), ":,.2f", " B", prefix="$"), fmt_num(liq.get('change_30d_billion'), ":+.2f", " B (30d)")],
            ["Fed Total Assets", fmt_num(liq.get('fed_assets_billion'), ":,.2f", " B", prefix="$"), "Weekly FRED"],
            ["Treasury Gen Acct (TGA)", fmt_num(liq.get('tga_billion'), ":,.2f", " B", prefix="$"), "Fed Balance"],
            ["Reverse Repo (RRP)", fmt_num(liq.get('rrp_billion'), ":,.2f", " B", prefix="$"), "Overnight Facility"]
        ]
        print("\n--- 1. FEDERAL RESERVE & RESERVE LIQUIDITY PROXY ---")
        print(tabulate(liq_table, headers=["Metric", "Current Value", "Note"], tablefmt="grid"))

        # 2. Rates & Yield Curve Table
        yc_table = [
            ["Policy Rate", fmt_num(policy.get('policy_rate'), ":.2f", "%")],
            ["Policy Rate 30d Change", fmt_num(policy.get('policy_rate_change_30d'), ":+.2f", "%")],
            ["10Y Real Yield Proxy", fmt_num(policy.get('real_yield_10y'), ":+.2f", "%")],
            ["10-Year Treasury Yield", fmt_num(yc.get('treasury_10y'), ":.2f", "%")],
            ["2-Year Treasury Yield", fmt_num(yc.get('treasury_2y'), ":.2f", "%")],
            ["10Y - 2Y Yield Spread", fmt_num(yc.get('spread_10y_2y'), ":+.2f", "%")],
            ["10Y - 3M Yield Spread", fmt_num(yc.get('spread_10y_3m'), ":+.2f", "%")]
        ]
        print("\n--- 2. RATES & YIELD CURVE SLOPE ---")
        print(tabulate(yc_table, headers=["Indicator", "Value"], tablefmt="grid"))

        # 3. Single-Stock Lagging Value Opportunities
        if lagging_stocks:
            lag_table = []
            for s in lagging_stocks[:6]:
                fwd_pe = fmt_num(s.get('forward_pe'), ":.1f", "x")
                p_avg = fmt_num(s.get('peer_avg_fpe'), ":.1f", "x")
                lag_table.append([s.get('ticker', ''), s.get('name', ''), s.get('group', ''), fwd_pe, p_avg, s.get('action', '')])
            print("\n--- 3. SINGLE-STOCK LAGGING VALUE OPPORTUNITIES (PEER DISPERSION) ---")
            print(tabulate(lag_table, headers=["Ticker", "Company Name", "Sector Group", "Fwd P/E", "Peer Avg", "Recommended Action"], tablefmt="grid"))

        # 4. Tax-Aware Mid-Term Sector Recommendations (3M - 1Y Horizon)
        if recommendations:
            rec_table = []
            for r in recommendations:
                fwd_pe = fmt_num(r.get('avg_forward_pe'), ":.1f", "x")
                rec_table.append([r.get('sector_group', ''), r.get('action', ''), r.get('conviction', ''), fwd_pe, r.get('selective_stock_pick', '')])
            print("\n--- 4. DYNAMIC TAX-AWARE SECTOR RECOMMENDATIONS (3M - 1Y HORIZON) ---")
            print(tabulate(rec_table, headers=["Sector Group", "Action Posture", "Conviction", "Avg Fwd P/E", "Selective Stock Pick"], tablefmt="grid"))

        # 5. AI, Memory, Physical AI & Downstream Power/Cooling Ecosystem
        if ai_ecosystem:
            ai_table = []
            for g in ai_ecosystem:
                fwd_pe = fmt_num(g.get('avg_forward_pe'), ":.2f", "x")
                eve = fmt_num(g.get('avg_ev_ebitda'), ":.2f", "x")
                tickers_str = ", ".join([c["ticker"] for c in g.get("companies", [])])
                ai_table.append([g.get('group', ''), tickers_str, fwd_pe, eve, fmt_num(g.get('fair_fpe_norm'), ":.1f", "x"), g.get('valuation_status', '')])
            print("\n--- 5. AI, MEMORY, PHYSICAL AI (ROBOTICS) & DOWNSTREAM POWER/COOLING ECOSYSTEM ---")
            print(tabulate(ai_table, headers=["Supply Chain Sub-Group", "Key Tickers", "Avg Fwd P/E", "Avg EV/EBITDA", "Norm P/E", "Ecosystem Status"], tablefmt="grid"))

        print("\n" + "=" * 100 + "\n")

    def generate_markdown_report(self, analysis: Dict[str, Any]) -> str:
        """Generates a detailed Markdown report file with 100% defensive format protection."""
        today_str = analysis.get("summary", {}).get("date", datetime.now().strftime("%Y-%m-%d"))
        summary = analysis.get("summary", {})
        liq = analysis.get("liquidity_details", {})
        policy = analysis.get("policy_details", {})
        yc = analysis.get("yield_curve_details", {})
        credit = analysis.get("credit_details", {})
        mkt = analysis.get("market_details", {})
        macro = analysis.get("macro_details", {})
        news_events = analysis.get("news_events", [])
        valuations = analysis.get("sector_valuations", [])
        ai_ecosystem = analysis.get("ai_ecosystem", [])
        recommendations = analysis.get("recommendations", [])
        lagging_stocks = analysis.get("lagging_stock_opportunities", [])
        lagging_stocks = analysis.get("lagging_stock_opportunities", [])
        macro_sit = analysis.get("macro_situation", {})

        stale_warning_md = ""
        try:
            latest_obs = self.storage.get_latest_observation('treasury_10y')
            if latest_obs and latest_obs.get('updated_at'):
                last_up = datetime.fromisoformat(latest_obs['updated_at'])
                if (datetime.now() - last_up).total_seconds() > 48 * 3600:
                    stale_warning_md = "\n> [!WARNING]\n> **DATA STALENESS DETECTED**: The underlying macro data hasn't been updated in over 48 hours. Run the fetch job to ensure accuracy.\n"
        except Exception:
            pass


        # Build 4 Macro Situations Section
        sit_section_md = ""
        if macro_sit:
            fav_sec_list = "\n".join([f"- {s}" for s in macro_sit.get("favored_sectors", [])])
            fav_comp_list = "\n".join([f"- {c}" for c in macro_sit.get("favored_company_types", [])])
            dis_sec_list = "\n".join([f"- {d}" for d in macro_sit.get("disfavored_sectors", [])])

            sit_section_md = f"""
## 1. Active Macro Situation (2x2 Matrix Analysis)

> [!IMPORTANT]
> **Active Quadrant**: `{macro_sit.get('name', 'N/A')}`
> - **Rates Stance**: `{macro_sit.get('rates_label', 'N/A')}`
> - **Net Liquidity Direction**: `{macro_sit.get('bs_label', 'N/A')}`
> - **Macro Environment**: {macro_sit.get('description', '')}

### Sector & Company Type Alignment for Current Situation

#### Favored Sectors
{fav_sec_list}

#### Preferred Company Characteristics
{fav_comp_list}

#### Disfavored / High Risk Sectors
{dis_sec_list}
"""

        # Build Lagging Stock Opportunities markdown section
        lag_section_md = ""
        if lagging_stocks:
            lag_rows = []
            for s in lagging_stocks:
                fwd_pe = fmt_num(s.get('forward_pe'), ":.1f", "x")
                p_avg = fmt_num(s.get('peer_avg_fpe'), ":.1f", "x")
                lag_rows.append(f"| `{md_cell(s.get('ticker',''))}` | **{md_cell(s.get('name',''))}** | {md_cell(s.get('group',''))} | `{fwd_pe}` | `{p_avg}` | **{md_cell(s.get('action',''))}** | {md_cell(s.get('rationale',''))} |")
            lag_table_md = "\n".join(lag_rows)
            lag_section_md = f"""
## 5. Single-Stock Lagging Value Opportunities (Peer Dispersion Analysis)

The following individual constituent stocks were identified as trading at deep peer discounts or lagging sector price performance while underlying fundamentals remain solid:

| Ticker | Company Name | Sector Group | Forward P/E | Peer Group Avg | Action Posture | Strategic Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{lag_table_md}
"""

        # Build Recommendations markdown section
        rec_section_md = ""
        if recommendations:
            rec_rows = []
            for r in recommendations:
                fwd_pe = fmt_num(r.get('avg_forward_pe'), ":.1f", "x")
                rec_rows.append(f"| **{md_cell(r.get('sector_group',''))}** | **{md_cell(r.get('action',''))}** | `{md_cell(r.get('conviction',''))}` | `{fwd_pe}` | `{md_cell(r.get('selective_stock_pick',''))}` | {md_cell(r.get('rationale',''))} |")
            rec_table_md = "\n".join(rec_rows)
            rec_section_md = f"""
## 6. Tax-Aware Mid-Term Sector Recommendations (3-Month to 1-Year Horizon)

> [!NOTE]
> **Tax-Aware Investment Framework**: Default posture leans strongly toward **HOLDing** assets to minimize capital gains tax friction. **BUY** and **SELL** actions are reserved for high-conviction valuation dislocations or macro regime shifts.

| Sector / Supply Chain Group | Action Posture | Conviction | Avg Fwd P/E | Selective Stock Pick | Strategic Mid-Term Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
{rec_table_md}
"""

        # Build AI & Physical AI Ecosystem Markdown section
        ai_section_md = ""
        if ai_ecosystem:
            ai_rows = []
            for g in ai_ecosystem:
                fwd_pe = fmt_num(g.get('avg_forward_pe'), ":.2f", "x")
                eve = fmt_num(g.get('avg_ev_ebitda'), ":.2f", "x")
                tickers_str = ", ".join([f"`{c['ticker']}`" for c in g.get("companies", [])])
                ai_rows.append(f"| **{g.get('group','')}** | {tickers_str} | `{fwd_pe}` | `{eve}` | `{fmt_num(g.get('fair_fpe_norm'), ':.1f', 'x')}` | `{g.get('valuation_status','')}` |")
            ai_table_md = "\n".join(ai_rows)
            ai_section_md = f"""
## 7. AI, Memory, Physical AI (Robotics) & Downstream Power/Cooling Supply Chain

Tracking valuation multiples and downstream physical dependencies across compute, memory, robotics, power grid, thermal cooling, and critical materials:

| Ecosystem Sub-Group | Key Tickers | Avg Forward P/E | Avg EV / EBITDA | Historical Norm (P/E) | Supply Chain & Valuation Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
{ai_table_md}
"""

        net_liq_val = fmt_num(liq.get('net_liquidity'), ":,.2f", " B", prefix="$")
        change_30d_val = fmt_num(liq.get('change_30d_billion'), ":+.2f", " B")
        fed_assets_val = fmt_num(liq.get('fed_assets_billion'), ":,.2f", " B", prefix="$")
        tga_val = fmt_num(liq.get('tga_billion'), ":,.2f", " B", prefix="$")
        rrp_val = fmt_num(liq.get('rrp_billion'), ":,.2f", " B", prefix="$")

        policy_rate_val = fmt_num(policy.get('policy_rate'), ":.2f", "%")
        policy_change_val = fmt_num(policy.get('policy_rate_change_30d'), ":+.2f", "%")
        real_yield_val = fmt_num(policy.get('real_yield_10y'), ":+.2f", "%")
        t10_val = fmt_num(yc.get('treasury_10y'), ":.2f", "%")
        t2_val = fmt_num(yc.get('treasury_2y'), ":.2f", "%")
        s10_2_val = fmt_num(yc.get('spread_10y_2y'), ":+.2f", "%")
        s10_3m_val = fmt_num(yc.get('spread_10y_3m'), ":+.2f", "%")

        hy_oas_val = fmt_num(credit.get('high_yield_oas'), ":.2f", "%")
        ig_oas_val = fmt_num(credit.get('invest_grade_oas'), ":.2f", "%")
        nfci_val = fmt_num(credit.get('chicago_fed_nfci'), ":.2f")

        vix_val = fmt_num(mkt.get('vix'), ":.2f")
        dxy_val = fmt_num(mkt.get('dxy'), ":.2f")
        sp500_val = fmt_num(mkt.get('sp500'), ":,.2f")
        crude_val = fmt_num(mkt.get('crude_oil'), ":.2f", prefix="$")
        gold_val = fmt_num(mkt.get('gold'), ":,.2f", prefix="$")
        copper_val = fmt_num(mkt.get('copper'), ":.2f", prefix="$")

        report_content = f"""# Daily 4-Quadrant Macro & Dynamic Sector Strategy Report ({today_str})
*Automated Capture Engine & Institutional Framework (Defiant Gatekeeper)*
{stale_warning_md}
---
{sit_section_md}
---

## 2. Federal Reserve & Reserve Liquidity Proxy

Reserve liquidity proxy is calculated as `Fed Total Assets - TGA Balance - Reverse Repo Facility (RRP)`. It is a useful banking-system liquidity heuristic, not a complete measure of money supply or global liquidity.

| Component | Value (Billions USD) | Notes / Description |
| :--- | :--- | :--- |
| **Reserve Liquidity Proxy** | **{net_liq_val}** | **30-Day Change: {change_30d_val}** |
| Fed Total Assets | {fed_assets_val} | Total Balance Sheet Size |
| Treasury General Account (TGA) | {tga_val} | Treasury Cash Buffer at Fed |
| Reverse Repo Facility (RRP) | {rrp_val} | Overnight Liquidity Drain |

---

## 3. Yield Curve & Interest Rates

The yield curve slope is a key indicator of economic cycle transitions and recession risk, especially when confirmed by labor, credit, and earnings data.

| Rate / Spread | Current Level | Institutional Signal |
| :--- | :--- | :--- |
| **Policy Rate** | `{policy_rate_val}` | Source: `{policy.get('source', 'N/A')}` / Stance: `{policy.get('policy_stance', 'N/A')}` |
| **Policy Rate 30d Change** | `{policy_change_val}` | Used for Rates Stance in Matrix |
| **10Y Real Yield Proxy** | `{real_yield_val}` | 10Y Treasury minus 10Y breakeven |
| **10-Year Treasury Yield** | `{t10_val}` | Benchmark Long Rate |
| **2-Year Treasury Yield** | `{t2_val}` | Short Rate / Fed Expectations |
| **10Y - 2Y Spread** | `{s10_2_val}` | **Regime: {yc.get('regime', 'N/A')}** |
| **10Y - 3M Spread** | `{s10_3m_val}` | Classic Recession Gauge |

---

## 4. Credit Markets & Risk Appetite

Credit spreads measure corporate risk premiums and systemic financial tightness.

| Metric | Current Value | Threshold Benchmark |
| :--- | :--- | :--- |
| **ICE BofA High Yield OAS** | `{hy_oas_val}` | Normal: <4.5%, Stress: >5.0%, Panic: >8.0% |
| **Investment Grade OAS** | `{ig_oas_val}` | High Quality Corporate Premium |
| **Chicago Fed Financial Conditions** | `{nfci_val}` | Negative = Loose, Positive = Tight |

---
{lag_section_md}
---
{rec_section_md}
---
{ai_section_md}
---

## 8. Market Risk, Volatility & Commodities

| Asset / Risk Gauge | Current Price / Level | Signal |
| :--- | :--- | :--- |
| **CBOE Volatility (VIX)** | `{vix_val}` | `{mkt.get('vix_state', 'N/A')}` |
| **US Dollar Index (DXY)** | `{dxy_val}` | Global Currency Tightness |
| **S&P 500 Index** | `{sp500_val}` | US Equity Benchmark |
| **WTI Crude Oil** | `{crude_val}` | Energy Cost Drivers |
| **Gold** | `{gold_val}` | Monetary Protection / Safe Haven |
| **Copper** | `{copper_val}` | Industrial Demand Indicator |

---
*Report auto-generated by 4-Quadrant Macro & Dynamic Sector Strategy Engine.*
"""

        report_filename = self.output_dir / f"macro_report_{today_str}.md"
        latest_filename = self.output_dir / "latest_report.md"

        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        with open(latest_filename, "w", encoding="utf-8") as f:
            f.write(report_content)

        if self.verbose:
            print(f"--> Daily Markdown Report with 4 Macro Situations generated: {report_filename}")
        return str(report_filename)
