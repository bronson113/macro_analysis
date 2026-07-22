"""
Main CLI entry point for Macro Economic Analysis & Data Capture System.
"""

import sys
import argparse
from datetime import datetime
from config import BASE_DIR, DB_PATH
from contextlib import closing
from storage import MacroStorage
from fetcher import MacroFetcher
from analyzer import MacroAnalyzer
from reporter import MacroReporter
from scheduler import run_daily_job, install_cron_job, run_daemon


def print_status():
    """Prints system status, indicator record counts, and last run log."""
    storage = MacroStorage()
    with closing(storage.get_connection()) as conn:
        cursor = conn.cursor()
    
        cursor.execute("SELECT COUNT(*) FROM indicators")
        ind_count = cursor.fetchone()[0]
    
        cursor.execute("SELECT COUNT(*) FROM macro_observations")
        obs_count = cursor.fetchone()[0]
    
        cursor.execute("SELECT COUNT(*) FROM daily_snapshots")
        snap_count = cursor.fetchone()[0]
    
        cursor.execute("SELECT * FROM run_logs ORDER BY run_time DESC LIMIT 5")
        logs = cursor.fetchall()

    print("\n" + "=" * 60)
    print("        MACRO ANALYSIS SYSTEM STATUS")
    print("=" * 60)
    print(f"Database Path:         {DB_PATH}")
    print(f"Tracked Indicators:   {ind_count}")
    print(f"Total Observations:    {obs_count:,}")
    print(f"Daily Snapshots Saved: {snap_count}")
    print("-" * 60)
    print("Recent Audit Logs:")
    for log in logs:
        print(f"  [{log['run_time']}] Status: {log['status']} | Records: {log['records_updated']} | Msg: {log['message']}")
    print("=" * 60 + "\n")


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
