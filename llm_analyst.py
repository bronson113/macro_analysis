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
import statistics
from typing import Dict, Any, Optional
from storage import MacroStorage
from stock_relative_valuation import relative_multiple_key, safe_ratio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


MIN_RELATIVE_HISTORY_POINTS = 3
RELATIVE_DISCOUNT_THRESHOLD_PCT = 20.0
RELATIVE_PREMIUM_THRESHOLD_PCT = 25.0


class DynamicMacroAnalyst:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()

    def _historical_relative_norm(self, group: str, ticker: str, multiple: str) -> Optional[float]:
        series = self.storage.get_indicator_series(relative_multiple_key(group, ticker, multiple), limit=756)
        if series.empty or len(series) < MIN_RELATIVE_HISTORY_POINTS:
            return None

        values = [
            float(v)
            for v in series["value"].dropna().tolist()
            if 0 < float(v) < 5
        ]
        if len(values) < MIN_RELATIVE_HISTORY_POINTS:
            return None

        return statistics.median(values)

    def _relative_valuation_result(
        self,
        group: str,
        ticker: str,
        multiple: str,
        current_multiple: Optional[float],
        peer_average: Optional[float],
    ) -> Dict[str, Any]:
        current_relative = safe_ratio(current_multiple, peer_average)
        historical_norm = self._historical_relative_norm(group, ticker, multiple) if current_relative else None
        discount_pct = None
        status = "Insufficient Relative History"

        if current_relative is not None and historical_norm:
            discount_pct = (1 - (current_relative / historical_norm)) * 100.0
            if discount_pct >= RELATIVE_DISCOUNT_THRESHOLD_PCT:
                status = "Discounted vs Historical Sector Relationship"
            elif discount_pct <= -RELATIVE_PREMIUM_THRESHOLD_PCT:
                status = "Rich vs Historical Sector Relationship"
            else:
                status = "Fair vs Historical Sector Relationship"

        return {
            "current_relative": round(current_relative, 3) if current_relative is not None else None,
            "historical_relative_norm": round(historical_norm, 3) if historical_norm else None,
            "relative_discount_pct": round(discount_pct, 1) if discount_pct is not None else None,
            "status": status,
        }

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

            constituent_relative_valuation = []

            # Find stocks discounted versus their own historical sector-relative multiple.
            for c in comp_list:
                reasons = []
                c_fpe = c.get("forward_pe")
                c_eve = c.get("ev_ebitda")
                c_dist52 = c.get("dist_from_52w_high_pct")
                ticker = c.get("ticker", "N/A")
                fpe_relative = self._relative_valuation_result(grp_name, ticker, "fpe", c_fpe, avg_fpe)
                eve_relative = self._relative_valuation_result(grp_name, ticker, "eve", c_eve, avg_eve)
                has_relative_history = (
                    fpe_relative["historical_relative_norm"] is not None
                    or eve_relative["historical_relative_norm"] is not None
                )

                relative_statuses = [
                    r["status"]
                    for r in [fpe_relative, eve_relative]
                    if r["historical_relative_norm"] is not None
                ]
                if "Discounted vs Historical Sector Relationship" in relative_statuses:
                    relative_valuation_status = "Discounted vs Historical Sector Relationship"
                elif "Rich vs Historical Sector Relationship" in relative_statuses:
                    relative_valuation_status = "Rich vs Historical Sector Relationship"
                elif relative_statuses:
                    relative_valuation_status = "Fair vs Historical Sector Relationship"
                else:
                    relative_valuation_status = "Insufficient Relative History"

                constituent_relative_valuation.append({
                    "ticker": ticker,
                    "forward_pe_relative": fpe_relative["current_relative"],
                    "historical_forward_pe_relative": fpe_relative["historical_relative_norm"],
                    "relative_fpe_discount_pct": fpe_relative["relative_discount_pct"],
                    "ev_ebitda_relative": eve_relative["current_relative"],
                    "historical_ev_ebitda_relative": eve_relative["historical_relative_norm"],
                    "relative_ev_ebitda_discount_pct": eve_relative["relative_discount_pct"],
                    "relative_valuation_status": relative_valuation_status,
                })

                if fpe_relative["status"] == "Discounted vs Historical Sector Relationship":
                    reasons.append(
                        f"Forward P/E relative multiple ({fpe_relative['current_relative']:.2f}x sector) is "
                        f"{fpe_relative['relative_discount_pct']:.1f}% below its historical sector-relative norm "
                        f"({fpe_relative['historical_relative_norm']:.2f}x sector)"
                    )
                elif not has_relative_history and avg_fpe and c_fpe and c_fpe < avg_fpe * 0.75:
                    reasons.append(f"Forward P/E ({c_fpe:.1f}x) is {((1 - c_fpe/avg_fpe)*100):.1f}% below peer group avg ({avg_fpe:.1f}x); historical relative history unavailable")

                if eve_relative["status"] == "Discounted vs Historical Sector Relationship":
                    reasons.append(
                        f"EV/EBITDA relative multiple ({eve_relative['current_relative']:.2f}x sector) is "
                        f"{eve_relative['relative_discount_pct']:.1f}% below its historical sector-relative norm "
                        f"({eve_relative['historical_relative_norm']:.2f}x sector)"
                    )
                elif not has_relative_history and avg_eve and c_eve and c_eve > 0 and c_eve < avg_eve * 0.75:
                    reasons.append(f"EV/EBITDA ({c_eve:.1f}x) is {((1 - c_eve/avg_eve)*100):.1f}% below peer group avg ({avg_eve:.1f}x); historical relative history unavailable")

                if c_dist52 and c_dist52 < -20.0:
                    reasons.append(f"Lagging price performance ({c_dist52:.1f}% below 52-week high)")

                relative_discount_confirmed = (
                    fpe_relative["status"] == "Discounted vs Historical Sector Relationship"
                    or eve_relative["status"] == "Discounted vs Historical Sector Relationship"
                )
                legacy_peer_discount = (
                    not has_relative_history
                    and c_fpe
                    and avg_fpe
                    and c_fpe < avg_fpe * 0.6
                )

                if (relative_discount_confirmed and len(reasons) >= 1) or (len(reasons) >= 2 and not has_relative_history) or legacy_peer_discount:
                    lagging_opportunities.append({
                        "group": grp_name,
                        "ticker": ticker,
                        "name": c.get("name", "N/A"),
                        "price": c.get("price"),
                        "forward_pe": c_fpe,
                        "ev_ebitda": c_eve,
                        "peer_avg_fpe": round(avg_fpe, 1) if avg_fpe else None,
                        "current_relative_fpe": fpe_relative["current_relative"],
                        "historical_relative_fpe": fpe_relative["historical_relative_norm"],
                        "relative_fpe_discount_pct": fpe_relative["relative_discount_pct"],
                        "dispersion_reasons": reasons,
                        "action": "WATCHLIST / SELECTIVE REVIEW (Lagging Value)",
                        "horizon": "3 Month - 1 Year",
                        "rationale": f"Peer-discount watchlist candidate within {grp_name}: {c.get('name', 'Stock')} ({ticker}) appears discounted relative to its historical sector-relative norm. Confirm sector signal, earnings quality, balance sheet, and catalyst before buying. " + "; ".join(reasons)
                    })

            sector_dispersion_summary.append({
                "group": grp_name,
                "ticker_count": len(comp_list),
                "avg_forward_pe": round(avg_fpe, 2) if avg_fpe else None,
                "avg_ev_ebitda": round(avg_eve, 2) if avg_eve else None,
                "constituent_relative_valuation": sorted(
                    constituent_relative_valuation,
                    key=lambda item: (
                        item["relative_fpe_discount_pct"] is None,
                        -(item["relative_fpe_discount_pct"] or -999),
                        item["ticker"],
                    ),
                )
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
