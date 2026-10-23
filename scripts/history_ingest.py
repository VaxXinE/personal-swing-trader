"""Explicit, bounded historical archive capture. Default is OFFLINE DEMO.

LIVE is opt-in and must not be used on machines showing malware warnings.
No subprocess, shell execution, URL input, dependency install, or file downloads.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.config import settings
from app.history import HistoryStore, HistoryError
from app.providers import ProviderError, load_bars
from app.registry import get_instruments


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Append-only observed OHLCV research archive')
    parser.add_argument('--mode', choices=('demo', 'live'), default='demo')
    parser.add_argument('--allow-live', action='store_true', help='Explicit consent to call public provider APIs')
    parser.add_argument('--instrument-id', help='Exact instrument ID from existing allowlisted registry')
    parser.add_argument('--limit', type=int, default=3, help='Max number of instruments (1..19 demo or 1..25 live)')
    parser.add_argument('--db', type=Path, default=settings.db_path.parent / 'history.sqlite')
    args = parser.parse_args(argv)

    if args.mode == 'live' and not args.allow_live:
        parser.error('LIVE requires --allow-live. Do not use on a Mac that is still showing malware alerts.')
    if args.mode == 'demo' and args.allow_live:
        parser.error('--allow-live requires --mode live')
    max_limit = 25 if args.mode == 'live' else 19
    if not 1 <= args.limit <= max_limit:
        parser.error(f'--limit must be 1..{max_limit}')
    instruments = list(get_instruments(args.mode))
    if args.instrument_id:
        instruments = [i for i in instruments if i.instrument_id == args.instrument_id]
        if not instruments:
            parser.error('Unknown instrument ID; no arbitrary provider symbol or URL accepted')
    else:
        instruments = instruments[:args.limit]

    # Never silently convert provider failures into synthetic prices.
    archive = HistoryStore(args.db)
    any_errors = False
    for ins in instruments:
        try:
            bars, _quote, source, _data_status = load_bars(ins, args.mode)
            basis = 'SYNTHETIC' if args.mode == 'demo' else 'VENDOR_UNVERIFIED'
            result = archive.ingest(ins, bars, source=source, price_basis=basis,
                                    metadata={'capture_mode':args.mode, 'timeframe':'1d',
                                              'input_count':len(bars), 'feed_category':'RESEARCH_ONLY'})
            print(f"{ins.instrument_id}: received={result['received']} inserted={result['inserted']} "
                  f"unchanged={result['unchanged']} corrected={result['corrected']} "
                  f"source={source} basis={basis}")
        except (ProviderError, HistoryError, ValueError) as exc:
            print(f'{ins.instrument_id}: capture rejected: {exc}', file=sys.stderr)
            any_errors = True
    print(f'Archive: {args.db} | research only | first-observed timestamps, NOT historical PIT certification')
    return 2 if any_errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
