import json
import logging
import math
import pandas as pd
import os
from config import DASHBOARD_HISTORY_DAYS, SNAPSHOTS_CSV, SOURCE_HEALTH_CSV, OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def _sanitize(val):
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as error:
        logging.warning("Could not read %s: %s", path, error)
        return default


def _latest_source_health():
    """Return the newest machine-readable health result for each fetch key."""
    if not os.path.exists(SOURCE_HEALTH_CSV):
        return []

    try:
        frame = pd.read_csv(SOURCE_HEALTH_CSV)
    except (OSError, pd.errors.EmptyDataError) as error:
        logging.warning("Could not read source-health data: %s", error)
        return []

    if frame.empty:
        return []
    if "fetch_time" in frame.columns:
        frame = frame.sort_values("fetch_time", kind="stable")
    if "fetch_key" in frame.columns:
        frame = frame.drop_duplicates(subset=["fetch_key"], keep="last")

    records = []
    for record in frame.to_dict("records"):
        records.append({
            key: None if pd.isna(value) else value
            for key, value in record.items()
        })
    return records


REGIME_SECTION_ORDER = (
    "Current State",
    "Momentum",
    "Consensus",
    "Interpretation",
    "Data Quality",
)


def _ordered_regime_sections(regime):
    """Expose the structured regime in the same decision order as reports."""
    regime = regime if isinstance(regime, dict) else {}
    current_state = regime.get("current_state")
    current_state = dict(current_state) if isinstance(current_state, dict) else {}
    if isinstance(regime.get("quadrant"), dict):
        current_state.setdefault("situation_id", regime["quadrant"].get("situation_id"))
        current_state.setdefault("quadrant", regime["quadrant"])
    if isinstance(regime.get("policy"), dict):
        current_state.setdefault("policy", regime["policy"])
    if isinstance(regime.get("liquidity"), dict):
        current_state.setdefault("liquidity", regime["liquidity"])

    return [
        {"name": REGIME_SECTION_ORDER[0], "data": current_state},
        {"name": REGIME_SECTION_ORDER[1], "data": regime.get("momentum") or {}},
        {"name": REGIME_SECTION_ORDER[2], "data": regime.get("consensus") or {}},
        {"name": REGIME_SECTION_ORDER[3], "data": regime.get("quadrant") or {}},
        {"name": REGIME_SECTION_ORDER[4], "data": regime.get("data_quality") or {}},
    ]


def export_dashboard_payload():
    """Publish a null-safe web payload with evidence, source health, and outcomes."""
    raw_payload = _read_json(OUTPUT_DIR / "latest_raw_payload.json", {})
    payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}
    payload["evidence_assessments"] = payload.get("evidence_assessments") or []
    payload["macro_regime_sections"] = _ordered_regime_sections(
        payload.get("macro_regime")
    )
    payload["source_health"] = _latest_source_health()
    payload["outcome_evaluation"] = _read_json(OUTPUT_DIR / "outcome_evaluation.json", None)

    destination = OUTPUT_DIR / "dashboard_data.json"
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, allow_nan=False)
    logging.info("Successfully exported unified dashboard payload to %s", destination)
    return payload

def extract_history():
    """Extract historical daily snapshots for dashboard timeline charts."""
    if not os.path.exists(SNAPSHOTS_CSV):
        logging.warning("No snapshots CSV found.")
        return

    try:
        df = pd.read_csv(SNAPSHOTS_CSV)
        if df.empty:
            logging.info("Snapshots CSV is empty.")
            return

        # Fetch up to the last ten years of data, ordered chronologically.
        df_sorted = df.sort_values(by='date', ascending=False).head(DASHBOARD_HISTORY_DAYS)
        
        # Keep only required columns, if they exist
        required_cols = [
            'date', 'net_liquidity', 'fed_assets', 'tga', 'rrp', 
            'treasury_10y', 'treasury_2y', 'spread_10y_2y', 'high_yield_oas', 
            'sp500', 'vix', 'dxy', 'cpi_yoy', 'policy_rate', 'real_yield_10y'
        ]
        available_cols = [c for c in required_cols if c in df_sorted.columns]
        df_sorted = df_sorted[available_cols]

        # Reverse to have chronological order for graphs (oldest to newest)
        history = df_sorted.sort_values(by='date', ascending=True).to_dict('records')
        history = [{k: _sanitize(v) for k, v in record.items()} for record in history]
        
        history_path = OUTPUT_DIR / "history.json"
        
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            
        logging.info(f"Successfully extracted {len(history)} historical records to {history_path}")
        
    except Exception as e:
        logging.error(f"Failed to extract history: {e}")

if __name__ == "__main__":
    extract_history()
    export_dashboard_payload()
