#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
echo "Dashboard: http://localhost:8000   (ctrl+c to stop)"
python desk.py ui
