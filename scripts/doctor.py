"""Preflight diagnostics without secrets, provider calls, or side effects.

Usage: python scripts/doctor.py
"""
from __future__ import annotations
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def check(label: str, ok: bool, note: str = '') -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f' — {note}' if note else ''))
    return ok


def main() -> int:
    print('SWING INTELLIGENCE · Environment doctor')
    print('Platform:', platform.platform())
    checks = []
    checks.append(check('Python 3.11+', sys.version_info >= (3, 11), platform.python_version()))
    dependencies = ('fastapi', 'uvicorn', 'pydantic', 'httpx')
    missing = [pkg for pkg in dependencies if importlib.util.find_spec(pkg) is None]
    checks.append(check('Backend dependencies', not missing,
                        'installed' if not missing else 'missing: ' + ', '.join(missing) + ' (install backend/requirements.txt explicitly before startup)'))
    path = ROOT / 'config/universe.json'
    try:
        instruments = json.loads(path.read_text(encoding='utf-8'))['instruments']
        valid = bool(instruments) and len(instruments) <= 250
        checks.append(check('Instrument config', valid, f'{len(instruments)} instruments'))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        checks.append(check('Instrument config', False, type(exc).__name__))
    checks.append(check('Web frontend', all((ROOT / f).is_file() for f in
                        ('web/index.html', 'web/app.js', 'web/styles.css', 'web/manifest.webmanifest'))))
    print('OPTIONAL Flutter SDK:', shutil.which('flutter') or 'Not found; use Flutter setup or GitHub Actions APK build')
    print('OPTIONAL Docker:', shutil.which('docker') or 'Not found')
    print('DATA mode:', os.getenv('SWING_DATA_MODE', 'demo'))
    print('API token:', 'configured (value hidden)' if os.getenv('SWING_API_TOKEN') else 'not set (okay for loopback-only)')
    if all(checks):
        print('READY: run scripts/start.sh on macOS/Linux or scripts/start.bat on Windows.')
        return 0
    print('FIX above failures, then rerun doctor.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
