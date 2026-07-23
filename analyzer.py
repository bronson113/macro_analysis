"""
Analyzer module for Macro Economic Analysis & Data Capture System.
Implements Defiant Gatekeeper institutional macro framework:
Liquidity, Yield Curve, Credit Spreads, Sector Valuations, 4 Macro Situations (2x2 Matrix),
AI/Memory/Physical AI Ecosystem, Single-Stock Lagging Opportunities (Micron, Western Digital, Citi, etc.),
Dynamic Raw Data JSON Payload Export, Tax-Aware Mid-Term Recommendations, and Major News Events.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from config import REGIME_THRESHOLDS
from storage import MacroStorage
from news_analyzer import MacroNewsAnalyzer
from valuation import SectorValuationEngine
from ai_ecosystem import AIRoboticsEcosystemTracker
from raw_data_engine import RawDataEngine
from llm_analyst import DynamicMacroAnalyst
from macro_matrix import MacroMatrixEngine
from recommendations import SectorRecommendationEngine


def _to_billions(value: Optional[float], unit_scale: str) -> Optional[float]:
    if value is None:
        return None
    if unit_scale == "millions":
        return value / 1000.0
    return value


def _value_on_or_before(df: pd.DataFrame, target_date: pd.Timestamp) -> Optional[float]:
    if df.empty:
        return None
    eligible = df[df["date"] <= target_date]
    if eligible.empty:
        return None
    return eligible.iloc[-1]["value"]


def _classify_fear_greed(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score <= 25:
        return "Extreme Fear"
    if score < 45:
        return "Fear"
    if score <= 55:
        return "Neutral"
    if score < 75:
        return "Greed"
    return "Extreme Greed"


def _fear_greed_signal(rating: Optional[str]) -> Optional[str]:
    if rating == "Extreme Fear":
        return "Extreme fear risk-appetite overlay: panic conditions may create selective opportunities only if credit and liquidity confirm."
    if rating == "Fear":
        return "Fear risk-appetite overlay: sentiment is cautious, so require confirmation from credit, liquidity, and valuation."
    if rating == "Neutral":
        return "Neutral risk-appetite overlay: sentiment is not providing a strong contrarian or caution signal."
    if rating == "Greed":
        return "Greed risk-appetite overlay: risk appetite is firm, so avoid chasing weak valuation setups."
    if rating == "Extreme Greed":
        return "Extreme greed risk-appetite overlay: avoid chasing crowded risk without valuation support."
    return None


class MacroAnalyzer:
    def __init__(self, storage: Optional[MacroStorage] = None):
        self.storage = storage or MacroStorage()
        self.news_analyzer = MacroNewsAnalyzer(self.storage)
        self.valuation_engine = SectorValuationEngine(self.storage)
        self.ai_tracker = AIRoboticsEcosystemTracker(self.storage)
        self.raw_engine = RawDataEngine(self.storage)
        self.llm_analyst = DynamicMacroAnalyst(self.storage)
        self.matrix_engine = MacroMatrixEngine()
        self.rec_engine = SectorRecommendationEngine(self.storage)

    def get_latest_value(self, key: str) -> Optional[float]:
        obs = self.storage.get_latest_observation(key)
        return obs["value"] if obs else None

    def calculate_net_liquidity(self) -> Dict[str, Any]:
        fed_assets_obs = self.storage.get_latest_observation("fed_total_assets")
        tga_obs = self.storage.get_latest_observation("tga_balance")
        rrp_obs = self.storage.get_latest_observation("reverse_repo")

        missing_components = [
            key for key, obs in [
                ("fed_total_assets", fed_assets_obs),
                ("tga_balance", tga_obs),
                ("reverse_repo", rrp_obs),
            ]
            if obs is None
        ]

        if missing_components:
            return {
                "net_liquidity": None,
                "fed_assets_billion": None,
                "tga_billion": None,
                "rrp_billion": None,
                "change_30d_billion": None,
                "m2_yoy": None,
                "last_date": None,
                "quality": "INSUFFICIENT_DATA",
                "missing_components": missing_components,
            }

        fed_assets_b = _to_billions(fed_assets_obs["value"], "millions")
        tga = _to_billions(tga_obs["value"], "millions")
        rrp = _to_billions(rrp_obs["value"], "billions")
        net_liquidity = fed_assets_b - tga - rrp

        df_assets = self.storage.get_indicator_series("fed_total_assets", limit=90)
        df_tga = self.storage.get_indicator_series("tga_balance", limit=90)
        df_rrp = self.storage.get_indicator_series("reverse_repo", limit=90)

        change_30d = None
        current_date = pd.to_datetime(fed_assets_obs["date"])
        target_date = current_date - pd.Timedelta(days=30)
        prev_assets = _value_on_or_before(df_assets, target_date)
        prev_tga_raw = _value_on_or_before(df_tga, target_date)
        prev_rrp_raw = _value_on_or_before(df_rrp, target_date)

        if prev_assets is not None and prev_tga_raw is not None and prev_rrp_raw is not None:
            prev_assets_b = _to_billions(prev_assets, "millions")
            prev_tga = _to_billions(prev_tga_raw, "millions")
            prev_rrp = _to_billions(prev_rrp_raw, "billions")
            prev_net_liq = prev_assets_b - prev_tga - prev_rrp
            change_30d = net_liquidity - prev_net_liq

        df_m2 = self.storage.get_indicator_series("m2_money_supply", limit=13)
        m2_yoy = None
        if not df_m2.empty and len(df_m2) >= 13:
            current_m2 = df_m2.iloc[-1]["value"]
            year_ago_m2 = df_m2.iloc[0]["value"]
            if year_ago_m2:
                m2_yoy = ((current_m2 / year_ago_m2) - 1.0) * 100.0

        return {
            "net_liquidity": round(net_liquidity, 2),
            "fed_assets_billion": round(fed_assets_b, 2),
            "tga_billion": round(tga, 2),
            "rrp_billion": round(rrp, 2),
            "change_30d_billion": round(change_30d, 2) if change_30d is not None else None,
            "m2_yoy": round(m2_yoy, 2) if m2_yoy is not None else None,
            "last_date": fed_assets_obs["date"] if fed_assets_obs else None,
            "quality": "OK" if change_30d is not None else "PARTIAL_DATA",
            "missing_components": [],
        }

    def analyze_policy_stance(self) -> Dict[str, Any]:
        df_rates = self.storage.get_indicator_series("dff", limit=90)
        source = "dff"
        if df_rates.empty:
            df_rates = self.storage.get_indicator_series("effr", limit=24)
            source = "effr"

        if df_rates.empty:
            return {
                "policy_rate": None,
                "policy_rate_change_30d": None,
                "policy_stance": "UNKNOWN",
                "rate_trend": "UNKNOWN",
                "source": None,
                "quality": "INSUFFICIENT_DATA",
            }

        latest = df_rates.iloc[-1]
        latest_rate = latest["value"]
        target_date = latest["date"] - pd.Timedelta(days=30)
        prior_rate = _value_on_or_before(df_rates, target_date)
        change_30d = latest_rate - prior_rate if prior_rate is not None else None
        treasury_10y = self.get_latest_value("treasury_10y")
        breakeven_10y = self.get_latest_value("breakeven_10y")
        real_yield_10y = None
        if treasury_10y is not None and breakeven_10y is not None:
            real_yield_10y = treasury_10y - breakeven_10y

        if change_30d is None:
            policy_stance = "UNKNOWN"
            rate_trend = "UNKNOWN"
            quality = "PARTIAL_DATA"
        elif change_30d <= -0.10:
            policy_stance = "CUTTING"
            rate_trend = "EASING"
            quality = "OK"
        elif change_30d >= 0.10:
            policy_stance = "RAISING"
            rate_trend = "HAWKISH"
            quality = "OK"
        else:
            if real_yield_10y is not None and real_yield_10y >= 1.50:
                policy_stance = "HOLDING_RESTRICTIVE"
                rate_trend = "RESTRICTIVE"
            else:
                policy_stance = "HOLDING"
                rate_trend = "NEUTRAL"
            quality = "OK"

        return {
            "policy_rate": round(latest_rate, 2) if latest_rate is not None else None,
            "policy_rate_change_30d": round(change_30d, 2) if change_30d is not None else None,
            "real_yield_10y": round(real_yield_10y, 2) if real_yield_10y is not None else None,
            "policy_stance": policy_stance,
            "rate_trend": rate_trend,
            "source": source,
            "quality": quality,
        }

    def analyze_yield_curve(self) -> Dict[str, Any]:
        t10 = self.get_latest_value("treasury_10y")
        t2 = self.get_latest_value("treasury_2y")
        t3m = self.get_latest_value("treasury_3m")
        s10_2 = self.get_latest_value("spread_10y_2y")
        s10_3m = self.get_latest_value("spread_10y_3m")

        if s10_2 is None and t10 is not None and t2 is not None:
            s10_2 = t10 - t2
        if s10_3m is None and t10 is not None and t3m is not None:
            s10_3m = t10 - t3m

        regime = "Normal (Steep)"
        if s10_2 is not None:
            if s10_2 < 0:
                regime = "Inverted (Recession Warning)"
            elif 0 <= s10_2 < 0.25:
                regime = "Flat / Re-steepening (Un-inversion)"
            else:
                regime = "Normal (Steep)"

        return {
            "treasury_10y": round(t10, 2) if t10 else None,
            "treasury_2y": round(t2, 2) if t2 else None,
            "treasury_3m": round(t3m, 2) if t3m else None,
            "spread_10y_2y": round(s10_2, 2) if s10_2 is not None else None,
            "spread_10y_3m": round(s10_3m, 2) if s10_3m is not None else None,
            "regime": regime
        }

    def analyze_credit_markets(self) -> Dict[str, Any]:
        hy_oas = self.get_latest_value("high_yield_oas")
        ig_oas = self.get_latest_value("invest_grade_oas")
        nfci = self.get_latest_value("chicago_fed_nfci")

        regime = "Benign (Tight Spreads)"
        if hy_oas is not None:
            if hy_oas > REGIME_THRESHOLDS["high_yield_panic"]:
                regime = "CRISIS / PANIC (Extreme Credit Stress)"
            elif hy_oas > REGIME_THRESHOLDS["high_yield_stress"]:
                regime = "ELEVATED STRESS (Credit Tightening)"
            elif hy_oas < 3.5:
                regime = "Complacent / Tight Spreads"
            else:
                regime = "Normal / Fairly Priced"

        return {
            "high_yield_oas": round(hy_oas, 2) if hy_oas else None,
            "invest_grade_oas": round(ig_oas, 2) if ig_oas else None,
            "chicago_fed_nfci": round(nfci, 2) if nfci else None,
            "regime": regime
        }

    def analyze_market_sentiment(self) -> Dict[str, Any]:
        vix = self.get_latest_value("vix")
        dxy = self.get_latest_value("dxy")
        sp500 = self.get_latest_value("sp500")
        crude = self.get_latest_value("crude_oil")
        gold = self.get_latest_value("gold")
        copper = self.get_latest_value("copper")
        cnn_fg_obs = self.storage.get_latest_observation("cnn_fear_greed_index")
        cnn_fg = cnn_fg_obs["value"] if cnn_fg_obs else None
        cnn_fg_rating = _classify_fear_greed(cnn_fg)
        cnn_fg_signal = _fear_greed_signal(cnn_fg_rating)
        if cnn_fg_obs:
            try:
                age_days = (pd.Timestamp(datetime.now().date()) - pd.to_datetime(cnn_fg_obs["date"])).days
                if age_days > 7:
                    cnn_fg = None
                    cnn_fg_rating = "Stale"
                    cnn_fg_signal = "CNN Fear & Greed reading is stale; refresh the fetch job before using it as a risk-appetite overlay."
            except Exception:
                cnn_fg = None
                cnn_fg_rating = "Stale"
                cnn_fg_signal = "CNN Fear & Greed reading has an invalid date; refresh the fetch job before using it."

        vix_state = "Low Volatility (Complacency)"
        if vix is not None:
            if vix > REGIME_THRESHOLDS["vix_panic"]:
                vix_state = "High Panic / Disruption (>30)"
            elif vix > REGIME_THRESHOLDS["vix_elevated"]:
                vix_state = "Elevated Volatility (20-30)"

        return {
            "vix": round(vix, 2) if vix else None,
            "dxy": round(dxy, 2) if dxy else None,
            "sp500": round(sp500, 2) if sp500 else None,
            "crude_oil": round(crude, 2) if crude else None,
            "gold": round(gold, 2) if gold else None,
            "copper": round(copper, 2) if copper else None,
            "vix_state": vix_state,
            "cnn_fear_greed_index": round(cnn_fg, 2) if cnn_fg is not None else None,
            "cnn_fear_greed_rating": cnn_fg_rating,
            "cnn_fear_greed_signal": cnn_fg_signal,
            "cnn_fear_greed_date": cnn_fg_obs["date"] if cnn_fg_obs else None,
        }

    def analyze_labor_and_inflation(self) -> Dict[str, Any]:
        unemployment = self.get_latest_value("unemployment_rate")
        payrolls = self.get_latest_value("nonfarm_payrolls")
        initial_claims = self.get_latest_value("initial_claims")
        be_5y = self.get_latest_value("breakeven_5y")
        be_10y = self.get_latest_value("breakeven_10y")

        df_cpi = self.storage.get_indicator_series("cpi", limit=13)
        cpi_yoy = None
        if not df_cpi.empty and len(df_cpi) >= 13:
            current_cpi = df_cpi.iloc[-1]['value']
            year_ago_cpi = df_cpi.iloc[0]['value']
            if year_ago_cpi:
                cpi_yoy = ((current_cpi / year_ago_cpi) - 1.0) * 100.0

        df_unemp = self.storage.get_indicator_series("unemployment_rate", limit=12)
        sahm_rule_triggered = False
        if not df_unemp.empty and len(df_unemp) >= 12:
            ma_3mo = df_unemp['value'].tail(3).mean()
            low_12mo = df_unemp['value'].min()
            if (ma_3mo - low_12mo) >= 0.50:
                sahm_rule_triggered = True

        df_housing = self.storage.get_indicator_series("housing_starts", limit=13)
        housing_yoy = None
        if not df_housing.empty and len(df_housing) >= 13:
            current_houst = df_housing.iloc[-1]['value']
            year_ago_houst = df_housing.iloc[0]['value']
            if year_ago_houst:
                housing_yoy = ((current_houst / year_ago_houst) - 1.0) * 100.0

        return {
            "unemployment_rate": round(unemployment, 2) if unemployment else None,
            "nonfarm_payrolls_k": round(payrolls, 1) if payrolls else None,
            "initial_claims": int(initial_claims) if initial_claims else None,
            "breakeven_5y": round(be_5y, 2) if be_5y else None,
            "breakeven_10y": round(be_10y, 2) if be_10y else None,
            "cpi_yoy": round(cpi_yoy, 2) if cpi_yoy else None,
            "housing_yoy": round(housing_yoy, 2) if housing_yoy else None,
            "sahm_rule_triggered": sahm_rule_triggered
        }

    def generate_full_snapshot(self) -> Dict[str, Any]:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        liq = self.calculate_net_liquidity()
        yc = self.analyze_yield_curve()
        policy = self.analyze_policy_stance()
        credit = self.analyze_credit_markets()
        market = self.analyze_market_sentiment()
        macro = self.analyze_labor_and_inflation()
        recent_news = self.news_analyzer.get_major_event_summary(limit=12)
        
        sector_valuations = self.valuation_engine.calculate_sector_valuations()
        self.valuation_engine.save_valuations_to_storage(sector_valuations)

        ai_ecosystem = self.ai_tracker.analyze_ecosystem_valuations()

        # Build Un-Hardcoded Raw Data Payload
        raw_payload = self.raw_engine.build_raw_payload()

        # Dynamic LLM Analysis & Single-Stock Lagging Opportunity Detection
        dynamic_analysis = self.llm_analyst.analyze_raw_payload(raw_payload)

        # 4-Quadrant Macro Situation Matrix Classification
        effr_trend = policy.get("policy_stance")
        macro_situation = self.matrix_engine.classify_situation(
            effr_trend, 
            liq.get("change_30d_billion"), 
            macro.get("cpi_yoy"), 
            macro.get("sahm_rule_triggered", False), 
            yc.get("spread_10y_2y"),
            liq.get("m2_yoy")
        )

        overall_regime = f"{macro_situation['name']} ({macro_situation['rates_label']} | {macro_situation['bs_label']})"

        if liq.get("quality") == "INSUFFICIENT_DATA":
            liquidity_regime = "Insufficient Data"
        elif liq.get("change_30d_billion") and liq["change_30d_billion"] > 0:
            liquidity_regime = "Expanding (+30d)"
        else:
            liquidity_regime = "Contracting / Neutral"

        snapshot = {
            "date": today_str,
            "net_liquidity": liq["net_liquidity"],
            "fed_assets": liq["fed_assets_billion"],
            "tga": liq["tga_billion"],
            "rrp": liq["rrp_billion"],
            "treasury_10y": yc["treasury_10y"],
            "treasury_2y": yc["treasury_2y"],
            "spread_10y_2y": yc["spread_10y_2y"],
            "high_yield_oas": credit["high_yield_oas"],
            "vix": market["vix"],
            "dxy": market["dxy"],
            "sp500": market["sp500"],
            "unemployment_rate": macro.get("unemployment_rate"),
            "cpi_yoy": macro.get("cpi_yoy"),
            "housing_yoy": macro.get("housing_yoy"),
            "breakeven_10y": macro.get("breakeven_10y"),
            "m2_yoy": liq.get("m2_yoy"),
            "policy_rate": policy.get("policy_rate"),
            "policy_rate_change_30d": policy.get("policy_rate_change_30d"),
            "real_yield_10y": policy.get("real_yield_10y"),
            "cnn_fear_greed_index": market.get("cnn_fear_greed_index"),
            "liquidity_regime": liquidity_regime,
            "yield_curve_regime": yc["regime"],
            "credit_regime": credit["regime"],
            "overall_regime": overall_regime,
            "created_at": datetime.now().isoformat()
        }

        self.storage.save_daily_snapshot(snapshot)

        tax_aware_recommendations = self.rec_engine.generate_recommendations(
            snapshot,
            credit,
            sector_valuations,
            ai_ecosystem,
            recent_news,
            macro_situation
        )
        
        lagging_opportunities = dynamic_analysis.get("single_stock_lagging_opportunities", [])
        if macro_situation.get("quality") == "INSUFFICIENT_DATA":
            for lag in lagging_opportunities:
                lag["action"] = "WATCHLIST / WAIT FOR MACRO DATA"
                lag["rationale"] = (
                    "Peer-relative discount detected, but macro quadrant data is incomplete. "
                    "Keep on watchlist and require fresh policy/liquidity confirmation before adding risk. "
                    + lag.get("rationale", "")
                )
        for rec in tax_aware_recommendations:
            grp = rec["sector"]
            rec["sector_group"] = rec.pop("sector")
            rec["selective_stock_pick"] = "None"
            for lag in lagging_opportunities:
                if lag["group"] == grp:
                    if macro_situation.get("quality") != "INSUFFICIENT_DATA" and rec["action"] == "HOLD":
                        rec["action"] = f"HOLD SECTOR / SELECTIVE BUY [{lag['ticker']}]"
                        rec["selective_stock_pick"] = lag["ticker"]
                        rec["rationale"] += f" Selective buying of lagging constituent {lag['ticker']} justified due to deep peer discount."
                    break

        return {
            "summary": snapshot,
            "liquidity_details": liq,
            "policy_details": policy,
            "yield_curve_details": yc,
            "credit_details": credit,
            "market_details": market,
            "macro_details": macro,
            "news_events": recent_news,
            "sector_valuations": sector_valuations,
            "ai_ecosystem": ai_ecosystem,
            "macro_situation": macro_situation,
            "lagging_stock_opportunities": lagging_opportunities,
            "recommendations": tax_aware_recommendations
        }
