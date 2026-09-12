#!/bin/bash

# Ensure we are in the project root
if [ ! -d "web" ] || [ ! -d "output" ]; then
    echo "Please run this script from the project root directory (macro_analysis)"
    exit 1
fi

# Detect python binary
if [ -f "./.venv/bin/python" ]; then
    PYTHON="./.venv/bin/python"
elif [ -f "./.venv/bin/python3" ]; then
    PYTHON="./.venv/bin/python3"
else
    PYTHON="python"
fi

# Extract historical data
$PYTHON extract_dashboard_data.py

# Generate weekly macro digests
$PYTHON weekly_digest.py --backfill


# Copy the unified payload and outcome evaluation to the web app's public directory
cp output/dashboard_data.json web/public/data.json
cp output/history.json web/public/history.json
cp output/latest_report.md web/public/latest_report.md
if [ -f output/latest_weekly_digest.md ]; then
    cp output/latest_weekly_digest.md web/public/latest_weekly_digest.md
fi
if [ -f output/outcome_evaluation.json ]; then
    cp output/outcome_evaluation.json web/public/outcome_evaluation.json
fi
$PYTHON report_manifest.py
echo "Successfully copied the unified data.json, history.json, latest_report.md, outcome evaluation, and report history to web/public/"

