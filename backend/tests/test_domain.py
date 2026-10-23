from dataclasses import replace
from decimal import Decimal
import pytest
from app.domain import INSTRUMENTS,Candle,ema,atr_wilder,calculate_features,validate_candles,analyze,position_size
from app.providers import demo_bars


def test_demo_has_310_utc_final_candles():
    for ins in INSTRUMENTS:
        bars=demo_bars(ins)
        assert len(bars)==310
        validate_candles(bars)
        assert all(x.volume>=0 for x in bars)

def test_deterministic_demo_fixture():
    assert demo_bars(INSTRUMENTS[0])==demo_bars(INSTRUMENTS[0])

def test_ohlc_corruption_rejected():
    bars=demo_bars(INSTRUMENTS[0]);bars[-1]=replace(bars[-1],low=bars[-1].high+1)
    with pytest.raises(ValueError,match='OHLC'):validate_candles(bars)

def test_duplicate_bar_rejected():
    bars=demo_bars(INSTRUMENTS[0]);bars.append(bars[-1])
    with pytest.raises(ValueError,match='chronological'):validate_candles(bars)

def test_ema_warmup_and_atr():
    bars=demo_bars(INSTRUMENTS[0]);closes=[b.close for b in bars]
    assert ema(closes,20)[18] is None
    assert ema(closes,20)[19] is not None
    assert atr_wilder(bars)[13]>0

def test_resistance_excludes_current_bar():
    bars=demo_bars(INSTRUMENTS[0]);old=calculate_features(bars)
    altered=replace(bars[-1],high=bars[-1].high*50)
    bars[-1]=altered
    new=calculate_features(bars)
    assert new['resistance_20']==old['resistance_20']

def test_no_synthetic_ready_and_no_fake_probabilities():
    ins=INSTRUMENTS[0];a=analyze(ins,demo_bars(ins))
    assert a['forecast_status']=='NOT_VALIDATED'
    assert all(s['status']!='READY' for s in a['strategies'])
    assert all(s['forecast_probabilities'] is None for s in a['strategies'])
    assert all(sum(s['score_breakdown'].values())==s['score'] for s in a['strategies'])

def test_position_size_idx_respects_lot_and_exposure():
    out=position_size(Decimal('10000000'),Decimal('2000'),Decimal('1900'),Decimal('0.5'),'IDX')
    q=Decimal(out['quantity']); assert q%100==0
    assert Decimal(out['position_value'])<=Decimal('2000000')
    assert Decimal(out['modeled_max_loss'])<=Decimal('50000')

def test_position_size_rejects_negative_stop_and_zero_capital():
    with pytest.raises(ValueError):position_size(Decimal('1000000'),Decimal('90'),Decimal('100'),Decimal('.5'),'US')
    with pytest.raises(ValueError):position_size(Decimal('0'),Decimal('100'),Decimal('95'),Decimal('.5'),'US')

def test_crypto_qty_six_decimal_research():
    out=position_size(Decimal('10000'),Decimal('3000'),Decimal('2800'),Decimal('0.5'),'CRYPTO')
    assert Decimal(out['position_value'])<=Decimal('2000')
    assert out['execution_verified'] is False
