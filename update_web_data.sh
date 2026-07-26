#!/bin/bash

# Ensure we are in the project root
if [ ! -d "web" ] || [ ! -d "output" ]; then
    echo "Please run this script from the project root directory (macro_analysis)"
    exit 1
fi

# Extract historical data
python extract_dashboard_data.py

# Copy the latest raw payload to the web app's public directory
cp output/latest_raw_payload.json web/public/data.json
cp output/history.json web/public/history.json
cp output/latest_report.md web/public/latest_report.md
python report_manifest.py
echo "Successfully copied data.json, history.json, latest_report.md, and report history to web/public/"
