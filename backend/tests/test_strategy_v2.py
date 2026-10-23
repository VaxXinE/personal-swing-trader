"""Swing Research Gate V2 offline, price-based contract tests."""
from copy import deepcopy
from dataclasses import replace
from math import isfinite
from app.domain import (Candle, INSTRUMENTS, analyze,
                        calculate_features, detect_strategy, evaluate_research_gate)
from app.providers import demo_bars


def setup(entry=100.0, stop=95.0, target=116.0, confirmed=True):
    return {'entry': entry, 'stop': stop, 'target': target,
            'criteria': [{'code': 'TREND', 'pass': confirmed}]}


def test_positive_gate_never_grants_trade_execution():
    g = evaluate_research_gate(setup(), 'PASS', atr=2.0)
    assert g['status'] == 'PASS'
    assert g['trade_ready'] is False
    assert g['execution_validated'] is False
    assert g['modeled_net_reward_risk'] < g['gross_reward_risk']
    assert all(x['pass'] for x in g['checks'])


def test_unverified_liquidity_excludes_even_good_technical_setup():
    g = evaluate_research_gate(setup(), 'FAIL', atr=2.0)
    assert g['status'] == 'EXCLUDED'
    assert 'HISTORICAL_LIQUIDITY' in g['reason_codes']


def test_tight_stop_is_blocked_even_with_high_rr():
    g = evaluate_research_gate(setup(stop=99.5, target=120), 'PASS', atr=2.0)
    assert g['status'] == 'BLOCKED'
    assert 'STOP_DISTANCE_ATR_0_5_TO_4' in g['reason_codes']


def test_missing_structural_target_waits_not_hypothetical_2r():
    g = evaluate_research_gate(setup(target=None), 'PASS', atr=2.0)
    assert g['status'] == 'WAIT'
    assert g['modeled_net_reward_risk'] is None
    assert 'STRUCTURAL_TARGET' in g['reason_codes']


def test_fee_proxy_can_reject_marginal_gross_rr():
    # Gross = 2.01 R, but cost-aware net R:R is below 2.
    g = evaluate_research_gate(setup(target=110.05), 'PASS', atr=2.0)
    assert g['gross_reward_risk'] > 2
    assert g['modeled_net_reward_risk'] < 2
    assert g['status'] == 'WAIT'


def test_no_conformation_does_not_pass_gate():
    g = evaluate_research_gate(setup(confirmed=False), 'PASS', atr=2.0)
    assert g['status'] == 'WAIT'
    assert 'TECHNICAL_CONFIRMATION' in g['reason_codes']


def test_all_19_demo_instruments_expose_research_gate_without_ready_status():
    for ins in INSTRUMENTS:
        a = analyze(ins, demo_bars(ins))
        for s in a['strategies']:
            g = s['research_gate']
            assert g['status'] in ('PASS', 'WAIT', 'BLOCKED', 'EXCLUDED')
            assert g['trade_ready'] is False
            assert s['status'] != 'READY'
            assert s['forecast_probabilities'] is None
            assert g['modeled_net_reward_risk'] is None or isfinite(g['modeled_net_reward_risk'])


def test_gate_is_point_in_time_on_prefix_only():
    ins = INSTRUMENTS[0]
    bars = demo_bars(ins)
    prefix = bars[:-1]
    baseline = analyze(ins, prefix)
    # Mutating an OUT-OF-SAMPLE next candle must not affect an existing prefix signal.
    altered = bars[:-1] + [replace(bars[-1], high=bars[-1].high * 8)]
    after = analyze(ins, altered[:-1])
    assert baseline['strategies'] == after['strategies']
    assert baseline['features'] == after['features']


def test_gate_does_not_expose_probabilities_from_scores():
    ins = INSTRUMENTS[0]
    result = analyze(ins, demo_bars(ins))
    assert all('win_probability' not in s['research_gate'] for s in result['strategies'])
