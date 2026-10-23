#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then echo 'Install Python 3.11+ first'; exit 1; fi
if [ ! -d .venv ]; then "$PYTHON" -m venv .venv; fi
source .venv/bin/activate
if [[ " $* " == *" --live"* ]]; then
  python -m pip install -r backend/requirements-live.txt
else
  python -m pip install -r backend/requirements.txt
fi
exec python scripts/launch.py "$@"
