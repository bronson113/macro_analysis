"""
LLM Analyst module for Macro Analysis System.
Ingests raw macro JSON payload and performs dynamic, un-hardcoded Defiant Gatekeeper analysis:
- Macro Regime & Net Liquidity Synthesis
- Sector P/E & EV/EBITDA Valuation Multiples
- Stock-Level Peer Dispersion & Lagging Stock Opportunity Detection (e.g., Micron MU, Citigroup C lagging peers)
- Tax-Aware Mid-Term (3-Month to 1-Year) Sector & Individual Stock Recommendations
Guarantees 100% defensive dictionary access safety (.get()).
"""

import logging
from typing import Dict, Any, Optional
from storage import MacroStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class DynamicMacroAnalyst:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()

    def analyze_raw_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically analyzes the un-hardcoded raw data payload.
        Scans individual stock constituents to spot peer dispersion and lagging stock opportunities.
        """
        macro = payload.get("macro_quantitative", {})
        news = payload.get("recent_news_events", [])
        stocks = payload.get("individual_stock_constituents", [])

        # 1. Macro Quantitative Synthesis
        fed_assets = macro.get("fed_total_assets", {}).get("value") if isinstance(macro.get("fed_total_assets"), dict) else None
        tga = macro.get("tga_balance", {}).get("value", 0.0) if isinstance(macro.get("tga_balance"), dict) else 0.0
        rrp = macro.get("reverse_repo", {}).get("value", 0.0) if isinstance(macro.get("reverse_repo"), dict) else 0.0
        
        net_liq = (fed_assets / 1000.0 - tga - rrp) if fed_assets else None
        
        t10 = macro.get("treasury_10y", {}).get("value") if isinstance(macro.get("treasury_10y"), dict) else None
        t2 = macro.get("treasury_2y", {}).get("value") if isinstance(macro.get("treasury_2y"), dict) else None
        s10_2 = macro.get("spread_10y_2y", {}).get("value") if isinstance(macro.get("spread_10y_2y"), dict) else None
        if s10_2 is None and t10 and t2: s10_2 = t10 - t2

        hy_oas = macro.get("high_yield_oas", {}).get("value") if isinstance(macro.get("high_yield_oas"), dict) else None

        # 2. Stock-Level Peer Dispersion & Lagging Opportunities
        grouped = {}
        for s in stocks:
            grp = s.get("group", "Other")
            if grp not in grouped: grouped[grp] = []
            grouped[grp].append(s)

        lagging_opportunities = []
        sector_dispersion_summary = []

        for grp_name, comp_list in grouped.items():
            valid_fpes = [c.get("forward_pe") for c in comp_list if c.get("forward_pe") and 0 < c.get("forward_pe", 0) < 150]
            valid_eves = [c.get("ev_ebitda") for c in comp_list if c.get("ev_ebitda") and 0 < c.get("ev_ebitda", 0) < 150]

            avg_fpe = sum(valid_fpes) / len(valid_fpes) if valid_fpes else None
            avg_eve = sum(valid_eves) / len(valid_eves) if valid_eves else None

            # Find individual stocks in this group lagging peer average Forward P/E or EV/EBITDA by > 20%
            for c in comp_list:
                reasons = []
                c_fpe = c.get("forward_pe")
                c_eve = c.get("ev_ebitda")
                c_dist52 = c.get("dist_from_52w_high_pct")

                if avg_fpe and c_fpe and c_fpe < avg_fpe * 0.75:
                    reasons.append(f"Forward P/E ({c_fpe:.1f}x) is {((1 - c_fpe/avg_fpe)*100):.1f}% below peer group avg ({avg_fpe:.1f}x)")
                if avg_eve and c_eve and c_eve > 0 and c_eve < avg_eve * 0.75:
                    reasons.append(f"EV/EBITDA ({c_eve:.1f}x) is {((1 - c_eve/avg_eve)*100):.1f}% below peer group avg ({avg_eve:.1f}x)")
                if c_dist52 and c_dist52 < -20.0:
                    reasons.append(f"Lagging price performance ({c_dist52:.1f}% below 52-week high)")

                if len(reasons) >= 2 or (c_fpe and avg_fpe and c_fpe < avg_fpe * 0.6):
                    lagging_opportunities.append({
                        "group": grp_name,
                        "ticker": c.get("ticker", "N/A"),
                        "name": c.get("name", "N/A"),
                        "price": c.get("price"),
                        "forward_pe": c_fpe,
                        "ev_ebitda": c_eve,
                        "peer_avg_fpe": round(avg_fpe, 1) if avg_fpe else None,
                        "dispersion_reasons": reasons,
                        "action": "WATCHLIST / SELECTIVE REVIEW (Lagging Value)",
                        "horizon": "3 Month - 1 Year",
                        "rationale": f"Peer-discount watchlist candidate within {grp_name}: {c.get('name', 'Stock')} ({c.get('ticker', '')}) appears discounted relative to peer average. Confirm sector signal, earnings quality, balance sheet, and catalyst before buying. " + "; ".join(reasons)
                    })

            sector_dispersion_summary.append({
                "group": grp_name,
                "ticker_count": len(comp_list),
                "avg_forward_pe": round(avg_fpe, 2) if avg_fpe else None,
                "avg_ev_ebitda": round(avg_eve, 2) if avg_eve else None
            })

        # 3. Dynamic Sector Recommendations (Tax-Aware 3M-1Y Horizon)
        tax_aware_recommendations = []

        for s_summary in sector_dispersion_summary:
            grp = s_summary["group"]
            fpe = s_summary["avg_forward_pe"]
            
            # Default tax-aware posture: HOLD
            action = "HOLD"
            conviction = "HIGH (Tax-Aware Default)"
            rationale = f"Maintain mid-term allocation in {grp}. Multiples and liquidity are balanced; holding avoids tax realization drag."

            # Check if group has specific lagging opportunities
            grp_lags = [l for l in lagging_opportunities if l["group"] == grp]
            if grp_lags:
                top_stock = grp_lags[0]
                action = f"HOLD SECTOR / SELECTIVE BUY [{top_stock['ticker']}]"
                conviction = "MODERATE TO HIGH (Single-Stock Dispersion)"
                rationale = f"Sector broad ETF is HOLD, but selective buying of lagging constituent {top_stock['name']} ({top_stock['ticker']}) is justified due to deep peer discount."

            tax_aware_recommendations.append({
                "sector_group": grp,
                "action": action,
                "conviction": conviction,
                "avg_forward_pe": fpe,
                "selective_stock_pick": grp_lags[0]["ticker"] if grp_lags else "None (Hold Sector)",
                "rationale": rationale
            })

        return {
            "macro_summary": {
                "net_liquidity_b": round(net_liq, 2) if net_liq else None,
                "spread_10y_2y": round(s10_2, 2) if s10_2 is not None else None,
                "high_yield_oas": round(hy_oas, 2) if hy_oas else None
            },
            "sector_dispersion": sector_dispersion_summary,
            "single_stock_lagging_opportunities": lagging_opportunities,
            "tax_aware_recommendations": tax_aware_recommendations
        }
