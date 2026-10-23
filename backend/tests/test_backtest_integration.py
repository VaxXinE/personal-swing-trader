"""End-to-end domain+research-gate+replay checks with real deterministic indicators.

No mocking of detect_strategy, liquidity, gates or data loading. All candles are
synthetic and intentionally engineered: THESE ARE NOT REAL MARKET RETURNS.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.backtest import replay
from app.domain import (
    Candle, INSTRUMENTS, calculate_features, detect_strategy,
    evaluate_research_gate, liquidity,
)


def engineered_bars(strategy: str) -> list[Candle]:
    """Uptrend, old resistance, end-of-sample signal, and next-day fill.

    Old wick at index 180 stays in the 60-day resistance window but outside
    20-day breakout window at signal index 210. Last-bar volume spikes ONLY
    for the BREAKOUT scenario. This fixture tests plumbing, not profitability.
    """
    instrument = INSTRUMENTS[0]
    first_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    for index in range(235):
        close = 100 + 0.04 * index
        opening = close - 0.1
        high = close + 0.3
        low = close - 0.3
        volume = 200_000
        if index == 180:
            high = 114  # old structural overhead; not fabricated after signal
        if index == 210 and strategy == 'BREAKOUT':
            close += 0.65
            high = close + 0.25
            low = close - 0.6
            opening = close - 0.5
            volume = 800_000  # >1.5x preceding RVOL baseline
        timestamp = (first_date + timedelta(days=index)).isoformat().replace('+00:00', 'Z')
        candles.append(Candle(timestamp, opening, high, low, close, volume, 20_000_000))

    # Construct the hypothetical fill using the actual unmodified strategy
    # logic. Only FUTURE candles are changed after the index-210 signal.
    signal = detect_strategy(instrument, candles[:211], calculate_features(candles[:211]), strategy)
    assert signal['status'] == 'QUALIFIED'
    trigger = signal['entry']
    candles[211] = replace(candles[211], open=trigger + 0.05,
                           high=trigger + 0.5, low=trigger - 0.1, close=trigger + 0.25)
    candles[212] = replace(candles[212], open=trigger + 0.3,
                           high=115, low=trigger + 0.15, close=114.5)
    return candles


@pytest.mark.parametrize('strategy', ['PULLBACK', 'BREAKOUT'])
def test_engine_accepts_real_domain_signals_without_mocking(strategy):
    ins = INSTRUMENTS[0]
    bars = engineered_bars(strategy)
    f = calculate_features(bars[:211])
    setup = detect_strategy(ins, bars[:211], f, strategy)
    assert setup['status'] == 'QUALIFIED'
    assert setup['target'] == 114.0
    assert all(c['pass'] for c in setup['criteria'])
    assert liquidity(ins, bars[:211], f, None)['historical'] == 'PASS'
    assert evaluate_research_gate(setup, 'PASS', f['atr_14'])['status'] == 'PASS'

    result = replay(ins, bars, strategy, 10)
    assert result['diagnostics']['qualified_setups'] >= 1
    assert result['diagnostics']['research_gate_passed'] >= 1
    assert result['samples'] >= 1
    first = result['trades'][0]
    assert first['entry_bar_index'] == 211
    assert first['exit_bar_index'] == 212
    assert first['outcome'] == 'TARGET'
    assert first['exit'] == 114.0
    assert first['net_r'] > 0  # engineered fixture, NOT a validated win expectation
    assert result['validated'] is False
    assert result['metrics']['status'] == 'INSUFFICIENT_SAMPLE'


def test_breakout_fixture_without_volume_spike_is_rejected():
    ins = INSTRUMENTS[0]
    bars = engineered_bars('BREAKOUT')
    bars[210] = replace(bars[210], volume=200_000)
    setup = detect_strategy(ins, bars[:211], calculate_features(bars[:211]), 'BREAKOUT')
    assert 'RVOL_LOW' in setup['reason_codes']
    result = replay(ins, bars, 'BREAKOUT', 10)
    assert result['diagnostics']['qualified_setups'] == 0
    assert result['samples'] == 0
