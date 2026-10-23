"""Reproducible OFFLINE demo-fixture coverage audit (NO LIVE provider usage).

Usage from repository root: python scripts/backtest_demo_diagnostics.py [--json]
No Run Scan, network, database writes, subprocesses, or trading operations.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.backtest import replay
from app.domain import INSTRUMENTS
from app.providers import demo_bars


def audit_demo() -> dict:
    rows = []
    totals = Counter()
    for ins in INSTRUMENTS:
        candles = demo_bars(ins)
        for strategy in ('PULLBACK', 'BREAKOUT'):
            result = replay(ins, candles, strategy=strategy, horizon=10)
            d = result['diagnostics']
            reason_counts = d['setup_rejection_reasons']
            key = max(sorted(reason_counts), key=lambda x: reason_counts[x]) if reason_counts else None
            rows.append({
                'symbol': ins.symbol,
                'market': ins.market,
                'strategy': strategy,
                'eligible_bars': d['eligible_signal_bars'],
                'qualified': d['qualified_setups'],
                'gate_passed': d['research_gate_passed'],
                'trades': d['completed_trades'],
                'most_common_rejection': key,
                'most_common_rejection_count': reason_counts.get(key, 0),
            })
            totals['eligible_bars'] += d['eligible_signal_bars']
            totals['qualified'] += d['qualified_setups']
            totals['gate_passed'] += d['research_gate_passed']
            totals['trades'] += d['completed_trades']
    return {
        'fixture': 'SYNTHETIC_DEMO_ONLY', 'research_only': True,
        'version': '1.0-offline-audit', 'instruments': len(INSTRUMENTS),
        'pairs': len(rows), 'totals': dict(totals), 'rows': rows,
        'warning': 'DEMO prices/turnovers are synthetic. Zero trades does NOT indicate a validated trading strategy or a broken backtesting engine.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Offline-only DEMO coverage diagnostics')
    parser.add_argument('--json', action='store_true', help='Emit structured JSON')
    args = parser.parse_args()
    report = audit_demo()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print('OFFLINE SYNTHETIC DEMO — not a market backtest')
        print('Instrument Strategy  Qualified Gate Trades Dominant rejection')
        for row in report['rows']:
            print(f"{row['symbol']:<10} {row['strategy']:<9} {row['qualified']:>9} "
                  f"{row['gate_passed']:>4} {row['trades']:>6} "
                  f"{row['most_common_rejection'] or 'NONE'} "
                  f"({row['most_common_rejection_count']})")
        print('Totals:', report['totals'])
        print(report['warning'])


if __name__ == '__main__':
    main()
