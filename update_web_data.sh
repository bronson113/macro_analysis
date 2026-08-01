#!/bin/bash

# Ensure we are in the project root
if [ ! -d "web" ] || [ ! -d "output" ]; then
    echo "Please run this script from the project root directory (macro_analysis)"
    exit 1
fi

# Extract historical data
python extract_dashboard_data.py

# Copy the unified payload and outcome evaluation to the web app's public directory
cp output/dashboard_data.json web/public/data.json
cp output/history.json web/public/history.json
cp output/latest_report.md web/public/latest_report.md
if [ -f output/outcome_evaluation.json ]; then
    cp output/outcome_evaluation.json web/public/outcome_evaluation.json
fi
python report_manifest.py
echo "Successfully copied the unified data.json, history.json, latest_report.md, outcome evaluation, and report history to web/public/"
