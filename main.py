"""
Main CLI entry point for Macro Economic Analysis & Data Capture System.
"""

import sys
import argparse
import pandas as pd
import os
import json
import tempfile
from pathlib import Path
from config import (
    DATA_DIR, INDICATORS_CSV, OBSERVATIONS_CSV, SNAPSHOTS_CSV, RUN_LOGS_CSV,
    OUTCOMES_JSON,
)
from outcome_evaluation import evaluate_signals
from storage import MacroStorage
from analyzer import MacroAnalyzer
from reporter import MacroReporter
from scheduler import run_daily_job, install_cron_job, run_daemon


def print_status():
    """Prints system status, indicator record counts, and last run log."""
    ind_count = len(pd.read_csv(INDICATORS_CSV)) if os.path.exists(INDICATORS_CSV) else 0
    obs_count = len(pd.read_csv(OBSERVATIONS_CSV)) if os.path.exists(OBSERVATIONS_CSV) else 0
    snap_count = len(pd.read_csv(SNAPSHOTS_CSV)) if os.path.exists(SNAPSHOTS_CSV) else 0
    
    logs = []
    if os.path.exists(RUN_LOGS_CSV):
        df_logs = pd.read_csv(RUN_LOGS_CSV)
        if not df_logs.empty:
            logs = df_logs.sort_values(by='run_time', ascending=False).head(5).to_dict('records')

    print("\n" + "=" * 60)
    print("        MACRO ANALYSIS SYSTEM STATUS")
    print("=" * 60)
    print(f"Data Directory:        {DATA_DIR}")
    print(f"Tracked Indicators:   {ind_count}")
    print(f"Total Observations:    {obs_count:,}")
    print(f"Daily Snapshots Saved: {snap_count}")
    print("-" * 60)
    print("Recent Audit Logs:")
    for log in logs:
        print(f"  [{log['run_time']}] Status: {log['status']} | Records: {log['records_updated']} | Msg: {log['message']}")
    print("=" * 60 + "\n")


def _required_price_tickers(signals):
    tickers = set()
    for signal in signals:
        instrument = str(signal.get("instrument") or "")
        tickers.update(part.strip() for part in instrument.split("/") if part.strip())
        benchmark = str(signal.get("benchmark") or "")
        if benchmark:
            tickers.add(benchmark)
    return sorted(tickers)


def download_signal_prices(signals):
    """Download only the ledger's required assets from its first signal date onward."""
    signal_dates = [str(signal.get("signal_date")) for signal in signals if signal.get("signal_date")]
    if not signal_dates:
        return {}
    try:
        import yfinance as yf
    except ImportError as error:
        raise RuntimeError("yfinance is required to evaluate recorded signals") from error

    start_date = min(signal_dates)
    histories = {}
    for ticker in _required_price_tickers(signals):
        history = yf.download(ticker, start=start_date, auto_adjust=True, progress=False)
        if history is None or history.empty or "Close" not in history.columns:
            continue
        closes = history["Close"]
        if hasattr(closes, "columns"):
            closes = closes.iloc[:, 0]
        histories[ticker] = [
            (str(observed_at)[:10], float(price))
            for observed_at, price in closes.dropna().items()
        ]
    return histories


def _write_json_atomically(path, payload):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=destination.parent, delete=False
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def run_evaluation(storage=None, output_path=OUTCOMES_JSON, price_loader=download_signal_prices):
    """Evaluate the prospective ledger and atomically publish a JSON sidecar."""
    storage = storage or MacroStorage()
    signals = storage.get_signal_assessments()
    prices = price_loader(signals) if signals else {}
    result = evaluate_signals(signals, prices)
    _write_json_atomically(output_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Defiant Gatekeeper Macro Analysis Data Engine")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run full daily data fetch, macro analysis & report generation")

    # dashboard command
    dash_parser = subparsers.add_parser("dashboard", help="Display macro terminal dashboard")

    # report command
    report_parser = subparsers.add_parser("report", help="Generate daily Markdown report and charts")

    # schedule command
    sched_parser = subparsers.add_parser("schedule", help="Setup automated daily scheduling")
    sched_parser.add_argument("--cron", action="store_true", help="Install macOS crontab entry")
    sched_parser.add_argument("--daemon", action="store_true", help="Run continuous background daemon")
    sched_parser.add_argument("--hour", type=int, default=8, help="Hour of day for cron (0-23)")
    sched_parser.add_argument("--minute", type=int, default=0, help="Minute of hour for cron (0-59)")

    # status command
    status_parser = subparsers.add_parser("status", help="Show system status and audit logs")

    # evaluate command
    evaluate_parser = subparsers.add_parser(
        "evaluate", help="Evaluate matured outcomes from prospective sector assessments"
    )

    args = parser.parse_args()

    try:
        if args.command == "run":
            run_daily_job()
        elif args.command == "dashboard":
            analyzer = MacroAnalyzer()
            reporter = MacroReporter()
            analysis = analyzer.generate_full_snapshot()
            reporter.print_terminal_dashboard(analysis)
        elif args.command == "report":
            analyzer = MacroAnalyzer()
            reporter = MacroReporter()
            analysis = analyzer.generate_full_snapshot()
            reporter.generate_markdown_report(analysis)
        elif args.command == "schedule":
            if args.cron:
                install_cron_job(hour=args.hour, minute=args.minute)
            elif args.daemon:
                run_daemon()
            else:
                print("Please specify --cron or --daemon. Example: python main.py schedule --cron")
        elif args.command == "status":
            print_status()
        elif args.command == "evaluate":
            result = run_evaluation()
            summary = result["summary"]
            print(
                "Outcome evaluation: "
                f"{summary['sample_size']} matured observations; {summary['status']}"
            )
        else:
            # Default action: print status & dashboard
            print_status()
            analyzer = MacroAnalyzer()
            reporter = MacroReporter()
            analysis = analyzer.generate_full_snapshot()
            reporter.print_terminal_dashboard(analysis)
    except Exception as e:
        print(f"\n[ERROR] System fault encountered: {e}")
        sys.exit(1)



if __name__ == "__main__":
    main()
