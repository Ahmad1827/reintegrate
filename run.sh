#!/usr/bin/env bash
# Reintegrate launcher for Linux / macOS / WSL.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt
  .venv/bin/pip install -q -r requirements-camera.txt || echo "Hand tracking not installed - keyboard only."
fi
exec .venv/bin/python main.py "$@"
