"""
Macro Matrix Module for Macro Economic Analysis Engine.
Implements Defiant Gatekeeper 4 Macro Situations (2x2 Matrix):
Interest Rates (Cutting vs Raising) x Fed Balance Sheet (Expanding vs Contracting).
Recommends specific sectors and company characteristics based on the active quadrant.
"""

from typing import Dict, Any


class MacroMatrixEngine:
    def classify_situation(self, effr_trend: str, liq_trend_30d: float, cpi_yoy: float, sahm_rule_triggered: bool, spread_10y_2y: float, m2_yoy: float = None) -> Dict[str, Any]:
        if effr_trend is None or liq_trend_30d is None:
            return {
                "situation_id": 0,
                "name": "INSUFFICIENT DATA: NO ACTIONABLE MACRO QUADRANT",
                "rates_label": "Interest Rates: insufficient policy-rate trend data",
                "bs_label": "Reserve Liquidity: insufficient 30-day liquidity data",
                "description": "The macro framework is withheld because rate stance or net liquidity direction is missing. Default to sector-level HOLD unless valuation or risk controls override.",
                "favored_sectors": [],
                "favored_company_types": [],
                "disfavored_sectors": [],
                "quality": "INSUFFICIENT_DATA"
            }

        rates_easing = effr_trend in ["CUTTING", "EASING", "DOVISH"]
        policy_restrictive = effr_trend in ["RAISING", "HAWKISH", "HOLDING_RESTRICTIVE", "RESTRICTIVE"]
        if not rates_easing and not policy_restrictive:
            return {
                "situation_id": 0,
                "name": "NO ACTIONABLE MACRO QUADRANT: POLICY HOLDING / NEUTRAL",
                "rates_label": "Interest Rates: Holding / Neutral",
                "bs_label": "Reserve Liquidity: direction observed but policy stance is not restrictive or easing",
                "description": "Policy-rate trend is flat without enough restrictive-rate evidence. Treat the matrix as neutral and let valuation, credit, earnings, and tax constraints drive sector actions.",
                "favored_sectors": [],
                "favored_company_types": [],
                "disfavored_sectors": [],
                "quality": "INSUFFICIENT_DATA"
            }

        balance_sheet_expanding = liq_trend_30d is not None and liq_trend_30d > 0
        is_sticky_inflation = cpi_yoy is not None and cpi_yoy > 3.0

        m2_warning = ""
        if m2_yoy is not None and m2_yoy < 0:
            m2_warning = f" M2 Money Supply is contracting ({m2_yoy:.1f}% YoY), signaling deep deflationary pressure on corporate earnings."


        if rates_easing and balance_sheet_expanding:
            situation_id = 1
            name = "SITUATION 1: EASING + RESERVE LIQUIDITY EXPANSION"
            rates_label = "Interest Rates: Cutting / Easing"
            bs_label = "Reserve Liquidity: Expanding (+30d)"
            description = "Risk-liquidity tailwind: lower policy-rate pressure and expanding reserve liquidity. Confirm valuation, credit, and labor data before adding risk."
            if sahm_rule_triggered:
                description += " However, SAHM rule triggered - monitoring for severe labor deterioration."
            description += m2_warning
            favored_sectors = [
                "Technology (XLK)",
                "AI Compute & Accelerators",
                "High-Bandwidth Memory (HBM)",
                "Physical AI & Robotics",
                "Downstream Power & Grid",
                "Consumer Discretionary (XLY)"
            ]
            favored_company_types = ["High-growth tech", "Capex super-cycle (AI, Grid)"]
            disfavored_sectors = ["Cash", "Consumer Staples (XLP)"]

        elif rates_easing and not balance_sheet_expanding:
            situation_id = 2
            name = "SITUATION 2: LATE CYCLE / RECESSION WARNING"
            rates_label = "Interest Rates: Cutting / Easing"
            bs_label = "Reserve Liquidity: Contracting (-30d)"
            description = "Central bank cutting rates due to economic deceleration while net liquidity remains tight."
            if sahm_rule_triggered:
                description += " SAHM rule triggered - High probability of recession."
            if spread_10y_2y is not None and spread_10y_2y > 0:
                description += " Yield Curve Un-inverting - historically bearish for risk assets."
            description += m2_warning
            favored_sectors = [
                "Healthcare (XLV)",
                "Consumer Staples (XLP)"
            ]
            favored_company_types = ["Defensive cash flow", "Low debt"]
            disfavored_sectors = ["Technology (XLK)", "Consumer Discretionary (XLY)", "Industrials (XLI)", "AI Compute & Accelerators", "Physical AI & Robotics"]

        elif policy_restrictive and not balance_sheet_expanding:
            situation_id = 3
            name = "SITUATION 3: RESTRICTIVE POLICY + RESERVE LIQUIDITY CONTRACTION"
            rates_label = "Interest Rates: Raising / Holding Restrictive"
            bs_label = "Reserve Liquidity: Contracting (-30d)"
            description = "Restrictive setup: policy-rate pressure and reserve-liquidity drainage raise valuation multiple-compression risk."
            description += m2_warning
            favored_sectors = [
                "Financials (XLF)",
                "Cash"
            ]
            favored_company_types = ["Net-Interest-Margin beneficiaries", "Zero debt"]
            disfavored_sectors = ["Technology (XLK)", "AI Compute & Accelerators", "Physical AI & Robotics", "Consumer Discretionary (XLY)"]

        else:
            situation_id = 4
            name = "SITUATION 4: RESTRICTIVE POLICY + RESERVE LIQUIDITY EXPANSION"
            rates_label = "Interest Rates: Raising / Holding Restrictive"
            bs_label = "Reserve Liquidity: Expanding (+30d)"
            description = "Policy/liquidity conflict: reserve liquidity is expanding while policy remains restrictive. Identify whether the liquidity source is Fed assets, TGA, RRP, or emergency facilities before drawing conclusions."
            if is_sticky_inflation:
                description += f" Sticky inflation confirmed ({cpi_yoy:.1f}% CPI)."
            description += m2_warning
            favored_sectors = [
                "Energy (XLE)",
                "Financials (XLF)",
                "Industrials (XLI)"
            ]
            favored_company_types = ["Real asset owners", "Inflation-indexed revenues"]
            disfavored_sectors = ["Consumer Discretionary (XLY)"]

        return {
            "situation_id": situation_id,
            "name": name,
            "rates_label": rates_label,
            "bs_label": bs_label,
            "description": description,
            "favored_sectors": favored_sectors,
            "favored_company_types": favored_company_types,
            "disfavored_sectors": disfavored_sectors,
            "quality": "OK"
        }
