"""Review a locally stored historical observation snapshot; NO LIVE requests."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.history import HistoryError, HistoryStore
from app.history_quality import audit_snapshot, load_session_calendar
from app.history_evidence import load_close_reference
from app.registry import get_instruments


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='Offline research-history quality audit')
    p.add_argument('--mode', choices=('demo', 'live'), default='demo')
    p.add_argument('--instrument-id', default='US:NASDAQ:MSFT')
    p.add_argument('--as-of', help='Archived first-observed cutoff in UTC')
    p.add_argument('--calendar', type=Path, help='Optional reviewed session-list JSON; not automatically trusted')
    p.add_argument('--reference', type=Path, help='Optional offline source-close evidence JSON')
    p.add_argument('--expected-evidence-sha256', help='Reject if evidence fingerprint changed')
    p.add_argument('--limit', type=int, default=2500)
    p.add_argument('--db', type=Path, default=settings.db_path.parent / 'history.sqlite')
    p.add_argument('--json', action='store_true', help='Print structured findings')
    a = p.parse_args(argv)
    ins = next((i for i in get_instruments(a.mode) if i.instrument_id == a.instrument_id), None)
    if ins is None:
        p.error('Instrument not in allowlisted registry')
    source = 'SYNTHETIC_FIXTURE' if a.mode == 'demo' else (
        'BINANCE_SPOT_EOD' if ins.market == 'CRYPTO' else 'YFINANCE_RESEARCH_RAW')
    basis = 'SYNTHETIC' if a.mode == 'demo' else 'VENDOR_UNVERIFIED'
    try:
        store = HistoryStore(a.db)
        snapshot = store.read(ins.instrument_id, source=source, price_basis=basis,
                              as_of=a.as_of, limit=a.limit)
        if snapshot['rows'] == 0:
            raise HistoryError('No archived observations exist for this instrument and mode')
        calendar = load_session_calendar(a.calendar, ins.market) if a.calendar else None
        actions = store.actions(ins.instrument_id, source=source,
                                as_of=snapshot['as_of_observation'])
        reference = load_close_reference(a.reference) if a.reference else None
        report = audit_snapshot(ins, snapshot, calendar=calendar, actions=actions, reference=reference)
        if a.expected_evidence_sha256 and a.expected_evidence_sha256 != report['evidence_sha256']:
            raise HistoryError('Historical evidence fingerprint mismatch')
    except (HistoryError, OSError, ValueError) as exc:
        print('Quality audit rejected: ' + str(exc), file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{ins.symbol}: {report['status']} | archived_rows={report['rows']} | calendar={report['calendar_coverage']}")
        print(f"finding_counts={report['finding_counts']}")
        print(f"evidence_sha256={report['evidence_sha256']}")
        print('calendar_validated=false | corporate_actions_verified=false | point_in_time_validated=false')
    return 2 if report['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
