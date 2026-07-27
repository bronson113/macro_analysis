# Macro Economic Analysis & Data Capture System

This repository contains an automated framework designed to track, analyze, and report on macro-economic indicators (via FRED), market prices (via Yahoo Finance), and market sentiment. It synthesizes this data into a comprehensive snapshot of the liquidity, yield curve, and credit regimes, generating daily Markdown reports and a terminal dashboard.

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

- **Schedule execution**:
  ```bash
  python main.py schedule --cron
  # or run as a continuous daemon
  python main.py schedule --daemon
  ```

## Generated Outputs & State

When run, the system generates and maintains local state in the following directories:
- `data/`: Contains `macro_data.db`, an SQLite database maintaining all historical indicator observations, snapshots, and logs.
- `output/`: Contains the generated Markdown reports (e.g., `macro_report_YYYY-MM-DD.md` and `latest_report.md`).
- `logs/`: System logs and execution audits.
- `cache/`: Local cache to minimize redundant API requests.

## Architecture

- **`fetcher.py`**: Retrieves data from FRED and Yahoo Finance.
- **`storage.py`**: Manages the SQLite database and time-series data.
- **`analyzer.py`**: Synthesizes the raw data into macro regime categorizations.
- **`reporter.py`**: Formats the analysis into Terminal Dashboards and Markdown reports.
- **`scheduler.py`**: Manages daily execution logic.
