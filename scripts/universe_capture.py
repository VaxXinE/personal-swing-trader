"""Explicit offline observation of the current candidate registry."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.history import HistoryError
from app.registry import get_instruments
from app.universe_history import UniverseHistory


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Capture an observed candidate roster (not historical membership)')
    parser.add_argument('--mode', choices=('demo', 'live'), default='demo')
    parser.add_argument('--db', type=Path, default=settings.db_path.parent / 'history.sqlite')
    args = parser.parse_args(argv)
    try:
        result = UniverseHistory(args.db).capture(get_instruments(args.mode), mode=args.mode)
    except (HistoryError, OSError, ValueError) as exc:
        print('Candidate capture rejected: ' + str(exc), file=sys.stderr)
        return 2
    print(f"{result['mode']}: observed_candidates={result['candidate_count']} unchanged={result['unchanged']}")
    print(f"observed_at={result['observed_at']}")
    print(f"sha256={result['sha256']}")
    print('RESEARCH_ONLY: candidate sample, NOT full historical listing or PIT membership evidence')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
