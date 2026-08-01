"""Render research-oriented macro reports and semantic notable-item state."""

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tabulate import tabulate
from typing import Dict, Any, Iterable, Optional, List
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


RESEARCH_DISCLOSURE = (
    "Deterministic outputs are research heuristics, not trade instructions or a "
    "validated strategy. WATCH and AVOID indicate research priority only."
)


@dataclass(frozen=True)
class NotableItem:
    """A rendered notable item with semantic state used for comparison."""

    key: str
    fingerprint: str
    body: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _as_notable_item(value: Any) -> Optional[NotableItem]:
    if isinstance(value, NotableItem):
        return value
    if not isinstance(value, dict):
        return None
    key = value.get("key")
    fingerprint = value.get("fingerprint")
    body = value.get("body")
    if not all(isinstance(item, str) for item in (key, fingerprint, body)):
        return None
    return NotableItem(key=key, fingerprint=fingerprint, body=body)


def apply_notable_change_labels(
    current_items: Iterable[NotableItem], previous_items: Iterable[Any]
) -> List[str]:
    """Label semantic notable-item changes while always rendering current bodies."""
    current_items = list(current_items)
    previous_by_key = {}
    previous_order = []
    for value in previous_items:
        item = _as_notable_item(value)
        if item is None or item.key in previous_by_key:
            continue
        previous_by_key[item.key] = item
        previous_order.append(item)

    if not previous_by_key:
        return [item.body for item in current_items]

    labeled = []
    current_keys = set()
    for item in current_items:
        current_keys.add(item.key)
        previous = previous_by_key.get(item.key)
        if previous is None:
            labeled.append(f"**New:** {item.body}")
        elif previous.fingerprint == item.fingerprint:
            labeled.append(f"**Unchanged:** {item.body}")
        else:
            labeled.append(f"**Changed:** {item.body} Previously: {previous.body}")

    for item in previous_order:
        if item.key not in current_keys:
            labeled.append(f"**Removed:** {item.body}")
    return labeled


def _atomic_write_text(path: Path, content: str) -> None:
    """Replace a report artifact without exposing a partially-written file."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temp_file:
        temp_file.write(content)
        temp_name = temp_file.name
    os.replace(temp_name, path)


class MacroReporter:
    def __init__(self, storage: Optional[MacroStorage] = None, analyzer: Optional[MacroAnalyzer] = None, output_dir: Optional[Path] = None, verbose: bool = True):
        self.storage = storage or MacroStorage()
        self.analyzer = analyzer or MacroAnalyzer(self.storage)
        self.output_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    @staticmethod
    def _score_bucket(score: Any) -> str:
        try:
            score = float(score)
        except (TypeError, ValueError):
            return "unknown"
        if score <= -6:
            return "strongly_negative"
        if score <= -2:
            return "negative"
        if score < 2:
            return "mixed"
        if score < 6:
            return "positive"
        return "strongly_positive"

    def _load_previous_notable_items(self, today_str: str) -> List[NotableItem]:
        """Load the newest dated semantic notable-state sidecar before today."""
        candidates = []
        for path in self.output_dir.glob("notable_state_*.json"):
            match = re.fullmatch(r"notable_state_(\d{4}-\d{2}-\d{2})\.json", path.name)
            if match and match.group(1) < today_str:
                candidates.append((match.group(1), path))
        if not candidates:
            return []
        _, path = max(candidates)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(loaded, list):
            return []
        return [item for value in loaded if (item := _as_notable_item(value))]

    def _write_notable_state(self, today_str: str, items: Iterable[NotableItem]) -> None:
        content = json.dumps([item.to_dict() for item in items], indent=2) + "\n"
        _atomic_write_text(self.output_dir / f"notable_state_{today_str}.json", content)
        _atomic_write_text(self.output_dir / "latest_notable_state.json", content)

    def _build_notable_items(self, analysis: Dict[str, Any]) -> List[NotableItem]:
        """Build rendered notables from stable structured fields, not prior prose."""
        macro_sit = analysis.get("macro_situation", {})
        news_events = analysis.get("news_events", [])
        assessments = analysis.get("evidence_assessments", [])
        market_details = analysis.get("market_details", {})
        items = []

        if macro_sit:
            name = md_cell(macro_sit.get("name", "N/A"))
            rates = md_cell(macro_sit.get("rates_label", "N/A"))
            liquidity = md_cell(macro_sit.get("bs_label", "N/A"))
            quality = md_cell(macro_sit.get("quality", "N/A"))
            description = md_cell(macro_sit.get("description", ""))
            items.append(NotableItem(
                key="macro:regime",
                fingerprint=f"macro:regime|{name}|{rates}|{liquidity}|{quality}",
                body=f"**Macro:** Active quadrant is `{name}` ({rates}; {liquidity}). {description}".strip(),
            ))

        for event in sorted(
            [item for item in news_events if (item.get("impact_score") or 0) >= 7],
            key=lambda item: item.get("impact_score") or 0,
            reverse=True,
        )[:3]:
            title = md_cell(event.get("title", "Untitled event"))
            category = md_cell(event.get("category", "News"))
            impact = event.get("impact_score", "N/A")
            sentiment = md_cell(event.get("sentiment", "N/A"))
            key = f"news:{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}"
            items.append(NotableItem(
                key=key,
                fingerprint=f"{key}|{category}|{impact}|{sentiment}",
                body=f"**News:** {title} ({category}; impact {impact}; {sentiment}).",
            ))

        material_assessments = [
            item for item in assessments if item.get("posture") in {"WATCH", "AVOID"}
        ]
        for assessment in material_assessments[:3]:
            sector = md_cell(assessment.get("sector_group", "Unknown sector"))
            posture = md_cell(assessment.get("posture", "NEUTRAL"))
            score = fmt_num(assessment.get("score"), ":.2f")
            score_range = assessment.get("score_range") or [None, None]
            low = fmt_num(score_range[0] if len(score_range) > 0 else None, ":.2f")
            high = fmt_num(score_range[1] if len(score_range) > 1 else None, ":.2f")
            coverage = fmt_num(assessment.get("coverage_pct"), ":.1f", "%")
            key = f"evidence:{sector.lower()}"
            items.append(NotableItem(
                key=key,
                fingerprint=f"{key}|{posture}|{self._score_bucket(assessment.get('score'))}",
                body=(f"**Evidence:** {sector} has `{posture}` research posture "
                      f"(score `{score}`, range `{low}` to `{high}`, coverage `{coverage}`)."),
            ))

        fg_value = market_details.get("cnn_fear_greed_index")
        fg_rating = market_details.get("cnn_fear_greed_rating")
        if fg_value is not None and fg_rating in {"Extreme Fear", "Extreme Greed"}:
            fg_display = fmt_num(fg_value, ":.2f")
            signal = md_cell(market_details.get("cnn_fear_greed_signal", ""))
            items.append(NotableItem(
                key="sentiment:cnn_fear_greed",
                fingerprint=f"sentiment:cnn_fear_greed|{fg_rating}",
                body=f"**Sentiment:** CNN Fear & Greed Index is `{fg_display}` (`{md_cell(fg_rating)}`). {signal}".strip(),
            ))

        shiller_pe = market_details.get("shiller_pe")
        shiller_rating = market_details.get("shiller_pe_rating")
        if shiller_pe is not None and shiller_rating in {"Expensive", "Very Expensive"}:
            shiller_display = fmt_num(shiller_pe, ":.2f")
            signal = md_cell(market_details.get("shiller_pe_signal", ""))
            items.append(NotableItem(
                key="valuation:shiller_pe",
                fingerprint=f"valuation:shiller_pe|{shiller_rating}",
                body=f"**Valuation:** Shiller PE Ratio is `{shiller_display}` (`{md_cell(shiller_rating)}`). {signal}".strip(),
            ))

        if not items:
            items.append(NotableItem(
                key="summary:none",
                fingerprint="summary:none",
                body="No notable macro, evidence, or context changes met the reporting threshold.",
            ))
        return items

    def _build_notable_summary_md(
        self, current_items: Iterable[NotableItem], previous_items: Iterable[NotableItem]
    ) -> str:
        labeled = apply_notable_change_labels(current_items, previous_items)
        return "## Notable Summary\n\n" + "\n".join(f"- {item}" for item in labeled) + "\n"

    @staticmethod
    def _factor_descriptions(items: Iterable[Any]) -> str:
        """Format factor explanations defensively for compact Markdown table cells."""
        descriptions = []
        for item in items or []:
            if isinstance(item, dict):
                description = item.get("missing_reason") or item.get("explanation")
            else:
                description = item
            if description:
                descriptions.append(md_cell(description))
        return "<br>".join(descriptions) or "—"

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
        evidence_assessments = analysis.get("evidence_assessments", [])
        constituent_assessments = analysis.get("constituent_assessments", [])
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
        if mkt.get("cnn_fear_greed_index") is not None:
            print(f"[CNN Fear & Greed]:     {fmt_num(mkt.get('cnn_fear_greed_index'), ':.2f')} ({mkt.get('cnn_fear_greed_rating', 'N/A')})")
        if mkt.get("shiller_pe") is not None:
            print(f"[Shiller PE Ratio]:    {fmt_num(mkt.get('shiller_pe'), ':.2f')} ({mkt.get('shiller_pe_rating', 'N/A')})")
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

        # 3. Sector Evidence Assessments
        if evidence_assessments:
            evidence_table = []
            for assessment in evidence_assessments:
                score_range = assessment.get("score_range") or [None, None]
                evidence_table.append([
                    assessment.get("sector_group", ""),
                    assessment.get("posture", ""),
                    fmt_num(assessment.get("score"), ":.2f"),
                    f"{fmt_num(score_range[0] if len(score_range) > 0 else None, ':.2f')} to {fmt_num(score_range[1] if len(score_range) > 1 else None, ':.2f')}",
                    fmt_num(assessment.get("coverage_pct"), ":.1f", "%"),
                    len(assessment.get("missing_evidence") or []),
                ])
            print("\n--- 3. SECTOR EVIDENCE ASSESSMENTS ---")
            print(tabulate(evidence_table, headers=["Sector Group", "Evidence Posture", "Score", "Uncertainty Range", "Coverage", "Missing Evidence"], tablefmt="grid"))

        # 4. Constituent Evidence Assessments
        if constituent_assessments:
            constituent_table = []
            for assessment in constituent_assessments[:6]:
                constituent_table.append([
                    assessment.get("ticker", ""),
                    assessment.get("group", ""),
                    assessment.get("relative_valuation_status", ""),
                    assessment.get("posture", ""),
                    len(assessment.get("missing_evidence") or []),
                ])
            print("\n--- 4. CONSTITUENT EVIDENCE ASSESSMENTS ---")
            print(tabulate(constituent_table, headers=["Ticker", "Peer Cohort", "Relative Valuation Status", "Research Posture", "Missing Evidence"], tablefmt="grid"))

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
        evidence_assessments = analysis.get("evidence_assessments", [])
        constituent_assessments = analysis.get("constituent_assessments", [])
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

        # Build sector evidence markdown section.
        evidence_section_md = ""
        if evidence_assessments:
            evidence_rows = []
            for assessment in evidence_assessments:
                score_range = assessment.get("score_range") or [None, None]
                low = fmt_num(score_range[0] if len(score_range) > 0 else None, ":.2f")
                high = fmt_num(score_range[1] if len(score_range) > 1 else None, ":.2f")
                evidence_rows.append(
                    f"| **{md_cell(assessment.get('sector_group', ''))}** | "
                    f"`{md_cell(assessment.get('posture', ''))}` | "
                    f"`{fmt_num(assessment.get('score'), ':.2f')}` | "
                    f"`{low}` to `{high}` | "
                    f"`{fmt_num(assessment.get('coverage_pct'), ':.1f', '%')}` | "
                    f"{self._factor_descriptions(assessment.get('positive_factors'))} | "
                    f"{self._factor_descriptions(assessment.get('negative_factors'))} | "
                    f"{self._factor_descriptions(assessment.get('missing_evidence'))} |"
                )
            evidence_table_md = "\n".join(evidence_rows)
            evidence_section_md = f"""
## 5. Sector Evidence Assessments

Each assessment makes its deterministic evidence, uncertainty, and missing inputs visible for research review.

| Sector / Supply Chain Group | Evidence Posture | Score | Uncertainty Range | Coverage | Positive Factors | Negative Factors | Missing Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{evidence_table_md}
"""

        # Build constituent evidence markdown section.
        constituent_section_md = ""
        if constituent_assessments:
            constituent_rows = []
            for assessment in constituent_assessments:
                constituent_rows.append(
                    f"| `{md_cell(assessment.get('ticker', ''))}` | "
                    f"{md_cell(assessment.get('group', ''))} | "
                    f"{md_cell(assessment.get('relative_valuation_status', ''))} | "
                    f"`{md_cell(assessment.get('posture', ''))}` | "
                    f"{self._factor_descriptions(assessment.get('evidence'))} | "
                    f"{self._factor_descriptions(assessment.get('missing_evidence'))} |"
                )
            constituent_table_md = "\n".join(constituent_rows)
            constituent_section_md = f"""
## 6. Constituent Evidence Assessments

Constituent review compares each company with its focused peer cohort and requires sufficient historical relative evidence.

| Ticker | Peer Cohort | Relative Valuation Status | Research Posture | Evidence | Missing Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
{constituent_table_md}
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
        fear_greed_val = fmt_num(mkt.get('cnn_fear_greed_index'), ":.2f")
        fear_greed_signal = md_cell(mkt.get('cnn_fear_greed_signal', 'N/A'))
        shiller_pe_val = fmt_num(mkt.get('shiller_pe'), ":.2f")
        shiller_pe_signal = md_cell(mkt.get('shiller_pe_signal', 'N/A'))
        current_notable_items = self._build_notable_items(analysis)
        previous_notable_items = self._load_previous_notable_items(today_str)
        notable_summary_md = self._build_notable_summary_md(
            current_notable_items, previous_notable_items
        )

        report_content = f"""# Daily Macro Evidence Report ({today_str})
*Automated Capture Engine & Institutional Research Framework (Defiant Gatekeeper)*
> {RESEARCH_DISCLOSURE}
{stale_warning_md}
---
{notable_summary_md}
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
{evidence_section_md}
---
{constituent_section_md}
---
{ai_section_md}
---

## 8. Market Risk, Volatility & Commodities

| Asset / Risk Gauge | Current Price / Level | Signal |
| :--- | :--- | :--- |
| **CBOE Volatility (VIX)** | `{vix_val}` | `{mkt.get('vix_state', 'N/A')}` |
| **US Dollar Index (DXY)** | `{dxy_val}` | Global Currency Tightness |
| **S&P 500 Index** | `{sp500_val}` | US Equity Benchmark |
| **CNN Fear & Greed Index** | `{fear_greed_val}` | `{fear_greed_signal}` |
| **Shiller PE Ratio** | `{shiller_pe_val}` | `{shiller_pe_signal}` |
| **WTI Crude Oil** | `{crude_val}` | Energy Cost Drivers |
| **Gold** | `{gold_val}` | Monetary Protection / Safe Haven |
| **Copper** | `{copper_val}` | Industrial Demand Indicator |

---
*{RESEARCH_DISCLOSURE}*
"""

        report_filename = self.output_dir / f"macro_report_{today_str}.md"
        latest_filename = self.output_dir / "latest_report.md"

        _atomic_write_text(report_filename, report_content)
        _atomic_write_text(latest_filename, report_content)
        self._write_notable_state(today_str, current_notable_items)

        if self.verbose:
            print(f"--> Daily Macro Evidence Report generated: {report_filename}")
        return str(report_filename)
