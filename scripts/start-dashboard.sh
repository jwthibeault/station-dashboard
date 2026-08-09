#!/bin/bash

# Start Chromium if it isn't already running.
# ~/station-dashboard/scripts/start-browser.sh

# Give Chromium time to start listening on the CDP port.
sleep 5

# Go to the project directory.
cd ~/station-dashboard

# Activate the virtual environment.
source venv/bin/activate

# Start the dashboard.
cd station_dashboard
python -u main.py
