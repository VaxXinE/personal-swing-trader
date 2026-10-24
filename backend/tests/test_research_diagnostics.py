"""Offline strategy funnel diagnostics: sample scarcity is not a trading recommendation."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace

import pytest

from app.domain import INSTRUMENTS, Candle
from app.history import HistoryError, HistoryStore
from scripts.research_diagnostics import summarize_replay, inspect_archive, main


def fake_result(*, signals=20, qualified=0, gate=0, trades=0, metrics='INSUFFICIENT_SAMPLE'):
    return {
        'strategy': 'PULLBACK', 'metrics': {'status': metrics, 'net_expectancy_r': None},
        'development': {'samples': trades}, 'holdout': {'samples': 0},
        'diagnostics': {
            'eligible_signal_bars': signals, 'qualified_setups': qualified,
            'research_gate_passed': gate, 'completed_trades': trades,
            'overlap_skipped_bars': 0,
            'setup_rejection_reasons': {'TREND_NOT_ALIGNED': 12, 'RR_BELOW_MIN': 19},
            'research_gate_rejection_reasons': {},
            'entry_rejection_reasons': {},
        },
    }


@pytest.mark.parametrize(('fields', 'stage'), [
    ({'signals': 0}, 'INSUFFICIENT_SIGNAL_HISTORY'),
    ({'qualified': 0}, 'TECHNICAL_SETUP'),
    ({'qualified': 3, 'gate': 0}, 'RESEARCH_GATE'),
    ({'qualified': 3, 'gate': 2}, 'NEXT_BAR_ENTRY'),
    ({'qualified': 3, 'gate': 2, 'trades': 1}, 'INSUFFICIENT_TRADE_SAMPLE'),
    ({'qualified': 20, 'gate': 20, 'trades': 20,
      'metrics': 'DESCRIPTIVE_ONLY'}, 'DESCRIPTIVE_SAMPLE_ONLY'),
])
def test_stage_classification_is_based_on_actual_funnel(fields, stage):
    result = summarize_replay(fake_result(**fields))
    assert result['bottleneck'] == stage
    assert result['rejections']['technical_setup']['RR_BELOW_MIN'] == 19
    assert result['net_expectancy_r'] is None


def fixture_archive(tmp_path):
    store = HistoryStore(tmp_path / 'historical.sqlite',
                         clock=lambda: datetime(2026, 2, 2, tzinfo=timezone.utc))
    instrument = next(ins for ins in INSTRUMENTS if ins.instrument_id == 'US:NASDAQ:MSFT')
    stamps = []
    current = datetime(2025, 1, 1, 20, tzinfo=timezone.utc)
    while len(stamps) < 230:
        if current.weekday() < 5:
            stamps.append(current)
        current += timedelta(days=1)
    candles = [Candle(at.isoformat().replace('+00:00', 'Z'),
                      100, 104, 97, 101, 1000000) for at in stamps]
    store.ingest(instrument, candles, source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC')
    return store, instrument


def test_both_replays_share_one_fingerprint_and_do_not_use_live_providers(tmp_path, monkeypatch):
    from app import providers
    store, ins = fixture_archive(tmp_path)
    monkeypatch.setattr(providers, 'load_bars',
                        lambda *_a, **_k: pytest.fail('Unexpected network provider'))
    report = inspect_archive(store, ins, mode='demo', strategies=('PULLBACK', 'BREAKOUT'))
    assert report['status'] == 'RESEARCH_ONLY' and report['validated'] is False
    assert report['quality_status'] == 'STRUCTURAL_PASS'
    assert len(report['snapshot_sha256']) == len(report['universe_evidence_sha256']) == 64
    assert [s['strategy'] for s in report['strategies']] == ['PULLBACK', 'BREAKOUT']
    assert all(s['completed_trades'] == 0 for s in report['strategies'])
    assert not report['point_in_time_validated']
    unchanged = inspect_archive(store, ins, mode='demo', strategies=('PULLBACK', 'BREAKOUT'),
                                as_of=report['snapshot_as_of'],
                                expected_snapshot_sha256=report['snapshot_sha256'],
                                expected_universe_evidence_sha256=report['universe_evidence_sha256'])
    assert unchanged == report


def test_fails_closed_on_wrong_fingerprint_and_wrong_mode(tmp_path):
    store, ins = fixture_archive(tmp_path)
    with pytest.raises(HistoryError, match='fingerprint'):
        inspect_archive(store, ins, mode='demo', strategies=('PULLBACK', 'BREAKOUT'),
                        expected_snapshot_sha256='0' * 64)
    with pytest.raises(HistoryError, match='Source|No archived'):
        inspect_archive(store, ins, mode='live', strategies=('PULLBACK',))
    with pytest.raises(HistoryError, match='Research strategies'):
        inspect_archive(store, ins, mode='demo', strategies=('FAKE',))


def test_cli_prints_two_strategies_and_rejects_wrong_pin(tmp_path, capsys):
    store, ins = fixture_archive(tmp_path)
    code = main(['--db', str(store.path), '--mode', 'demo',
                 '--instrument-id', ins.instrument_id])
    output = capsys.readouterr().out
    assert code == 0 and 'PULLBACK:' in output and 'BREAKOUT:' in output
    assert 'overlapping counts' in output
    assert main(['--db', str(store.path), '--mode', 'demo',
                 '--instrument-id', ins.instrument_id,
                 '--expected-snapshot-sha256', '0' * 64]) == 2
    assert 'fingerprint' in capsys.readouterr().err


def test_exact_reason_sets_do_not_double_count_one_signal(tmp_path):
    store, ins = fixture_archive(tmp_path)
    from app.backtest import replay
    from app.domain import Candle

    snapshot = store.read(ins.instrument_id, source='SYNTHETIC_FIXTURE',
                          price_basis='SYNTHETIC')
    bars = [Candle(**row['candle']) for row in snapshot['candles']]
    for strategy in ('PULLBACK', 'BREAKOUT'):
        result = replay(ins, bars, strategy=strategy)
        diag = result['diagnostics']
        rejected = diag['unique_setup_rejected_bars']
        assert rejected == sum(diag['setup_rejection_combinations'].values())
        assert rejected + diag['qualified_setups'] == diag['eligible_signal_bars']
        assert sum(diag['exclusive_setup_rejections'].values()) <= rejected
        assert all('|'.join(sorted(k.split('|'))) == k for k in
                   diag['setup_rejection_combinations'])
        report = summarize_replay(result)
        assert report['unique_setup_rejected_bars'] == rejected
        assert len(report['top_rejection_combinations']) <= 5
        assert sum(report['top_rejection_combinations'].values()) <= rejected


def test_research_summary_reports_exclusive_failure_without_false_profit_claims():
    fixture = fake_result(qualified=0, trades=0)
    fixture['diagnostics']['unique_setup_rejected_bars'] = 20
    fixture['diagnostics']['exclusive_setup_rejections'] = {'RR_BELOW_MIN': 3}
    fixture['diagnostics']['setup_rejection_combinations'] = {
        'RR_BELOW_MIN': 3, 'PULLBACK_NOT_NEAR_SUPPORT|RR_BELOW_MIN': 17}
    report = summarize_replay(fixture)
    assert report['exclusive_setup_rejections'] == {'RR_BELOW_MIN': 3}
    assert report['top_rejection_combinations'] == {
        'PULLBACK_NOT_NEAR_SUPPORT|RR_BELOW_MIN': 17, 'RR_BELOW_MIN': 3}
    assert report['net_expectancy_r'] is None
    assert report['bottleneck'] == 'TECHNICAL_SETUP'
