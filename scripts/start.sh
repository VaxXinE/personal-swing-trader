#!/usr/bin/env bash
# Local-only launcher: NEVER install or download packages on application startup.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo 'Python 3.11+ is required.' >&2; exit 1
fi
if [[ ! -f .venv/bin/activate ]]; then
  echo 'Missing .venv. Run: python3 -m venv .venv' >&2
  echo 'Then: source .venv/bin/activate && python -m pip install -r backend/requirements.txt' >&2
  echo 'For LIVE research, install backend/requirements-live.txt explicitly instead.' >&2
  exit 1
fi
source .venv/bin/activate
if ! python -c 'import fastapi, uvicorn, httpx, pydantic' >/dev/null 2>&1; then
  echo 'Required Python packages missing; installation is manual and never run at server startup.' >&2
  echo 'Run: python -m pip install -r backend/requirements.txt' >&2; exit 1
fi
for arg in "$@"; do
  if [[ "$arg" == '--live' ]] && ! python -c 'import yfinance' >/dev/null 2>&1; then
    echo 'LIVE extras missing. Explicitly run: python -m pip install -r backend/requirements-live.txt' >&2
    exit 1
  fi
done
exec python scripts/launch.py "$@"
