"""Compare archived strategy rejection funnels without contacting market providers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.archive_backtest import replay_from_archive
from app.config import settings
from app.history import HistoryError, HistoryStore
from app.registry import get_instruments


def summarize_replay(result: dict) -> dict:
    """Classify the deepest reached gate; rejection reasons may overlap."""
    d = result['diagnostics']
    trades = d['completed_trades']
    if not d['eligible_signal_bars']:
        bottleneck = 'INSUFFICIENT_SIGNAL_HISTORY'
    elif not d['qualified_setups']:
        bottleneck = 'TECHNICAL_SETUP'
    elif not d['research_gate_passed']:
        bottleneck = 'RESEARCH_GATE'
    elif not trades:
        bottleneck = 'NEXT_BAR_ENTRY'
    elif result['metrics']['status'] == 'INSUFFICIENT_SAMPLE':
        bottleneck = 'INSUFFICIENT_TRADE_SAMPLE'
    else:
        bottleneck = 'DESCRIPTIVE_SAMPLE_ONLY'
    return {
        'strategy': result['strategy'],
        'bottleneck': bottleneck,
        'eligible_signal_bars': d['eligible_signal_bars'],
        'qualified_setups': d['qualified_setups'],
        'research_gate_passed': d['research_gate_passed'],
        'completed_trades': trades,
        'overlap_skipped_bars': d['overlap_skipped_bars'],
        'unique_setup_rejected_bars': d.get('unique_setup_rejected_bars'),
        'exclusive_setup_rejections': d.get('exclusive_setup_rejections', {}),
        'signal_periods': d.get('signal_periods', []),
        'top_rejection_combinations': dict(sorted(
            d.get('setup_rejection_combinations', {}).items(),
            key=lambda pair: (-pair[1], pair[0]))[:5]),
        'development_samples': result['development']['samples'],
        'holdout_samples': result['holdout']['samples'],
        'metrics_status': result['metrics']['status'],
        'net_expectancy_r': result['metrics']['net_expectancy_r'],
        'rejections': {
            'technical_setup': d['setup_rejection_reasons'],
            'research_gate': d['research_gate_rejection_reasons'],
            'next_bar_entry': d['entry_rejection_reasons'],
        },
    }


def inspect_archive(store: HistoryStore, instrument, *, mode: str, strategies: tuple[str, ...],
                    horizon: int = 10, as_of: str | None = None,
                    expected_snapshot_sha256: str | None = None,
                    expected_universe_evidence_sha256: str | None = None) -> dict:
    """Hold the same archived candle and universe revisions across both strategies."""
    source = 'SYNTHETIC_FIXTURE' if mode == 'demo' else (
        'BINANCE_SPOT_EOD' if instrument.market == 'CRYPTO' else 'YFINANCE_RESEARCH_RAW')
    basis = 'SYNTHETIC' if mode == 'demo' else 'VENDOR_UNVERIFIED'
    if not strategies or any(s not in ('PULLBACK', 'BREAKOUT') for s in strategies):
        raise HistoryError('Research strategies must be PULLBACK and/or BREAKOUT')
    reports = []
    anchor = None
    for strategy in strategies:
        result = replay_from_archive(
            store, instrument, mode=mode, source=source, price_basis=basis,
            strategy=strategy, horizon=horizon,
            as_of=anchor['as_of_observation'] if anchor else as_of,
            expected_snapshot_sha256=anchor['sha256'] if anchor else expected_snapshot_sha256,
            expected_universe_evidence_sha256=(
                anchor['universe_evidence']['evidence_sha256'] if anchor
                else expected_universe_evidence_sha256),
        )
        if anchor is None:
            anchor = result['archive_snapshot']
        reports.append(summarize_replay(result))
    return {
        'instrument_id': instrument.instrument_id, 'mode': mode,
        'horizon': horizon, 'status': 'RESEARCH_ONLY', 'validated': False,
        'data_source': source, 'price_basis': basis,
        'snapshot_as_of': anchor['as_of_observation'],
        'snapshot_sha256': anchor['sha256'],
        'universe_evidence_sha256': anchor['universe_evidence']['evidence_sha256'],
        'quality_status': anchor['quality_report']['status'],
        'calendar_coverage': anchor['quality_report']['calendar_coverage'],
        'historical_membership_verified': False, 'point_in_time_validated': False,
        'friction_model': '0.1% per side, not broker-specific',
        'strategies': reports,
        'note': ('Rejection labels overlap; do not add counts to infer unique bars. '
                 'Holdout is descriptive; zero or small trade samples cannot establish profitability.'),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='Offline PULLBACK/BREAKOUT research funnel')
    p.add_argument('--mode', choices=('demo', 'live'), default='demo')
    p.add_argument('--instrument-id', default='US:NASDAQ:MSFT')
    p.add_argument('--strategy', choices=('BOTH', 'PULLBACK', 'BREAKOUT'), default='BOTH')
    p.add_argument('--horizon', type=int, default=10)
    p.add_argument('--as-of')
    p.add_argument('--expected-snapshot-sha256')
    p.add_argument('--expected-universe-evidence-sha256')
    p.add_argument('--db', type=Path, default=settings.db_path.parent / 'history.sqlite')
    p.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    ins = next((i for i in get_instruments(a.mode)
                if i.instrument_id == a.instrument_id), None)
    if ins is None:
        p.error('Unknown instrument in local registry; no arbitrary provider symbols')
    strategies = ('PULLBACK', 'BREAKOUT') if a.strategy == 'BOTH' else (a.strategy,)
    try:
        report = inspect_archive(
            HistoryStore(a.db), ins, mode=a.mode, strategies=strategies,
            horizon=a.horizon, as_of=a.as_of,
            expected_snapshot_sha256=a.expected_snapshot_sha256,
            expected_universe_evidence_sha256=a.expected_universe_evidence_sha256)
    except HistoryError as exc:
        print(f'Research diagnosis rejected: {exc}', file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{ins.instrument_id}: {report['quality_status']} | "
              f"snapshot_sha256={report['snapshot_sha256']}")
        for item in report['strategies']:
            print(f"{item['strategy']}: signals={item['eligible_signal_bars']} "
                  f"qualified={item['qualified_setups']} gate={item['research_gate_passed']} "
                  f"trades={item['completed_trades']} holdout={item['holdout_samples']} "
                  f"bottleneck={item['bottleneck']}")
            if item['exclusive_setup_rejections']:
                print(f"  exclusive_setup_rejections: {item['exclusive_setup_rejections']}")
            if item['top_rejection_combinations']:
                print(f"  top_rejection_combinations: {item['top_rejection_combinations']} "
                      '(disjoint per signal)')
            for stage, reasons in item['rejections'].items():
                if reasons:
                    top = sorted(reasons.items(), key=lambda entry: (-entry[1], entry[0]))[:5]
                    print(f"  {stage}: {dict(top)} (overlapping counts)")
            for period in item['signal_periods']:
                leading = sorted(period['setup_rejection_combinations'].items(),
                                 key=lambda pair: (-pair[1], pair[0]))[:2]
                print(f"  {period['label']}: eligible={period['eligible_signal_bars']} "
                      f"qualified={period['qualified_setups']} "
                      f"trades={period['completed_trades']} "
                      f"dates={period['first_signal_at']}..{period['last_signal_at']}")
                print(f"    top_combinations={dict(leading)} (disjoint per signal)")
        print('RESEARCH_ONLY; validated=false; no provider or broker request')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
