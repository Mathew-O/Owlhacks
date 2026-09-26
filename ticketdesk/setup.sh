#!/usr/bin/env bash
# Mac or Linux: bash setup.sh
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p logs
[ -f .env ] || cp .env.example .env
python -m tests.smoke
echo
echo "Setup done. Next: bash run_ui.sh   (Ollama on Mac: brew install ollama && ollama pull gemma3:4b)"
