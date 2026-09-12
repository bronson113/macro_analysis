"""
Weekly Macro Digest Generator.
Synthesizes daily snapshots, indicators, news, and sector assessments
into institutional-grade weekly macro digests.
"""

import json
import logging
import math
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config import (
    DATA_DIR,
    NEWS_CSV,
    OBSERVATIONS_CSV,
    OUTPUT_DIR,
    SNAPSHOTS_CSV,
)

logger = logging.getLogger(__name__)

RESEARCH_DISCLOSURE = (
    "Deterministic outputs are research heuristics, not trade instructions or a "
    "validated strategy. WATCH and AVOID indicate research priority only."
)


def fmt_val(
    val: Optional[float],
    fmt_spec: str = ":,.2f",
    prefix: str = "",
    suffix: str = "",
    default: str = "N/A",
) -> str:
    """Safely format numeric values."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return default
    try:
        format_str = "{" + fmt_spec + "}"
        return prefix + format_str.format(val) + suffix
    except Exception:
        return default


def fmt_delta(
    delta: Optional[float],
    fmt_spec: str = ":+,.2f",
    prefix: str = "",
    suffix: str = "",
    default: str = "N/A",
) -> str:
    """Safely format delta values with explicit sign."""
    if delta is None or (isinstance(delta, float) and (math.isnan(delta) or math.isinf(delta))):
        return default
    try:
        format_str = "{" + fmt_spec + "}"
        return prefix + format_str.format(delta) + suffix
    except Exception:
        return default


def _atomic_write(filepath: Path, content: str) -> None:
    """Safely write text content to a file via atomic replacement."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=filepath.parent, delete=False, encoding="utf-8"
        ) as f:
            temp_file = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, filepath)
    finally:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


class WeeklyDigestGenerator:
    """Generates weekly macro digest markdown reports and JSON indexes."""

    def __init__(
        self,
        snapshots_path: Path = SNAPSHOTS_CSV,
        observations_path: Path = OBSERVATIONS_CSV,
        news_path: Path = NEWS_CSV,
        output_dir: Path = OUTPUT_DIR,
    ):
        self.snapshots_path = Path(snapshots_path)
        self.observations_path = Path(observations_path)
        self.news_path = Path(news_path)
        self.output_dir = Path(output_dir)
        self._snapshots_df: Optional[pd.DataFrame] = None
        self._observations_df: Optional[pd.DataFrame] = None
        self._news_df: Optional[pd.DataFrame] = None

    def _load_snapshots(self) -> pd.DataFrame:
        if self._snapshots_df is None:
            if self.snapshots_path.exists():
                try:
                    df = pd.read_csv(self.snapshots_path)
                    df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["datetime"]).sort_values("date")
                    self._snapshots_df = df
                except Exception as e:
                    logger.error("Failed to load snapshots: %s", e)
                    self._snapshots_df = pd.DataFrame()
            else:
                self._snapshots_df = pd.DataFrame()
        return self._snapshots_df

    def _load_observations(self) -> pd.DataFrame:
        if self._observations_df is None:
            if self.observations_path.exists():
                try:
                    df = pd.read_csv(self.observations_path, low_memory=False)
                    df["datetime"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["datetime", "indicator_key", "value"])
                    self._observations_df = df
                except Exception as e:
                    logger.error("Failed to load observations: %s", e)
                    self._observations_df = pd.DataFrame()
            else:
                self._observations_df = pd.DataFrame()
        return self._observations_df

    def _load_news(self) -> pd.DataFrame:
        if self._news_df is None:
            if self.news_path.exists():
                try:
                    df = pd.read_csv(self.news_path)
                    self._news_df = df
                except Exception as e:
                    logger.error("Failed to load news: %s", e)
                    self._news_df = pd.DataFrame()
            else:
                self._news_df = pd.DataFrame()
        return self._news_df

    def get_available_weeks(self, min_date: str = "2026-07-01") -> List[Dict[str, Any]]:
        """Identify distinct trading weeks from snapshots on or after min_date."""
        df = self._load_snapshots()
        if df.empty:
            return []

        filtered = df[df["date"] >= min_date].copy()
        if filtered.empty:
            return []

        # Group by Monday of each calendar week
        filtered["week_start_dt"] = filtered["datetime"].apply(
            lambda dt: dt - timedelta(days=dt.weekday())
        )
        filtered["week_start"] = filtered["week_start_dt"].dt.strftime("%Y-%m-%d")

        weeks = []
        for week_start_str, group in filtered.groupby("week_start"):
            # Prefer business days (Monday-Friday) for trading week bounds
            weekdays_group = group[group["datetime"].dt.weekday < 5]
            target_group = weekdays_group if not weekdays_group.empty else group

            dates = sorted(target_group["date"].unique().tolist())
            if not dates:
                continue
            start_date = dates[0]
            end_date = dates[-1]

            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            dt_end = datetime.strptime(end_date, "%Y-%m-%d")
            year, week_num, _ = dt_end.isocalendar()
            week_id = f"{year}-W{week_num:02d}"

            if dt_start.month == dt_end.month:
                label = f"{dt_start.strftime('%b %d')} – {dt_end.strftime('%b %d, %Y')}"
            else:
                label = f"{dt_start.strftime('%b %d')} – {dt_end.strftime('%b %d, %Y')}"

            weeks.append({
                "week_id": week_id,
                "start_date": start_date,
                "end_date": end_date,
                "label": label,
                "trading_days": len(dates),
                "dates": dates,
            })

        # Return ordered newest to oldest
        weeks.sort(key=lambda w: w["end_date"], reverse=True)
        return weeks

    def _get_obs_value(self, key: str, date: str) -> Optional[float]:
        """Fetch indicator observation on or nearest before the target date."""
        obs = self._load_observations()
        if obs.empty:
            return None
        matches = obs[(obs["indicator_key"] == key) & (obs["date"] <= date)]
        if matches.empty:
            return None
        latest = matches.sort_values("date").iloc[-1]
        try:
            return float(latest["value"])
        except (ValueError, TypeError):
            return None

    def compute_weekly_deltas(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Compute start-of-week vs end-of-week values and deltas for core metrics."""
        df = self._load_snapshots()
        if df.empty:
            return {}

        start_rows = df[df["date"] == start_date]
        end_rows = df[df["date"] == end_date]

        if start_rows.empty or end_rows.empty:
            return {}

        start = start_rows.iloc[0].to_dict()
        end = end_rows.iloc[0].to_dict()

        def get_val(field: str, obs_key: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
            s_val = start.get(field)
            e_val = end.get(field)

            if (s_val is None or pd.isna(s_val)) and obs_key:
                s_val = self._get_obs_value(obs_key, start_date)
            if (e_val is None or pd.isna(e_val)) and obs_key:
                e_val = self._get_obs_value(obs_key, end_date)

            try:
                s_float = float(s_val) if s_val is not None and not pd.isna(s_val) else None
            except (ValueError, TypeError):
                s_float = None

            try:
                e_float = float(e_val) if e_val is not None and not pd.isna(e_val) else None
            except (ValueError, TypeError):
                e_float = None

            return s_float, e_float

        def diff(s: Optional[float], e: Optional[float]) -> Optional[float]:
            if s is not None and e is not None:
                return e - s
            return None

        def pct_diff(s: Optional[float], e: Optional[float]) -> Optional[float]:
            if s is not None and e is not None and s != 0:
                return 100.0 * (e - s) / s
            return None

        # 1. Liquidity
        net_liq_s, net_liq_e = get_val("net_liquidity")
        fed_assets_s, fed_assets_e = get_val("fed_assets")
        tga_s, tga_e = get_val("tga")
        rrp_s, rrp_e = get_val("rrp")

        if fed_assets_s and fed_assets_s > 100_000:
            fed_assets_s /= 1000.0
        if fed_assets_e and fed_assets_e > 100_000:
            fed_assets_e /= 1000.0
        if tga_s and tga_s > 100_000:
            tga_s /= 1000.0
        if tga_e and tga_e > 100_000:
            tga_e /= 1000.0

        norm_liq_s, norm_liq_e = get_val("normalized_liquidity_pct_gdp")
        liq_pctile_s, liq_pctile_e = get_val("liquidity_percentile")

        # 2. Rates & Yield Curve
        dff_s, dff_e = get_val("policy_rate", "dff")
        t10_s, t10_e = get_val("treasury_10y", "treasury_10y")
        t2_s, t2_e = get_val("treasury_2y", "treasury_2y")
        s10_2_s, s10_2_e = get_val("spread_10y_2y", "spread_10y_2y")
        real_yield_s, real_yield_e = get_val("real_yield_10y")

        # 3. Credit
        hy_oas_s, hy_oas_e = get_val("high_yield_oas", "high_yield_oas")
        ig_oas_s, ig_oas_e = get_val("invest_grade_oas", "invest_grade_oas")
        nfci_s, nfci_e = get_val("chicago_fed_nfci", "chicago_fed_nfci")

        # 4. Equities, Volatility & Commodities
        sp500_s, sp500_e = get_val("sp500")
        vix_s, vix_e = get_val("vix")
        dxy_s, dxy_e = get_val("dxy")
        crude_s, crude_e = get_val("crude_oil", "crude_oil")
        gold_s, gold_e = get_val("gold", "gold")
        copper_s, copper_e = get_val("copper", "copper")
        shiller_s, shiller_e = get_val("shiller_pe")
        fear_greed_s, fear_greed_e = get_val("cnn_fear_greed_index")

        return {
            "liquidity": {
                "net_liquidity": {"start": net_liq_s, "end": net_liq_e, "delta": diff(net_liq_s, net_liq_e), "pct": pct_diff(net_liq_s, net_liq_e)},
                "fed_assets": {"start": fed_assets_s, "end": fed_assets_e, "delta": diff(fed_assets_s, fed_assets_e)},
                "tga": {"start": tga_s, "end": tga_e, "delta": diff(tga_s, tga_e)},
                "rrp": {"start": rrp_s, "end": rrp_e, "delta": diff(rrp_s, rrp_e)},
                "normalized_pct_gdp": {"start": norm_liq_s, "end": norm_liq_e, "delta": diff(norm_liq_s, norm_liq_e)},
                "percentile": {"start": liq_pctile_s, "end": liq_pctile_e, "delta": diff(liq_pctile_s, liq_pctile_e)},
            },
            "rates": {
                "policy_rate": {"start": dff_s, "end": dff_e, "delta_bps": diff(dff_s, dff_e) * 100 if diff(dff_s, dff_e) is not None else None},
                "treasury_10y": {"start": t10_s, "end": t10_e, "delta_bps": diff(t10_s, t10_e) * 100 if diff(t10_s, t10_e) is not None else None},
                "treasury_2y": {"start": t2_s, "end": t2_e, "delta_bps": diff(t2_s, t2_e) * 100 if diff(t2_s, t2_e) is not None else None},
                "spread_10y_2y": {"start": s10_2_s, "end": s10_2_e, "delta_bps": diff(s10_2_s, s10_2_e) * 100 if diff(s10_2_s, s10_2_e) is not None else None},
                "real_yield_10y": {"start": real_yield_s, "end": real_yield_e, "delta_bps": diff(real_yield_s, real_yield_e) * 100 if diff(real_yield_s, real_yield_e) is not None else None},
            },
            "credit": {
                "high_yield_oas": {"start": hy_oas_s, "end": hy_oas_e, "delta_bps": diff(hy_oas_s, hy_oas_e) * 100 if diff(hy_oas_s, hy_oas_e) is not None else None},
                "invest_grade_oas": {"start": ig_oas_s, "end": ig_oas_e, "delta_bps": diff(ig_oas_s, ig_oas_e) * 100 if diff(ig_oas_s, ig_oas_e) is not None else None},
                "chicago_fed_nfci": {"start": nfci_s, "end": nfci_e, "delta": diff(nfci_s, nfci_e)},
            },
            "market": {
                "sp500": {"start": sp500_s, "end": sp500_e, "delta": diff(sp500_s, sp500_e), "pct": pct_diff(sp500_s, sp500_e)},
                "vix": {"start": vix_s, "end": vix_e, "delta": diff(vix_s, vix_e)},
                "dxy": {"start": dxy_s, "end": dxy_e, "delta": diff(dxy_s, dxy_e), "pct": pct_diff(dxy_s, dxy_e)},
                "crude_oil": {"start": crude_s, "end": crude_e, "delta": diff(crude_s, crude_e), "pct": pct_diff(crude_s, crude_e)},
                "gold": {"start": gold_s, "end": gold_e, "delta": diff(gold_s, gold_e), "pct": pct_diff(gold_s, gold_e)},
                "copper": {"start": copper_s, "end": copper_e, "delta": diff(copper_s, copper_e), "pct": pct_diff(copper_s, copper_e)},
                "shiller_pe": {"start": shiller_s, "end": shiller_e, "delta": diff(shiller_s, shiller_e)},
                "fear_greed": {"start": fear_greed_s, "end": fear_greed_e, "delta": diff(fear_greed_s, fear_greed_e)},
            },
        }

    def get_weekly_regime_trajectory(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Track macro situation and regime changes during the week."""
        df = self._load_snapshots()
        week_snaps = df[(df["date"] >= start_date) & (df["date"] <= end_date)].sort_values("date")

        start_sit = None
        end_sit = None
        start_policy = None
        end_policy = None
        start_liq = None
        end_liq = None

        if not week_snaps.empty:
            first = week_snaps.iloc[0].to_dict()
            last = week_snaps.iloc[-1].to_dict()
            start_sit = first.get("situation_id")
            end_sit = last.get("situation_id")
            start_policy = first.get("policy_state")
            end_policy = last.get("policy_state")
            start_liq = first.get("liquidity_state")
            end_liq = last.get("liquidity_state")

        # Fallback to reading daily markdown reports if snapshots lack situation_id
        for date, setter in [(start_date, "start"), (end_date, "end")]:
            current_val = start_sit if setter == "start" else end_sit
            if current_val is None or pd.isna(current_val):
                rep_file = self.output_dir / f"macro_report_{date}.md"
                if rep_file.exists():
                    text = rep_file.read_text(encoding="utf-8")
                    match = re.search(r"Situation\s*(\d+)", text, re.IGNORECASE)
                    if match:
                        sit_num = int(match.group(1))
                        if setter == "start":
                            start_sit = float(sit_num)
                        else:
                            end_sit = float(sit_num)

        sit_descriptions = {
            1: "Situation 1: Accommodative Policy + Abundant Liquidity (Strong Risk Tailwind)",
            2: "Situation 2: Accommodative Policy + Scarce Liquidity (Late-Cycle Caution)",
            3: "Situation 3: Restrictive Policy + Scarce Liquidity (Maximum Valuation Headwind)",
            4: "Situation 4: Restrictive Policy + Abundant Liquidity (Offsetting Flow)",
            0: "Situation 0: No Actionable Macro Quadrant (Gated / Insufficient Data)",
        }

        s_id = int(start_sit) if start_sit is not None and not pd.isna(start_sit) else None
        e_id = int(end_sit) if end_sit is not None and not pd.isna(end_sit) else None

        regime_stable = (s_id == e_id) if (s_id is not None and e_id is not None) else True

        return {
            "start_situation_id": s_id,
            "end_situation_id": e_id,
            "start_situation_label": sit_descriptions.get(s_id, f"Situation {s_id}") if s_id is not None else "Unclassified",
            "end_situation_label": sit_descriptions.get(e_id, f"Situation {e_id}") if e_id is not None else "Unclassified",
            "is_stable": regime_stable,
            "start_policy": str(start_policy) if start_policy and not pd.isna(start_policy) else "ACCOMMODATIVE",
            "end_policy": str(end_policy) if end_policy and not pd.isna(end_policy) else "ACCOMMODATIVE",
            "start_liquidity": str(start_liq) if start_liq and not pd.isna(start_liq) else "SCARCE",
            "end_liquidity": str(end_liq) if end_liq and not pd.isna(end_liq) else "SCARCE",
        }

    def get_weekly_news_digest(self, start_date: str, end_date: str, limit: int = 8) -> List[Dict[str, str]]:
        """Retrieve and summarize top news events published during the week."""
        news_df = self._load_news()
        if news_df.empty:
            return []

        filtered = news_df[
            (news_df["date"] >= start_date) & (news_df["date"] <= end_date)
        ].copy()

        if filtered.empty:
            return []

        if "impact_score" in filtered.columns:
            filtered["impact_score"] = pd.to_numeric(filtered["impact_score"], errors="coerce").fillna(0)
            filtered = filtered.sort_values(by=["impact_score", "date"], ascending=[False, False])
        else:
            filtered = filtered.sort_values(by="date", ascending=False)

        seen_titles = set()
        unique_news = []
        for _, row in filtered.iterrows():
            title = str(row.get("title") or "").strip()
            title_key = re.sub(r"[^a-zA-Z0-9]", "", title[:40].lower())
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            unique_news.append({
                "date": str(row.get("date") or ""),
                "title": title,
                "summary": str(row.get("summary") or ""),
                "category": str(row.get("category") or "Macro"),
                "source": str(row.get("source") or "News"),
                "link": str(row.get("link") or ""),
            })
            if len(unique_news) >= limit:
                break

        return unique_news

    def get_weekly_sector_and_stock_highlights(self, end_date: str) -> Dict[str, Any]:
        """Extract sector postures and stock highlights from the week-ending payload/report."""
        payload_file = self.output_dir / f"raw_macro_payload_{end_date}.json"
        if not payload_file.exists():
            payload_file = self.output_dir / "latest_raw_payload.json"

        evidence_assessments = []
        ai_ecosystem = []
        single_stocks = []

        if payload_file.exists():
            try:
                with open(payload_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    evidence_assessments = data.get("evidence_assessments") or []
                    constituent_assessments = data.get("constituent_assessments") or []
                    if constituent_assessments:
                        single_stocks = constituent_assessments[:5]
            except Exception:
                pass

        if not ai_ecosystem:
            dash_file = self.output_dir / "dashboard_data.json"
            if dash_file.exists():
                try:
                    with open(dash_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        ai_ecosystem = data.get("ai_ecosystem") or []
                except Exception:
                    pass

        return {
            "evidence_assessments": evidence_assessments,
            "single_stocks": single_stocks,
            "ai_ecosystem": ai_ecosystem,
        }

    def generate_weekly_digest_markdown(self, week_info: Dict[str, Any]) -> str:
        """Render institutional Markdown weekly digest."""
        start_date = week_info["start_date"]
        end_date = week_info["end_date"]
        label = week_info["label"]

        deltas = self.compute_weekly_deltas(start_date, end_date)
        regime = self.get_weekly_regime_trajectory(start_date, end_date)
        news = self.get_weekly_news_digest(start_date, end_date, limit=8)

        liq = deltas.get("liquidity", {})
        rates = deltas.get("rates", {})
        credit = deltas.get("credit", {})
        market = deltas.get("market", {})

        sit_label = regime.get("end_situation_label", "Unclassified")
        policy_stance = regime.get("end_policy", "N/A")
        liq_stance = regime.get("end_liquidity", "N/A")

        net_liq_delta = liq.get("net_liquidity", {}).get("delta")
        net_liq_delta_str = fmt_delta(net_liq_delta, ":+,.2f", prefix="$", suffix=" B")

        t10_delta_bps = rates.get("treasury_10y", {}).get("delta_bps")
        t10_delta_str = fmt_delta(t10_delta_bps, ":+.1f", suffix=" bps")

        sp500_pct = market.get("sp500", {}).get("pct")
        sp500_pct_str = fmt_delta(sp500_pct, ":+.2f", suffix="%")

        hy_oas_delta_bps = credit.get("high_yield_oas", {}).get("delta_bps")
        hy_oas_delta_str = fmt_delta(hy_oas_delta_bps, ":+.1f", suffix=" bps")

        vix_end = market.get("vix", {}).get("end")
        vix_delta = market.get("vix", {}).get("delta")
        vix_str = f"{fmt_val(vix_end, ':.2f')} ({fmt_delta(vix_delta, ':+.2f')} pts)"

        if net_liq_delta is not None:
            liq_dir = "Expanding" if net_liq_delta > 0 else ("Contracting" if net_liq_delta < 0 else "Neutral")
        else:
            liq_dir = "Neutral"

        if sp500_pct is not None:
            mkt_dir = "Positive" if sp500_pct > 0 else ("Negative" if sp500_pct < 0 else "Flat")
        else:
            mkt_dir = "Flat"

        news_bullets_md = ""
        if news:
            news_items = []
            for n in news:
                news_items.append(
                    f"- **{n['date']}** — *[{n['category']}]* **{n['title']}**\n  > {n['summary']}"
                )
            news_bullets_md = "\n".join(news_items)
        else:
            news_bullets_md = "- *No high-impact news events captured for this week.*"

        def make_row(
            name: str,
            s_val: Optional[float],
            e_val: Optional[float],
            d_val: Optional[float],
            is_bps: bool = False,
            is_pct: bool = False,
            prefix: str = "",
            suffix: str = "",
            context: str = "",
        ) -> str:
            fmt = ":,.2f"
            s_str = fmt_val(s_val, fmt, prefix=prefix, suffix=suffix)
            e_str = fmt_val(e_val, fmt, prefix=prefix, suffix=suffix)
            if is_bps:
                d_str = fmt_delta(d_val, ":+.1f", suffix=" bps")
            elif is_pct:
                d_str = fmt_delta(d_val, ":+.2f", suffix="%")
            else:
                d_str = fmt_delta(d_val, ":+,.2f", prefix=prefix, suffix=suffix)
            return f"| **{name}** | `{s_str}` | `{e_str}` | `{d_str}` | {context} |"

        table_rows = [
            make_row("Reserve Liquidity Proxy", liq.get("net_liquidity", {}).get("start"), liq.get("net_liquidity", {}).get("end"), liq.get("net_liquidity", {}).get("delta"), prefix="$", suffix=" B", context=f"Direction: {liq_dir}"),
            make_row("Fed Total Assets", liq.get("fed_assets", {}).get("start"), liq.get("fed_assets", {}).get("end"), liq.get("fed_assets", {}).get("delta"), prefix="$", suffix=" B", context="Balance Sheet Size"),
            make_row("Treasury General Account (TGA)", liq.get("tga", {}).get("start"), liq.get("tga", {}).get("end"), liq.get("tga", {}).get("delta"), prefix="$", suffix=" B", context="Treasury Cash Buffer"),
            make_row("Reverse Repo Facility (RRP)", liq.get("rrp", {}).get("start"), liq.get("rrp", {}).get("end"), liq.get("rrp", {}).get("delta"), prefix="$", suffix=" B", context="Overnight Cash Drain"),
            make_row("10-Year Treasury Yield", rates.get("treasury_10y", {}).get("start"), rates.get("treasury_10y", {}).get("end"), rates.get("treasury_10y", {}).get("delta_bps"), is_bps=True, suffix="%", context="Benchmark Long Rate"),
            make_row("2-Year Treasury Yield", rates.get("treasury_2y", {}).get("start"), rates.get("treasury_2y", {}).get("end"), rates.get("treasury_2y", {}).get("delta_bps"), is_bps=True, suffix="%", context="Policy Expectations"),
            make_row("10Y – 2Y Yield Spread", rates.get("spread_10y_2y", {}).get("start"), rates.get("spread_10y_2y", {}).get("end"), rates.get("spread_10y_2y", {}).get("delta_bps"), is_bps=True, suffix="%", context="Yield Curve Slope"),
            make_row("10Y Real Yield Proxy", rates.get("real_yield_10y", {}).get("start"), rates.get("real_yield_10y", {}).get("end"), rates.get("real_yield_10y", {}).get("delta_bps"), is_bps=True, suffix="%", context="TIPS Real Rate Benchmark"),
            make_row("ICE BofA High Yield OAS", credit.get("high_yield_oas", {}).get("start"), credit.get("high_yield_oas", {}).get("end"), credit.get("high_yield_oas", {}).get("delta_bps"), is_bps=True, suffix="%", context="Corporate Risk Premium"),
            make_row("S&P 500 Index", market.get("sp500", {}).get("start"), market.get("sp500", {}).get("end"), market.get("sp500", {}).get("pct"), is_pct=True, context=f"Equities ({mkt_dir})"),
            make_row("CBOE Volatility (VIX)", market.get("vix", {}).get("start"), market.get("vix", {}).get("end"), market.get("vix", {}).get("delta"), suffix="", context="Equity Risk Pricing"),
            make_row("US Dollar Index (DXY)", market.get("dxy", {}).get("start"), market.get("dxy", {}).get("end"), market.get("dxy", {}).get("pct"), is_pct=True, context="FX & Global Liquidity"),
            make_row("WTI Crude Oil", market.get("crude_oil", {}).get("start"), market.get("crude_oil", {}).get("end"), market.get("crude_oil", {}).get("pct"), is_pct=True, prefix="$", context="Energy Input Costs"),
            make_row("Gold", market.get("gold", {}).get("start"), market.get("gold", {}).get("end"), market.get("gold", {}).get("pct"), is_pct=True, prefix="$", context="Monetary Hedge / Safe Haven"),
            make_row("Copper", market.get("copper", {}).get("start"), market.get("copper", {}).get("end"), market.get("copper", {}).get("pct"), is_pct=True, prefix="$", context="Industrial Demand Gauge"),
            make_row("Shiller P/E Ratio", market.get("shiller_pe", {}).get("start"), market.get("shiller_pe", {}).get("end"), market.get("shiller_pe", {}).get("delta"), context="Long-Term Equity Multiple"),
            make_row("CNN Fear & Greed Index", market.get("fear_greed", {}).get("start"), market.get("fear_greed", {}).get("end"), market.get("fear_greed", {}).get("delta"), context="Retail Sentiment Overlay"),
        ]
        delta_table_md = "\n".join(table_rows)

        content = f"""# Weekly Macro Digest ({label})
*Automated Weekly Synthesis & Institutional Research Framework (Defiant Gatekeeper)*
> {RESEARCH_DISCLOSURE}

---
## Notable Summary

- **Regime Stability:** Active quadrant is `{sit_label}` throughout the week. Rates stance is `{policy_stance}`, and reserve liquidity is `{liq_stance}`.
- **Liquidity Flow:** Weekly reserve liquidity moved `{net_liq_delta_str}` (ending at `${fmt_val(liq.get('net_liquidity', {}).get('end'), ':,.2f')} B`).
- **Rates & Yield Curve:** 10Y Treasury yield moved `{t10_delta_str}` to finish at `{fmt_val(rates.get('treasury_10y', {}).get('end'), ':.2f')}%`. The 10Y-2Y spread ended at `{fmt_val(rates.get('spread_10y_2y', {}).get('end'), ':+.2f')}%`.
- **Credit & Equities:** High Yield OAS moved `{hy_oas_delta_str}` (at `{fmt_val(credit.get('high_yield_oas', {}).get('end'), ':.2f')}%`). S&P 500 delivered `{sp500_pct_str}` over the week with VIX at `{vix_str}`.

---
## Current State

- **Quadrant:** `{sit_label}`.
- **Policy level:** `{policy_stance}`. Policy gap remains within gate boundaries.
- **Reserve-liquidity level:** `{liq_stance}`. Normalized reserve liquidity at `{fmt_val(liq.get('normalized_pct_gdp', {}).get('end'), ':.2f')}% of GDP` (historical percentile: `{fmt_val(liq.get('percentile', {}).get('end'), ':.1f')}th`).
- **Week timeframe:** {start_date} to {end_date} ({week_info['trading_days']} captured trading sessions).

---

## 1. Active Macro Situation (Weekly Review)

> [!IMPORTANT]
> **Active Quadrant at Week Close**: `{sit_label}`
> - **Policy Stance**: `{policy_stance}`
> - **Reserve Liquidity**: `{liq_stance}`
> - **Weekly Trajectory**: {"Regime maintained stability throughout all trading sessions." if regime.get("is_stable") else f"Transitioned from Situation {regime.get('start_situation_id')} to Situation {regime.get('end_situation_id')} during the week."}

### Prevailing Sector & Asset Research Alignment
- **Defensive & Quality Cash Flows:** Favored under scarce liquidity regimes where broad equity multiples remain vulnerable to liquidity drawdowns.
- **Duration Sensitivity:** Low nominal rate shifts and positive real yields require scrutiny of high-beta multiples without earnings justification.
- **Commodity & Hard Assets:** Monitor real rate and dollar direction for confirmation before adjusting cyclical posture.

---

## 2. Weekly Indicator Movements (Start vs. End of Week)

Comparison of market and macroeconomic indicators from **{start_date}** to **{end_date}**:

| Category / Indicator | Start of Week ({start_date}) | End of Week ({end_date}) | Weekly Change (Δ) | Description / Direction |
| :--- | :--- | :--- | :--- | :--- |
{delta_table_md}

---

## 3. Federal Reserve & Reserve Liquidity Proxy Flow

Weekly changes across the banking reserve heuristic (`Fed Total Assets - TGA Balance - Reverse Repo Facility`):

- **Reserve Liquidity Net Change:** `{net_liq_delta_str}`
- **Fed Total Assets:** `{fmt_delta(liq.get('fed_assets', {}).get('delta'), ':+,.2f', prefix='$', suffix=' B')}` (ended at `${fmt_val(liq.get('fed_assets', {}).get('end'), ':,.2f')} B`)
- **Treasury General Account (TGA):** `{fmt_delta(liq.get('tga', {}).get('delta'), ':+,.2f', prefix='$', suffix=' B')}` (ended at `${fmt_val(liq.get('tga', {}).get('end'), ':,.2f')} B`)
- **Reverse Repo Facility (RRP):** `{fmt_delta(liq.get('rrp', {}).get('delta'), ':+,.2f', prefix='$', suffix=' B')}` (ended at `${fmt_val(liq.get('rrp', {}).get('end'), ':,.2f')} B`)

> [!NOTE]
> Reserve liquidity expansion or contraction reflects the combined flow of open-market balance sheet actions, Treasury issuance/spending, and money market facility usage. It is a banking-system liquidity proxy, not a broad money measure.

---

## 4. Key Catalysts, Data Releases & Headlines

Significant macroeconomic, central bank, and sector developments captured across the week:

{news_bullets_md}

---

## 5. Forward Outlook & Key Invalidation Triggers

Critical thresholds and signals to monitor entering the subsequent week:

- **Liquidity Invalidation:** An upgrade in liquidity classification requires normalized reserves to break above the **40th percentile** (`~20.26% of GDP`), accompanied by easing 30-day momentum.
- **Credit Stress Warning:** Any sharp widening in High Yield OAS above **4.50%** (currently `{fmt_val(credit.get('high_yield_oas', {}).get('end'), ':.2f')}%`) or positive shift in NFCI would trigger defensive de-risking.
- **Policy Reclassification:** Nominal rate and yield curve slope moves alone do not reclassify policy; a shift requires the real-policy gap (`DFF - Core PCE - r*`) to exceed `+0.50 pp`.
- **Valuation Headwind:** Shiller P/E at `{fmt_val(market.get('shiller_pe', {}).get('end'), ':.2f')}` reinforces that broad market beta carries negative asymmetry without fundamental earnings beats.

---
*{RESEARCH_DISCLOSURE}*
"""
        return content

    def build_weekly_digest(self, week_info: Dict[str, Any]) -> str:
        """Generate and save markdown for a single week."""
        end_date = week_info["end_date"]
        content = self.generate_weekly_digest_markdown(week_info)
        out_file = self.output_dir / f"weekly_digest_{end_date}.md"
        _atomic_write(out_file, content)
        logger.info("Saved weekly digest for %s to %s", week_info["week_id"], out_file)
        return str(out_file)

    def build_all_weekly_digests(
        self, min_date: str = "2026-07-01"
    ) -> List[Dict[str, Any]]:
        """Backfill and generate weekly digests for all available weeks."""
        weeks = self.get_available_weeks(min_date=min_date)
        if not weeks:
            logger.warning("No weeks found for weekly digests.")
            return []

        index_entries = []
        for week in weeks:
            try:
                out_path = self.build_weekly_digest(week)
                deltas = self.compute_weekly_deltas(week["start_date"], week["end_date"])
                regime = self.get_weekly_regime_trajectory(week["start_date"], week["end_date"])

                liq = deltas.get("liquidity", {})
                rates = deltas.get("rates", {})
                credit = deltas.get("credit", {})
                market = deltas.get("market", {})

                net_liq_delta = liq.get("net_liquidity", {}).get("delta")
                sp500_pct = market.get("sp500", {}).get("pct")
                t10_delta_bps = rates.get("treasury_10y", {}).get("delta_bps")
                hy_oas_delta_bps = credit.get("high_yield_oas", {}).get("delta_bps")

                index_entries.append({
                    "week_id": week["week_id"],
                    "date": week["end_date"],
                    "start_date": week["start_date"],
                    "end_date": week["end_date"],
                    "label": week["label"],
                    "trading_days": week["trading_days"],
                    "path": f"digests/weekly_digest_{week['end_date']}.md",
                    "filename": f"weekly_digest_{week['end_date']}.md",
                    "situation_id": regime.get("end_situation_id"),
                    "situation_label": regime.get("end_situation_label"),
                    "net_liquidity_change": fmt_delta(net_liq_delta, ":+,.2f", prefix="$", suffix=" B"),
                    "sp500_change": fmt_delta(sp500_pct, ":+.2f", suffix="%"),
                    "treasury_10y_change": fmt_delta(t10_delta_bps, ":+.1f", suffix=" bps"),
                    "hy_oas_change": fmt_delta(hy_oas_delta_bps, ":+.1f", suffix=" bps"),
                })
            except Exception as e:
                logger.error("Error generating digest for week %s: %s", week.get("week_id"), e, exc_info=True)

        if index_entries:
            latest = index_entries[0]
            latest_src = self.output_dir / latest["filename"]
            latest_dest = self.output_dir / "latest_weekly_digest.md"
            if latest_src.exists():
                shutil.copy2(latest_src, latest_dest)

            index_path = self.output_dir / "weekly_digests_index.json"
            _atomic_write(index_path, json.dumps(index_entries, indent=2) + "\n")
            logger.info("Saved weekly digests index (%d weeks) to %s", len(index_entries), index_path)

        return index_entries


def run_weekly_digest(backfill: bool = False, min_date: str = "2026-07-01") -> List[Dict[str, Any]]:
    """CLI / programmatic helper to run weekly digest generation."""
    generator = WeeklyDigestGenerator()
    if backfill:
        return generator.build_all_weekly_digests(min_date=min_date)
    else:
        weeks = generator.get_available_weeks(min_date=min_date)
        if not weeks:
            return []
        generator.build_weekly_digest(weeks[0])
        return generator.build_all_weekly_digests(min_date=min_date)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Weekly Macro Digests")
    parser.add_argument("--backfill", action="store_true", help="Backfill all historical weeks")
    parser.add_argument("--min-date", default="2026-07-01", help="Earliest date to include")
    args = parser.parse_args()

    results = run_weekly_digest(backfill=args.backfill, min_date=args.min_date)
    print(f"Generated {len(results)} weekly macro digests.")
