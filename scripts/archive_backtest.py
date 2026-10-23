"""Inspect a stored history snapshot, without starting a server or contacting a vendor."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.archive_backtest import ArchiveNotFound, SnapshotMismatch, replay_from_archive
from app.config import settings
from app.history import HistoryError, HistoryStore
from app.registry import get_instruments


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='Offline archived backtest (research only)')
    p.add_argument('--mode', choices=('demo', 'live'), default='demo')
    p.add_argument('--instrument-id', default='US:NASDAQ:MSFT')
    p.add_argument('--strategy', choices=('PULLBACK', 'BREAKOUT'), default='PULLBACK')
    p.add_argument('--horizon', type=int, default=10)
    p.add_argument('--limit', type=int, default=2500)
    p.add_argument('--as-of')
    p.add_argument('--expected-snapshot-sha256')
    p.add_argument('--expected-universe-evidence-sha256')
    p.add_argument('--db', type=Path, default=settings.db_path.parent / 'history.sqlite')
    args = p.parse_args(argv)
    ins = next((i for i in get_instruments(args.mode) if i.instrument_id == args.instrument_id), None)
    if ins is None:
        p.error('Unknown instrument for chosen mode')
    source = 'SYNTHETIC_FIXTURE' if args.mode == 'demo' else (
        'BINANCE_SPOT_EOD' if ins.market == 'CRYPTO' else 'YFINANCE_RESEARCH_RAW')
    basis = 'SYNTHETIC' if args.mode == 'demo' else 'VENDOR_UNVERIFIED'
    try:
        result = replay_from_archive(
            HistoryStore(args.db), ins, mode=args.mode, source=source,
            price_basis=basis, strategy=args.strategy, horizon=args.horizon,
            as_of=args.as_of, limit=args.limit,
            expected_snapshot_sha256=args.expected_snapshot_sha256,
            expected_universe_evidence_sha256=args.expected_universe_evidence_sha256,
        )
    except (HistoryError, SnapshotMismatch, ArchiveNotFound) as exc:
        print(f'Archive replay rejected: {exc}', file=sys.stderr)
        return 2
    archive = result['archive_snapshot']
    print(f"{ins.symbol} / {args.strategy}: archived_rows={archive['rows']} trades={result['samples']}")
    print(f"snapshot_as_of={archive['as_of_observation']}")
    print(f"snapshot_sha256={archive['sha256']}")
    print(f"universe_evidence_sha256={archive['universe_evidence']['evidence_sha256']}")
    print(f"historical_universe={archive['universe_evidence']['status']} counts={archive['universe_evidence']['candidate_observation_counts']}")
    print(f"quality_flags={','.join(archive['quality_flags'])}")
    print(f"setup_rejections={result['diagnostics']['setup_rejection_reasons']}")
    print('RESEARCH_ONLY; verified=false; no LIVE provider call was made')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
