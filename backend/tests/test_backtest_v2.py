"""Offline regression tests: no provider calls, subprocesses, or network."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import pytest
from app.domain import Candle, INSTRUMENTS
from app import backtest


def make_bars(n=265, *, opening=100, high=120, low=90, close=101):
    t=datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [Candle((t + timedelta(days=i)).isoformat().replace('+00:00','Z'),
                   opening, high, low, close, 200000) for i in range(n)]


def enable_synthetic_signals(monkeypatch, *, target=115, entry=105, stop=95, atr=10):
    observed_lengths=[]
    def fake_features(prefix):
        observed_lengths.append(len(prefix))
        return {'atr_14':atr}
    def fake_setup(ins,prefix,features,strat):
        assert prefix[-1].at == make_bars(len(prefix))[-1].at
        return {'status':'QUALIFIED','target':target,'entry':entry,'stop':stop}
    monkeypatch.setattr(backtest,'calculate_features',fake_features)
    monkeypatch.setattr(backtest,'detect_strategy',fake_setup)
    monkeypatch.setattr(backtest,'liquidity',lambda *a, **k: {'historical':'PASS'})
    monkeypatch.setattr(backtest,'evaluate_research_gate',lambda *a, **k: {'status':'PASS'})
    return observed_lengths


def test_invalid_horizon_and_strategy_fail_closed():
    with pytest.raises(ValueError,match='strategy'):
        backtest.replay(INSTRUMENTS[0],make_bars(),'OTHER')
    for horizon in (0, 1, 21, True, 1.5):
        with pytest.raises(ValueError,match='horizon'):
            backtest.replay(INSTRUMENTS[0],make_bars(),horizon=horizon)


def test_backtest_never_trades_without_history_and_hides_small_sample_metrics():
    r=backtest.replay(INSTRUMENTS[0],make_bars(80))
    assert r['trades']==[] and r['samples']==0
    assert r['metrics']['net_expectancy_r'] is None
    assert r['holdout']['status']=='INSUFFICIENT_SAMPLE'
    assert r['validated'] is False


def test_next_bar_only_stops_first_and_nonoverlap(monkeypatch):
    lengths=enable_synthetic_signals(monkeypatch)
    bars=make_bars()  # each next bar hits both STOP and TARGET
    r=backtest.replay(INSTRUMENTS[0], bars, horizon=4)
    assert r['samples']>0
    assert all(t['outcome']=='STOP' for t in r['trades'])
    assert all(t['net_r'] < 0 for t in r['trades'])
    assert all(t['entry_bar_index']>210 for t in r['trades'])
    assert all(t['exit_bar_index']>=t['entry_bar_index'] for t in r['trades'])
    # Confirm signals never receive a future candle.
    assert all(211<=n<=len(bars)-4 for n in lengths)
    assert r['version']=='2.0-research' and r['validated'] is False


def test_down_gap_loses_more_than_one_r(monkeypatch):
    enable_synthetic_signals(monkeypatch, stop=95, entry=105, target=115)
    bars=make_bars()
    # Entry bar fills at 105 without touching stop/target.
    bars[211]=replace(bars[211],open=105,high=110,low=100,close=107)
    # Following session gaps below stop (95), should fill at opening 85.
    bars[212]=replace(bars[212],open=85,high=110,low=80,close=90)
    result=backtest.replay(INSTRUMENTS[0],bars,horizon=3)
    first=result['trades'][0]
    assert first['entry_bar_index']==211
    assert first['outcome']=='STOP'
    assert first['exit']==85  # adverse opening gap worse than stop
    assert first['net_r'] < -1.0


def test_future_bar_modification_does_not_change_prior_signal(monkeypatch):
    seen=[]
    def fake_features(prefix):
        seen.append((len(prefix), prefix[-1].at, prefix[-1].high))
        return {'atr_14':10}
    monkeypatch.setattr(backtest,'calculate_features',fake_features)
    monkeypatch.setattr(backtest,'detect_strategy',lambda *a, **k: {'status':'DISCOVERED','target':None})
    bars=make_bars(235)
    backtest.replay(INSTRUMENTS[0],bars,horizon=5)
    first=list(seen)
    seen.clear()
    modified=bars[:-1]+[replace(bars[-1],high=10000)]
    backtest.replay(INSTRUMENTS[0],modified,horizon=5)
    assert first==seen  # latest future candle is never in signal prefixes


def test_chronological_holdout_partition(monkeypatch):
    enable_synthetic_signals(monkeypatch)
    result=backtest.replay(INSTRUMENTS[0],make_bars(350),horizon=2)
    boundary=result['holdout_start_index']
    assert boundary==262
    for trade in result['trades']:
        expected='HOLDOUT' if trade['entry_bar_index']>=boundary else 'DEVELOPMENT'
        assert trade['partition']==expected


def test_provider_called_nowhere_in_replay(monkeypatch):
    # This module has no provider adapter by design; no HTTP or subprocess path.
    assert 'fetch_yfinance' not in backtest.replay.__code__.co_names
    assert 'subprocess' not in backtest.replay.__code__.co_names
    assert 'exec' not in backtest.replay.__code__.co_names


def test_no_fill_when_next_bar_never_reaches_trigger(monkeypatch):
    enable_synthetic_signals(monkeypatch, entry=105, target=115)
    bars=make_bars(opening=99,high=104,low=96,close=100)
    result=backtest.replay(INSTRUMENTS[0],bars,horizon=3)
    assert result['samples']==0
    assert result['research_gate_passed']>0  # gating != executed fills


def test_target_returns_positive_net_r_after_costs(monkeypatch):
    enable_synthetic_signals(monkeypatch,entry=105,stop=95,target=115)
    bars=make_bars(opening=100,high=116,low=99,close=106)
    result=backtest.replay(INSTRUMENTS[0],bars,horizon=3)
    assert result['samples']>0
    assert all(t['outcome']=='TARGET' for t in result['trades'])
    assert all(0 < t['net_r'] < 1 for t in result['trades'])


def test_invalid_candles_are_rejected_without_cleaning(monkeypatch):
    bars=make_bars(230)
    bars[30]=replace(bars[30],low=120)  # higher than close
    with pytest.raises(ValueError,match='OHLC'):
        backtest.replay(INSTRUMENTS[0],bars)
