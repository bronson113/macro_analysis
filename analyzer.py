"""Macro analysis and provider-neutral research-payload orchestration."""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Mapping, Iterable
from config import REGIME_THRESHOLDS
from storage import MacroStorage
from news_analyzer import MacroNewsAnalyzer
from valuation import SectorValuationEngine
from ai_ecosystem import AIRoboticsEcosystemTracker
from raw_data_engine import RawDataEngine
from mechanical_analyst import MechanicalMacroAnalyst
from macro_matrix import MacroMatrixEngine
from recommendations import SectorEvidenceEngine
from consensus import interpret_consensus
from macro_regime import classify_liquidity_level, classify_policy_level


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


def _classify_shiller_pe(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if value < 15:
        return "Inexpensive"
    if value < 20:
        return "Fair"
    if value < 30:
        return "Elevated"
    if value < 35:
        return "Expensive"
    return "Very Expensive"


def _shiller_pe_signal(rating: Optional[str]) -> Optional[str]:
    if rating == "Inexpensive":
        return "Inexpensive secondary valuation overlay: broad equity valuations may support adding risk when macro, credit, and earnings also confirm."
    if rating == "Fair":
        return "Fair secondary valuation overlay: broad market valuation is not a major standalone headwind."
    if rating == "Elevated":
        return "Elevated secondary valuation overlay: broad market valuation requires selectivity and confirmation from liquidity, credit, and earnings."
    if rating == "Expensive":
        return "Expensive secondary valuation overlay: broad equity valuations are stretched, so avoid chasing weak setups without macro and earnings support."
    if rating == "Very Expensive":
        return "Very expensive secondary valuation overlay: broad equity valuations are stretched, so require stronger macro, credit, and earnings confirmation before adding index beta."
    return None


class MacroAnalyzer:
    def __init__(
        self,
        storage: Optional[MacroStorage] = None,
        consensus_provider: Optional[Any] = None,
    ):
        self.storage = storage or MacroStorage()
        self.consensus_provider = consensus_provider
        self.news_analyzer = MacroNewsAnalyzer(self.storage)
        self.valuation_engine = SectorValuationEngine(self.storage)
        self.ai_tracker = AIRoboticsEcosystemTracker(self.storage)
        self.raw_engine = RawDataEngine(self.storage)
        self.mechanical_analyst = MechanicalMacroAnalyst(self.storage)
        self.matrix_engine = MacroMatrixEngine()
        self.evidence_engine = SectorEvidenceEngine()

    def _load_regime_series(self) -> Dict[str, pd.DataFrame]:
        """Load the point-in-time inputs consumed by the pure regime module."""

        def series(*keys: str, limit: Optional[int] = None) -> pd.DataFrame:
            for key in keys:
                frame = self.storage.get_indicator_series(key, limit=limit)
                if not frame.empty:
                    return frame
            return pd.DataFrame(columns=["date", "value"])

        return {
            "dff": series("dff"),
            "core_pce": series("core_pce"),
            "rstar": series("rstar", "neutral_real_rate", "hlw_rstar"),
            "fed_assets": series("fed_total_assets"),
            "tga": series("tga_balance"),
            "rrp": series("reverse_repo"),
            "nominal_gdp": series("nominal_gdp"),
            # DFF is the policy input; EFFR is a separate corroboration
            # series and must remain missing when no EFFR record exists.
            "effr": series("effr"),
            "iorb": series("iorb"),
            "sofr": series("sofr"),
        }

    def _load_consensus_records(self, as_of: pd.Timestamp) -> Iterable[Mapping[str, Any]]:
        """Load optional consensus records through a non-blocking provider boundary."""

        provider = self.consensus_provider
        if provider is None:
            provider = getattr(self.storage, "get_consensus_records", None)
        if provider is None:
            return []
        try:
            if hasattr(provider, "get_records"):
                provider = provider.get_records
            if not callable(provider):
                return provider
            try:
                records = provider(as_of=as_of)
            except TypeError:
                records = provider()
            return [] if records is None else records
        except Exception:
            # Survey retrieval is an optional overlay and must never prevent a
            # current level analysis from being produced.
            return []

    @staticmethod
    def _combined_regime_quality(policy: Dict[str, Any], liquidity: Dict[str, Any]) -> str:
        qualities = {policy.get("quality"), liquidity.get("quality")}
        if "INDETERMINATE_CONFLICT" in qualities:
            return "INDETERMINATE_CONFLICT"
        if "INSUFFICIENT_DATA" in qualities:
            return "INSUFFICIENT_DATA"
        if "PARTIAL" in qualities:
            return "PARTIAL"
        return "OK"

    def analyze_macro_regime(
        self,
        as_of: Optional[pd.Timestamp] = None,
        consensus_records: Optional[Iterable[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Assemble current level states, overlays, and a pure matrix result."""

        analysis_date = pd.Timestamp(as_of if as_of is not None else datetime.now().date()).normalize()
        series = self._load_regime_series()
        policy = classify_policy_level(
            series["dff"], series["core_pce"], series["rstar"], analysis_date
        )
        liquidity = classify_liquidity_level(
            series["fed_assets"],
            series["tga"],
            series["rrp"],
            series["nominal_gdp"],
            series["effr"],
            series["iorb"],
            series["sofr"],
            analysis_date,
        )

        if consensus_records is None:
            consensus_records = self._load_consensus_records(analysis_date)
        current_assets = liquidity.get("fed_assets_billions")
        if current_assets is None:
            current_assets = liquidity.get("fed_assets_billion")
        if current_assets is None and liquidity.get("fed_assets_millions") is not None:
            current_assets = float(liquidity["fed_assets_millions"]) / 1000.0
        consensus = dict(interpret_consensus(
            consensus_records,
            policy.get("dff_value"),
            current_assets,
            analysis_date,
        ))
        consensus.setdefault("policy", consensus.get("policy_direction"))
        consensus.setdefault("balance_sheet", consensus.get("balance_sheet_direction"))
        consensus.setdefault("date", consensus.get("selected_survey_date"))
        consensus.setdefault("target", consensus.get("selected_target_date"))

        # These diagnostics remain interpretation context. They are never used
        # to infer either matrix axis.
        try:
            macro_context = self.analyze_labor_and_inflation()
        except Exception:
            macro_context = {}
        try:
            yield_context = self.analyze_yield_curve()
        except Exception:
            yield_context = {}
        try:
            net_liquidity_context = self.calculate_net_liquidity()
        except Exception:
            net_liquidity_context = {}
        momentum = {
            "policy_30d": policy.get("momentum_30d"),
            "policy_30d_value": policy.get("momentum_30d_value"),
            "policy_90d": policy.get("momentum_90d"),
            "policy_90d_value": policy.get("momentum_90d_value"),
            "liquidity_30d": liquidity.get("momentum_30d"),
            "liquidity_30d_value": liquidity.get("momentum_30d_value"),
            "liquidity_90d": liquidity.get("momentum_90d"),
            "liquidity_90d_value": liquidity.get("momentum_90d_value"),
            "policy": {
                "30d": policy.get("momentum_30d"),
                "30d_value": policy.get("momentum_30d_value"),
                "90d": policy.get("momentum_90d"),
                "90d_value": policy.get("momentum_90d_value"),
            },
            "liquidity": {
                "30d": liquidity.get("momentum_30d"),
                "30d_value": liquidity.get("momentum_30d_value"),
                "90d": liquidity.get("momentum_90d"),
                "90d_value": liquidity.get("momentum_90d_value"),
            },
        }
        quality = self._combined_regime_quality(policy, liquidity)
        data_quality = {
            "quality": quality,
            "overall": quality,
            "policy_quality": policy.get("quality"),
            "liquidity_quality": liquidity.get("quality"),
            "policy_reasons": list(policy.get("reasons") or []),
            "liquidity_reasons": list(liquidity.get("reasons") or []),
            "input_ages": {
                "dff": policy.get("dff_age_days"),
                "core_pce": policy.get("core_pce_age_days"),
                "rstar": policy.get("rstar_age_days"),
                "fed_assets": liquidity.get("fed_assets_age_days"),
                "tga": liquidity.get("tga_age_days"),
                "rrp": liquidity.get("rrp_age_days"),
                "nominal_gdp": liquidity.get("nominal_gdp_age_days"),
                "effr": liquidity.get("effr_age_days"),
                "iorb": liquidity.get("iorb_age_days"),
                "sofr": liquidity.get("sofr_age_days"),
            },
        }
        data_quality["ages"] = data_quality["input_ages"]
        context = {
            "policy": policy,
            "liquidity": liquidity,
            "momentum": momentum,
            "consensus": consensus,
            "data_quality": data_quality,
            "cpi_yoy": macro_context.get("cpi_yoy"),
            "sahm_rule_triggered": macro_context.get("sahm_rule_triggered", False),
            "spread_10y_2y": yield_context.get("spread_10y_2y"),
            "m2_yoy": net_liquidity_context.get("m2_yoy"),
            "missing_inputs": policy.get("reasons", []) + liquidity.get("reasons", []),
            "conflicts": liquidity.get("pressure_flags", []),
        }
        try:
            quadrant = self.matrix_engine.classify_situation(
                policy.get("state"),
                liquidity.get("state"),
                quality=quality,
                context=context,
            )
        except TypeError as error:
            # Keep older injected test doubles/callers usable during the
            # schema migration; the production matrix always receives the
            # explicit level-state boundary above.
            if "unexpected keyword argument" not in str(error):
                raise
            quadrant = self.matrix_engine.classify_situation(
                policy.get("state"), liquidity.get("state")
            )
        current_state = {
            "policy": policy.get("state"),
            "liquidity": liquidity.get("state"),
            "policy_state": policy.get("state"),
            "liquidity_state": liquidity.get("state"),
            "situation_id": quadrant.get("situation_id", 0),
            "policy_measurement": policy,
            "liquidity_measurement": liquidity,
            "quadrant": quadrant,
        }
        return {
            "as_of": analysis_date,
            "current_state": current_state,
            "momentum": momentum,
            "consensus": consensus,
            "data_quality": data_quality,
            "policy": policy,
            "liquidity": liquidity,
            "policy_details": policy,
            "liquidity_details": liquidity,
            "quadrant": quadrant,
            "macro_situation": quadrant,
            "quality": quality,
        }

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
        shiller_pe_obs = self.storage.get_latest_observation("shiller_pe")
        shiller_pe = shiller_pe_obs["value"] if shiller_pe_obs else None
        shiller_pe_rating = _classify_shiller_pe(shiller_pe)
        shiller_pe_signal = _shiller_pe_signal(shiller_pe_rating)
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
        if shiller_pe_obs:
            try:
                age_days = (pd.Timestamp(datetime.now().date()) - pd.to_datetime(shiller_pe_obs["date"])).days
                if age_days > 45:
                    shiller_pe = None
                    shiller_pe_rating = "Stale"
                    shiller_pe_signal = "Shiller PE reading is stale; refresh the fetch job before using it as a secondary valuation overlay."
            except Exception:
                shiller_pe = None
                shiller_pe_rating = "Stale"
                shiller_pe_signal = "Shiller PE reading has an invalid date; refresh the fetch job before using it."

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
            "shiller_pe": round(shiller_pe, 2) if shiller_pe is not None else None,
            "shiller_pe_rating": shiller_pe_rating,
            "shiller_pe_signal": shiller_pe_signal,
            "shiller_pe_date": shiller_pe_obs["date"] if shiller_pe_obs else None,
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

        # Current levels, momentum, consensus, and data quality are assembled
        # by the pure regime boundary.  The legacy analyses above remain in
        # the report as interpretation context and diagnostics.
        macro_regime = self.analyze_macro_regime(as_of=pd.Timestamp(today_str))
        regime_liq = macro_regime.get("liquidity", {})
        regime_policy = macro_regime.get("policy", {})
        consensus = macro_regime.get("consensus", {})
        macro_situation = macro_regime.get("quadrant", {})

        overall_regime = f"{macro_situation['name']} ({macro_situation['rates_label']} | {macro_situation['bs_label']})"

        if regime_liq.get("state"):
            liquidity_regime = regime_liq["state"]
        elif liq.get("quality") == "INSUFFICIENT_DATA":
            liquidity_regime = "Insufficient Data"
        elif liq.get("change_30d_billion") and liq["change_30d_billion"] > 0:
            liquidity_regime = "Expanding (+30d)"
        else:
            liquidity_regime = "Contracting / Neutral"

        input_ages = macro_regime.get("data_quality", {}).get("input_ages", {})

        def snapshot_date(value: Any) -> Optional[str]:
            if value is None or (not isinstance(value, (dict, list, tuple)) and pd.isna(value)):
                return None
            try:
                return pd.Timestamp(value).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                return str(value)

        snapshot = {
            "date": today_str,
            "net_liquidity": liq.get("net_liquidity"),
            "fed_assets": liq.get("fed_assets_billion"),
            "tga": liq.get("tga_billion"),
            "rrp": liq.get("rrp_billion"),
            "treasury_10y": yc.get("treasury_10y"),
            "treasury_2y": yc.get("treasury_2y"),
            "spread_10y_2y": yc.get("spread_10y_2y"),
            "high_yield_oas": credit.get("high_yield_oas"),
            "vix": market.get("vix"),
            "dxy": market.get("dxy"),
            "sp500": market.get("sp500"),
            "unemployment_rate": macro.get("unemployment_rate"),
            "cpi_yoy": macro.get("cpi_yoy"),
            "housing_yoy": macro.get("housing_yoy"),
            "breakeven_10y": macro.get("breakeven_10y"),
            "m2_yoy": liq.get("m2_yoy"),
            "policy_rate": policy.get("policy_rate"),
            "policy_rate_change_30d": policy.get("policy_rate_change_30d"),
            "real_yield_10y": policy.get("real_yield_10y"),
            "cnn_fear_greed_index": market.get("cnn_fear_greed_index"),
            "shiller_pe": market.get("shiller_pe"),
            "liquidity_regime": liquidity_regime,
            "yield_curve_regime": yc.get("regime"),
            "credit_regime": credit.get("regime"),
            "overall_regime": overall_regime,
            # Level-based regime fields.
            "policy_state": regime_policy.get("state"),
            "real_policy_rate": regime_policy.get("real_policy_rate"),
            "rstar": regime_policy.get("rstar_value"),
            "neutral_real_rate": regime_policy.get("neutral_real_rate"),
            "policy_gap": regime_policy.get("policy_gap"),
            "policy_rstar": regime_policy.get("rstar_value"),
            "r_star": regime_policy.get("rstar_value"),
            "policy_real_rate": regime_policy.get("real_policy_rate"),
            "policy_percentile": regime_policy.get("historical_percentile"),
            "policy_historical_percentile": regime_policy.get("historical_percentile"),
            "liquidity_state": regime_liq.get("state"),
            "normalized_liquidity_pct_gdp": regime_liq.get("normalized_liquidity_pct_gdp"),
            "liquidity_normalized_value": regime_liq.get("normalized_liquidity_pct_gdp"),
            "liquidity_normalized": regime_liq.get("normalized_liquidity_pct_gdp"),
            "liquidity_percentile": regime_liq.get("current_percentile"),
            "liquidity_current_percentile": regime_liq.get("current_percentile"),
            "liquidity_historical_median": regime_liq.get("historical_median"),
            "liquidity_historical_p40": regime_liq.get("historical_p40"),
            "liquidity_historical_p60": regime_liq.get("historical_p60"),
            "liquidity_threshold_40": regime_liq.get("historical_p40"),
            "liquidity_threshold_60": regime_liq.get("historical_p60"),
            "liquidity_p40": regime_liq.get("historical_p40"),
            "liquidity_p60": regime_liq.get("historical_p60"),
            "policy_momentum_30d": regime_policy.get("momentum_30d"),
            "policy_momentum_30d_value": regime_policy.get("momentum_30d_value"),
            "policy_momentum_90d": regime_policy.get("momentum_90d"),
            "policy_momentum_90d_value": regime_policy.get("momentum_90d_value"),
            "liquidity_momentum_30d": regime_liq.get("momentum_30d"),
            "liquidity_momentum_30d_value": regime_liq.get("momentum_30d_value"),
            "liquidity_momentum_90d": regime_liq.get("momentum_90d"),
            "liquidity_momentum_90d_value": regime_liq.get("momentum_90d_value"),
            "consensus_policy_direction": consensus.get("policy_direction"),
            "consensus_balance_sheet_direction": consensus.get("balance_sheet_direction"),
            "consensus_expected_dff": consensus.get("expected_dff"),
            "consensus_expected_fed_assets": consensus.get("expected_fed_assets"),
            "consensus_survey_date": consensus.get("selected_survey_date"),
            "consensus_target_date": consensus.get("selected_target_date"),
            "consensus_policy_date": consensus.get("selected_survey_date"),
            "consensus_balance_sheet_date": consensus.get("selected_survey_date"),
            "consensus_quality": consensus.get("quality"),
            "quadrant_quality": macro_situation.get("quality"),
            "situation_id": macro_situation.get("situation_id"),
            "input_age_dff": input_ages.get("dff"),
            "input_age_core_pce": input_ages.get("core_pce"),
            "input_age_rstar": input_ages.get("rstar"),
            "input_age_fed_assets": input_ages.get("fed_assets"),
            "input_age_tga": input_ages.get("tga"),
            "input_age_rrp": input_ages.get("rrp"),
            "input_age_nominal_gdp": input_ages.get("nominal_gdp"),
            "input_age_effr": input_ages.get("effr"),
            "input_age_iorb": input_ages.get("iorb"),
            "input_age_sofr": input_ages.get("sofr"),
            "dff_age_days": input_ages.get("dff"),
            "core_pce_age_days": input_ages.get("core_pce"),
            "rstar_age_days": input_ages.get("rstar"),
            "fed_assets_age_days": input_ages.get("fed_assets"),
            "tga_age_days": input_ages.get("tga"),
            "rrp_age_days": input_ages.get("rrp"),
            "nominal_gdp_age_days": input_ages.get("nominal_gdp"),
            "effr_age_days": input_ages.get("effr"),
            "iorb_age_days": input_ages.get("iorb"),
            "sofr_age_days": input_ages.get("sofr"),
            "policy_history_start": snapshot_date(regime_policy.get("history_start")),
            "policy_history_end": snapshot_date(regime_policy.get("history_end")),
            "policy_history_count": regime_policy.get("history_count"),
            "policy_sample_start": snapshot_date(regime_policy.get("history_start")),
            "policy_sample_end": snapshot_date(regime_policy.get("history_end")),
            "policy_sample_count": regime_policy.get("history_count"),
            "policy_history_sample_start": snapshot_date(regime_policy.get("history_start")),
            "policy_history_sample_end": snapshot_date(regime_policy.get("history_end")),
            "policy_history_sample_count": regime_policy.get("history_count"),
            "liquidity_history_start": snapshot_date(regime_liq.get("history_start")),
            "liquidity_history_end": snapshot_date(regime_liq.get("history_end")),
            "liquidity_history_count": regime_liq.get("history_count"),
            "liquidity_sample_start": snapshot_date(
                regime_liq.get("history_sample_start") or regime_liq.get("history_start")
            ),
            "liquidity_sample_end": snapshot_date(
                regime_liq.get("history_sample_end") or regime_liq.get("history_end")
            ),
            "liquidity_sample_count": regime_liq.get("history_count"),
            "liquidity_history_sample_start": snapshot_date(
                regime_liq.get("history_sample_start") or regime_liq.get("history_start")
            ),
            "liquidity_history_sample_end": snapshot_date(
                regime_liq.get("history_sample_end") or regime_liq.get("history_end")
            ),
            "liquidity_history_sample_count": regime_liq.get("history_count"),
            "created_at": datetime.now().isoformat()
        }

        self.storage.save_daily_snapshot(snapshot)

        evidence_assessments = self.evidence_engine.generate_assessments(
            snapshot,
            credit,
            sector_valuations,
            ai_ecosystem,
            recent_news,
            macro_situation
        )
        self.storage.save_signal_assessments(
            evidence_assessments, signal_date=snapshot["date"]
        )

        raw_payload = self.raw_engine.build_raw_payload(
            evidence_assessments=evidence_assessments,
            macro_regime=macro_regime,
        )
        mechanical_analysis = self.mechanical_analyst.analyze_raw_payload(raw_payload)
        constituent_assessments = mechanical_analysis.get("constituent_assessments", [])
        self.raw_engine.publish_constituent_assessments(
            raw_payload, constituent_assessments
        )

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
            "macro_regime": macro_regime,
            "current_state": macro_regime.get("current_state", {}),
            "momentum": macro_regime.get("momentum", {}),
            "consensus": macro_regime.get("consensus", {}),
            "data_quality": macro_regime.get("data_quality", {}),
            "evidence_assessments": evidence_assessments,
            "constituent_assessments": constituent_assessments,
        }
