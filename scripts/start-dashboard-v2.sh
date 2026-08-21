#!/bin/bash

set -e

cd /home/station1/station-dashboard

source venv/bin/activate

exec python3 -u v2/start-dashboard.py
