"""
Scheduler module for Macro Economic Analysis & Data Capture System.
Manages daily execution via cron, launchd, or daemon background loop.
"""

import sys
import time
import subprocess
import logging
from datetime import datetime
from config import BASE_DIR, LOG_DIR
from fetcher import MacroFetcher
from analyzer import MacroAnalyzer
from reporter import MacroReporter

logging.basicConfig(
    filename=LOG_DIR / "scheduler.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def run_daily_job():
    """Executes full daily data capture, macro analysis, and report generation."""
    print("=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STARTING DAILY MACRO DATA CAPTURE")
    print("=" * 60)

    try:
        # 1. Data Fetch
        fetcher = MacroFetcher()
        fetch_results = fetcher.fetch_all()
        print(f"--> Data Fetch Complete: {fetch_results['status']} ({fetch_results['total_records']} records updated)")

        # 2. Analysis & Synthesis
        analyzer = MacroAnalyzer(fetcher.storage)
        analysis = analyzer.generate_full_snapshot()

        # 3. Report & Dashboard
        reporter = MacroReporter(fetcher.storage, analyzer)
        reporter.print_terminal_dashboard(analysis)
        report_path = reporter.generate_markdown_report(analysis)

        logging.info(f"Daily macro job completed successfully. Report: {report_path}")
        print(f"--> Daily Job Successfully Completed! Report: {report_path}")

        return {
            "status": "SUCCESS",
            "fetch_results": fetch_results,
            "source_status_counts": fetch_results.get("source_status_counts", {}),
            "report_path": report_path
        }

    except Exception as e:
        err_msg = f"Error during daily macro job execution: {str(e)}"
        logging.error(err_msg, exc_info=True)
        print(f"--> ERROR: {err_msg}")
        return {"status": "ERROR", "message": err_msg}


def install_cron_job(hour: int = 8, minute: int = 0) -> str:
    """Installs standard crontab entry on Mac/Linux for daily execution."""
    python_bin = sys.executable
    main_script = BASE_DIR / "main.py"
    
    cron_command = f"{minute} {hour} * * * cd {BASE_DIR} && {python_bin} {main_script} run >> {LOG_DIR}/cron.log 2>&1"
    
    try:
        # Read current crontab
        res = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_crontab = res.stdout if res.returncode == 0 else ""
        
        # Check if already installed
        if str(main_script) in current_crontab:
            print("--> Cron job is already installed.")
            return "ALREADY_INSTALLED"
        
        # Append new cron job
        new_crontab = current_crontab.strip() + f"\n{cron_command}\n"
        
        # Write crontab
        proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
        if proc.returncode == 0:
            msg = f"Successfully installed daily cron job at {hour:02d}:{minute:02d} daily."
            print(f"--> {msg}")
            logging.info(msg)
            return "SUCCESS"
        else:
            err = f"Failed to install crontab: {proc.stderr}"
            print(f"--> {err}")
            return err
            
    except Exception as e:
        err = f"Failed to setup cron: {str(e)}"
        print(f"--> {err}")
        return err


def run_daemon(interval_seconds: int = 86400):
    """Runs continuous background daemon loop."""
    print(f"--> Starting Macro Scheduler Daemon (Interval: {interval_seconds}s)...")
    logging.info("Starting Macro Scheduler Daemon...")
    
    while True:
        run_daily_job()
        print(f"--> Daemon sleeping for {interval_seconds} seconds until next run...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--install-cron":
        install_cron_job()
    else:
        run_daily_job()
