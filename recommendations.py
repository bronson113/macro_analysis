"""
Recommendations module for Macro & Sector Analysis Engine.
Generates Tax-Aware, Mid-Term (3-Month to 1-Year Horizon) Sector Buy/Sell/Hold Recommendations
based on Net Liquidity, Sector EV/EBITDA & P/E Multiples, Credit Spreads, and News Catalysts.
"""

import logging
from typing import Dict, List, Any, Optional
from storage import MacroStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Target Sectors & Supply Chain Baskets
SECTOR_LIST = [
    {"name": "Technology (XLK)", "etf": "XLK", "norm_pe": 24.0},
    {"name": "Financials (XLF)", "etf": "XLF", "norm_pe": 13.0},
    {"name": "Healthcare (XLV)", "etf": "XLV", "norm_pe": 18.0},
    {"name": "Energy (XLE)", "etf": "XLE", "norm_pe": 12.0},
    {"name": "Industrials (XLI)", "etf": "XLI", "norm_pe": 19.0},
    {"name": "Consumer Discretionary (XLY)", "etf": "XLY", "norm_pe": 22.0},
    {"name": "Consumer Staples (XLP)", "etf": "XLP", "norm_pe": 20.0},
    {"name": "AI Compute & Accelerators", "etf": "NVDA/AMD/TSM", "norm_pe": 28.0},
    {"name": "High-Bandwidth Memory (HBM)", "etf": "MU/WDC", "norm_pe": 16.0},
    {"name": "Physical AI & Robotics", "etf": "TSLA/TER/SYM", "norm_pe": 30.0},
    {"name": "Downstream Power & Grid", "etf": "CEG/VST/ETN", "norm_pe": 22.0}
]


class SectorRecommendationEngine:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()

    def generate_recommendations(
        self,
        summary: Dict[str, Any],
        credit: Dict[str, Any],
        valuations: List[Dict[str, Any]],
        ai_ecosystem: List[Dict[str, Any]],
        news_events: List[Dict[str, Any]],
        macro_situation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        recommendations = []
        hy_oas = credit.get("high_yield_oas")
        liq_regime = summary.get("liquidity_regime", "Neutral")
        overall_regime = summary.get("overall_regime", "Neutral")
        treasury_10y = summary.get("treasury_10y")
        breakeven_10y = summary.get("breakeven_10y")
        housing_yoy = summary.get("housing_yoy")
        dxy = summary.get("dxy")
        favored_sectors = macro_situation.get("favored_sectors", [])
        disfavored_sectors = macro_situation.get("disfavored_sectors", [])
        macro_quality = macro_situation.get("quality", "OK")

        val_map = {v["sector"]: v for v in valuations}
        ai_map = {g["group"]: g for g in ai_ecosystem}
        contagion_news = [n for n in news_events if "contagion" in n.get("sentiment", "").lower() or "stress" in n.get("sentiment", "").lower()]

        for sector in SECTOR_LIST:
            sec_name = sector["name"]
            norm_pe = sector["norm_pe"]
            
            val_data = val_map.get(sec_name)
            if not val_data:
                for g_name, g_data in ai_map.items():
                    if sec_name.split()[0].lower() in g_name.lower():
                        val_data = {
                            "forward_pe": g_data["avg_forward_pe"],
                            "ev_ebitda": g_data["avg_ev_ebitda"],
                            "valuation_status": g_data["valuation_status"]
                        }
                        break

            fwd_pe = val_data.get("forward_pe") if val_data else None
            ev_ebitda = val_data.get("ev_ebitda") if val_data else None
            valuation_stretched = fwd_pe is not None and fwd_pe > norm_pe * 1.15
            valuation_severely_stretched = fwd_pe is not None and fwd_pe > norm_pe * 1.35

            erp = None
            if fwd_pe and treasury_10y:
                earnings_yield = (1.0 / fwd_pe) * 100.0
                erp = earnings_yield - treasury_10y

            action = "HOLD"
            conviction = "HIGH (Tax-Aware Default)"
            rationale = "Mid-term horizon (3-12m): Valuation and macro drivers are within stable parameters. Holding avoids unnecessary tax drag."
            if macro_quality == "INSUFFICIENT_DATA":
                conviction = "LOW (Macro Data Incomplete)"
                rationale = "Macro quadrant is withheld because policy-rate or liquidity data is incomplete. Defaulting to HOLD unless non-macro risk controls provide a stronger signal."

            if macro_quality != "INSUFFICIENT_DATA" and sec_name in favored_sectors:
                action = "BUY / ACCUMULATE"
                conviction = "HIGH (Macro Quadrant Tailwinds)"
                rationale = f"Sector is highly favored in the current {macro_situation.get('name')} regime."
                if fwd_pe and fwd_pe < norm_pe:
                    rationale += f" Trading at a discount ({fwd_pe:.1f}x vs {norm_pe:.1f}x norm)."
            elif macro_quality != "INSUFFICIENT_DATA" and sec_name in disfavored_sectors:
                action = "SELL / TRIM"
                conviction = "HIGH (Macro Risk Avoidance)"
                rationale = f"Sector faces severe headwinds in the current {macro_situation.get('name')} regime."
            
            if fwd_pe and fwd_pe < norm_pe * 0.85 and "Expanding" in liq_regime and (hy_oas is not None and hy_oas < 4.5):
                if action == "HOLD":
                    action = "BUY / ACCUMULATE"
                    conviction = "MODERATE TO HIGH"
                    rationale = f"Sector is trading at a discount ({fwd_pe:.1f}x Fwd P/E vs {norm_pe:.1f}x norm) alongside expanding liquidity."

            if hy_oas is not None and hy_oas > 5.0:
                if sec_name in ["Healthcare (XLV)", "Consumer Staples (XLP)", "Gold"]:
                    action = "BUY / ACCUMULATE"
                    conviction = "HIGH (Flight to Safety)"
                    rationale = f"Elevated credit stress (HY OAS {hy_oas:.2f}%). Defensive sector provides capital protection."
                else:
                    action = "SELL / TRIM"
                    conviction = "HIGH (Risk Mitigation)"
                    rationale = f"Elevated credit stress (HY OAS {hy_oas:.2f}%). Protect capital as financial conditions tighten."

            elif (macro_quality != "INSUFFICIENT_DATA" and valuation_severely_stretched and ("Contracting" in liq_regime or "LIQUIDITY DRAIN" in overall_regime)):
                action = "SELL / TRIM"
                conviction = "HIGH (Risk Mitigation)"
                rationale = f"Elevated valuation stretch ({fwd_pe:.1f}x Fwd P/E vs {norm_pe:.1f}x norm) combined with liquidity tightening."
            
            if "Energy" in sec_name and ev_ebitda and ev_ebitda < 7.5:
                if "SELL" not in action:
                    action = "BUY / ACCUMULATE"
                    conviction = "MODERATE (High Free Cash Flow)"
                    rationale = f"Energy EV/EBITDA ({ev_ebitda:.1f}x) is deeply discounted. Strategic mid-term inflation hedge."
            
            if "Memory" in sec_name and contagion_news:
                action = "HOLD / CAUTION"
                conviction = "MODERATE"
                rationale = "Memory supply chain headline volatility present. Maintain position for mid-term HBM structural cycle; avoid panic selling."

            # Housing Overrides
            if housing_yoy is not None and housing_yoy < -10.0:
                if "Consumer Discretionary" in sec_name or "Industrials" in sec_name:
                    action = "SELL / TRIM"
                    conviction = "HIGH (Housing Contraction)"
                    rationale = f"Housing Starts contracting violently ({housing_yoy:.1f}% YoY). Severe cyclical and consumer spending headwind."

            # FX Overrides
            if dxy is not None and dxy > 105.0:
                if "Technology" in sec_name or "Energy" in sec_name or "Industrials" in sec_name:
                    if "SELL" not in action:
                        action = "SELL / TRIM"
                        conviction = "MODERATE TO HIGH (FX Headwinds)"
                        rationale = f"Strong US Dollar (DXY > 105) creates severe FX translation headwinds for global exporters."
                elif "Financials" in sec_name or "Utilities" in sec_name:
                    if action == "HOLD":
                        action = "BUY / ACCUMULATE"
                        conviction = "MODERATE (Domestic Safe Haven)"
                        rationale = "Domestic revenue base provides safety during global Dollar wrecking-ball periods."

            # Real Yield Overrides
            if treasury_10y is not None and breakeven_10y is not None:
                real_yield = treasury_10y - breakeven_10y
                if real_yield > 2.0 and ("Technology" in sec_name or "AI" in sec_name or "Robotics" in sec_name):
                    if valuation_stretched:
                        action = "SELL / TRIM"
                        conviction = "HIGH (Restrictive Real Yields + Valuation Stretch)"
                        rationale = f"Real yields ({real_yield:.2f}%) are restrictive and valuation is stretched ({fwd_pe:.1f}x vs {norm_pe:.1f}x norm), creating multiple-compression risk."
                    elif "SELL" not in action:
                        action = "HOLD / CAUTION"
                        conviction = "MODERATE (Restrictive Real Yield Headwind)"
                        rationale = f"Real yields ({real_yield:.2f}%) are a headwind for long-duration growth, but valuation is not stretched versus norm. Hold existing exposure and require earnings confirmation before adding."

            # ERP Overrides
            if erp is not None:
                if erp < -1.0 and valuation_stretched:
                    action = "SELL / TRIM"
                    conviction = "HIGH (Negative ERP + Valuation Stretch)"
                    rationale = f"Negative ERP ({erp:.2f}%) combined with valuation stretch ({fwd_pe:.1f}x vs {norm_pe:.1f}x norm). Risk-free yield competes strongly with sector earnings yield."
                elif erp < 0.0 and "SELL" not in action:
                    if "BUY" in action:
                        action = "HOLD / SELECTIVE"
                    else:
                        action = "HOLD / CAUTION"
                    conviction = "MODERATE (Rate/Valuation Headwind)"
                    rationale = f"Negative ERP ({erp:.2f}%) is a rate/valuation headwind, but valuation is not stretched enough to justify an automatic sell."
                elif erp > 4.0 and "SELL" not in action:
                    action = "BUY / ACCUMULATE"
                    conviction = "HIGH (Deep Value Risk Premium)"
                    rationale = f"Extremely attractive ERP ({erp:.2f}%). Equities offer significant yield over risk-free bonds."

            recommendations.append({
                "sector": sec_name,
                "action": action,
                "conviction": conviction,
                "avg_forward_pe": fwd_pe,
                "ev_ebitda": ev_ebitda,
                "erp": erp,
                "rationale": rationale
            })

        return recommendations
