"""Deterministic long-only EOD replay with a chronological holdout.

Research simulation ONLY: no broker, intraday tape, exchange calendar, shorting,
probability estimate, or claims of out-of-sample *validation*.
"""
from __future__ import annotations

from statistics import mean, median
from math import isfinite
from .domain import (Instrument, Candle, calculate_features, detect_strategy,
                     evaluate_research_gate, liquidity, validate_candles)

MIN_WARMUP = 210
MIN_SAMPLES = 20
FRICTION_PER_SIDE = 0.001  # 10 basis points: illustrative fees + slippage proxy


def _segment(trades: list[dict]) -> dict:
    """Do not present unstable performance ratios from tiny samples."""
    n = len(trades)
    base = {'samples': n, 'status': 'DESCRIPTIVE_ONLY' if n >= MIN_SAMPLES else 'INSUFFICIENT_SAMPLE',
            'min_samples': MIN_SAMPLES, 'win_rate_pct': None,
            'net_expectancy_r': None, 'median_net_r': None, 'profit_factor': None,
            'max_drawdown_r': None}
    if n < MIN_SAMPLES:
        return base
    values = [t['net_r'] for t in trades]
    wins = sum(v > 0 for v in values)
    profits = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    equity = high_water = drawdown = 0.0
    for value in values:
        equity += value
        high_water = max(high_water, equity)
        drawdown = max(drawdown, high_water - equity)
    base.update({'win_rate_pct': round(100 * wins / n, 2),
                 'net_expectancy_r': round(mean(values), 4),
                 'median_net_r': round(median(values), 4),
                 'profit_factor': round(profits / losses, 4) if losses > 0 else None,
                 'max_drawdown_r': round(drawdown, 4)})
    return base


def replay(ins: Instrument, bars: list[Candle], strategy: str = 'PULLBACK',
           horizon: int = 10) -> dict:
    """At most one open trade per instrument. All signals use observed EOD prefixes.

    The last chronological quarter is labeled a *holdout observation*, not a
    rigorously untouched OOS validation. Neither parameters nor asset selection
    are fitted here. Signals use data <= i and hypothetical orders first activate
    on i+1. An OHLC bar that hits both barriers is assigned the STOP.
    """
    if strategy not in ('PULLBACK', 'BREAKOUT'):
        raise ValueError('strategy must be PULLBACK or BREAKOUT')
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 2 <= horizon <= 20:
        raise ValueError('horizon must be 2..20')
    if len(bars) > 2500:
        raise ValueError('backtest candle limit exceeded (2500)')
    validate_candles(bars)
    n = len(bars)
    # At least 25% of chronological rows are reserved, but only complete future
    # horizons can form trades. Report insufficient history instead of guessing.
    holdout_start = max(MIN_WARMUP + 1, int(n * 0.75)) if n else 0
    results: list[dict] = []
    candidate_count = 0
    gate_pass_count = 0
    nonoverlap_skip = 0
    next_eligible_signal = MIN_WARMUP

    for i in range(MIN_WARMUP, max(MIN_WARMUP, n - horizon)):
        if i < next_eligible_signal:
            nonoverlap_skip += 1
            continue
        prefix = bars[:i + 1]
        f = calculate_features(prefix)
        setup = detect_strategy(ins, prefix, f, strategy)
        if setup['status'] != 'QUALIFIED' or setup['target'] is None:
            continue
        candidate_count += 1
        historical_liquidity = liquidity(ins, prefix, f, None)['historical']
        gate = evaluate_research_gate(setup, historical_liquidity, f['atr_14'])
        if gate['status'] != 'PASS':
            continue
        gate_pass_count += 1
        entry, stop, target = setup['entry'], setup['stop'], setup['target']
        if not all(isfinite(v) for v in (entry, stop, target)) or not target > entry > stop > 0:
            continue
        nextbar = bars[i + 1]
        atr = f['atr_14']
        if nextbar.open > entry + 0.5 * atr:
            continue  # reject chase gaps, never assume fill at the stale trigger
        if nextbar.open >= entry:
            fill = nextbar.open
        elif nextbar.high >= entry:
            fill = entry  # same-bar sequencing ambiguous; STOP takes precedence
        else:
            continue  # one-session limit/stop research entry; unfilled is skipped
        if fill >= target:
            continue
        # Conservative fill-denominator: apply modeled entry + exit friction on
        # both profitable trades and stops, and model adverse opening gaps.
        invested = fill * (1 + FRICTION_PER_SIDE)
        modeled_stop = stop * (1 - FRICTION_PER_SIDE)
        initial_risk = invested - modeled_stop
        if not initial_risk > 0:
            continue
        outcome = 'TIMEOUT'
        exit_index = i + horizon
        exit_price = bars[exit_index].close
        for j in range(i + 1, i + horizon + 1):
            bar = bars[j]
            if bar.low <= stop:
                outcome = 'STOP'
                exit_index = j
                # A downside opening gap must not be filled at a better stop.
                exit_price = (stop if j == i + 1 and nextbar.open < entry
                              else min(stop, bar.open))
                break
            if bar.high >= target:
                outcome = 'TARGET'
                exit_index = j
                exit_price = target  # no optimistic upside gap fills
                break
        proceeds = exit_price * (1 - FRICTION_PER_SIDE)
        net_r = (proceeds - invested) / initial_risk
        if not isfinite(net_r):
            continue
        partition = 'HOLDOUT' if i + 1 >= holdout_start else 'DEVELOPMENT'
        results.append({'signal_at': bars[i].at, 'entry_at': nextbar.at,
                        'exit_at': bars[exit_index].at, 'entry': round(fill, 8),
                        'stop': round(stop, 8), 'target': round(target, 8),
                        'exit': round(exit_price, 8), 'outcome': outcome,
                        'net_r': round(net_r, 5), 'partition': partition,
                        'entry_bar_index': i + 1, 'exit_bar_index': exit_index})
        # Prevent overlapping positions. Signals on exit day may place a new
        # next-day order, but never open a position while another is active.
        next_eligible_signal = exit_index

    development = [t for t in results if t['partition'] == 'DEVELOPMENT']
    holdout = [t for t in results if t['partition'] == 'HOLDOUT']
    stats = _segment(results)
    return {
        'instrument_id': ins.instrument_id, 'strategy': strategy, 'horizon': horizon,
        'status': 'RESEARCH_ONLY', 'validated': False,
        'version': '2.0-research', 'signal_start_index': MIN_WARMUP,
        'holdout_start_index': holdout_start,
        'holdout_start_at': bars[holdout_start].at if holdout_start < n else None,
        'samples': len(results), 'net_expectancy_r': stats['net_expectancy_r'],
        'metrics': stats, 'development': _segment(development),
        'holdout': _segment(holdout), 'trades': results,
        'qualified_setups_examined': candidate_count,
        'research_gate_passed': gate_pass_count,
        'overlap_skipped_bars': nonoverlap_skip,
        'assumption': 'Final EOD signals; next-bar entry; one open trade; same-bar stop first; gap-through-stop at opening; 0.1% modeled friction each side.',
        'limitations': [
            'Chronological holdout is descriptive, not independent validation or walk-forward optimization',
            'Survivorship and candidate-selection bias: historical universe is not point-in-time',
            'Split/dividend adjustment, delistings, halts, borrow, lot/tick, fees, spread and taxes are not verified',
            'OHLC bars cannot establish intraday barrier sequence; conservative stop-first assumption',
            'No confidence intervals or probability claims; sample metrics hidden below 20 completed trades',
            'Modeled 0.1% cost each side is not the user broker fee; price gaps may exceed stops',
        ],
    }
