# Macro Economic Analysis & Data Capture System

This repository contains an automated framework designed to track, analyze, and report on macro-economic indicators (via FRED), market prices (via Yahoo Finance), and market sentiment. It synthesizes this data into a comprehensive snapshot of the liquidity, yield curve, and credit regimes, generating daily Markdown reports and a terminal dashboard.

> Deterministic outputs are research heuristics, not trade instructions or a validated strategy. WATCH and AVOID indicate research priority only.

## Setup

1. Ensure you have Python 3.8+ installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The system exposes a CLI through `main.py` with several sub-commands:

- **Run full daily pipeline** (fetch data, analyze, and generate report):
  ```bash
  python main.py run
  ```

- **Generate markdown reports** (from existing data):
  ```bash
  python main.py report
  ```

- **View the terminal dashboard**:
  ```bash
  python main.py dashboard
  ```

- **Check system status & logs**:
  ```bash
  python main.py status
  ```

- **Evaluate matured research outcomes** (downloads only the instruments and benchmark required by the prospective signal ledger):
  ```bash
  python main.py evaluate
  ```

- **Schedule execution**:
  ```bash
  python main.py schedule --cron
  # or run as a continuous daemon
  python main.py schedule --daemon
  ```

## Generated Outputs & State

When run, the system generates and maintains local state in the following directories:
- `data/`: CSV ledgers for indicators, observations, snapshots, news, run logs, prospective signal assessments, and source-health results. `data/macro_data.db` is a legacy SQLite artifact retained only for compatibility; current storage is CSV-backed.
- `output/`: Generated Markdown reports, raw and unified dashboard JSON, and `outcome_evaluation.json` after `python main.py evaluate` runs.
- `logs/`: System logs and execution audits.
- `cache/`: Local cache to minimize redundant API requests.

## Evidence, Sources, and Evaluation Limits

- `WATCH` marks evidence worth further research; `AVOID` marks adverse evidence requiring review; `NEUTRAL` means the current deterministic evidence does not justify either priority. These are postures, not trade directives.
- Each evidence assessment shows a score range, coverage percentage, supporting and adverse factors, and missing inputs. Missing evidence reduces confidence; it is not treated as a favorable signal.
- FRED, Yahoo Finance, Google News, and other free sources can be delayed, incomplete, rate-limited, or change format. `data/source_health.csv` records the latest fetch outcome per source key; the exported dashboard surfaces those machine-readable states instead of silently treating failed inputs as current.
- Outcome evaluation is a point-in-time research check against recorded sector postures, with a one-way 10 bps cost and no look-ahead pricing. It remains `INSUFFICIENT_SAMPLE` until at least 30 matured observations cover at least 365 elapsed days, so it is not strategy validation or a performance promise.

## Architecture

- **`fetcher.py`**: Retrieves data from FRED and Yahoo Finance.
- **`storage.py`**: Manages CSV-backed time-series ledgers and the legacy SQLite compatibility artifact.
- **`analyzer.py`**: Synthesizes the raw data into macro regime categorizations.
- **`reporter.py`**: Formats the analysis into Terminal Dashboards and Markdown reports.
- **`scheduler.py`**: Manages daily execution logic.
