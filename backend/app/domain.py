"""Pure deterministic market-domain logic; no database, HTTP, FastAPI or LLM."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from hashlib import sha256
from math import isfinite
from statistics import median
from typing import Sequence

@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    symbol: str
    name: str
    market: str
    venue: str
    currency: str
    provider_symbol: str
    kind: str = 'EQUITY'

@dataclass(frozen=True)
class Candle:
    at: str                    # ISO UTC closing timestamp, FINAL ONLY
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float | None = None  # actual quote traded value if provider offers

@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    at: str
    source: str

INSTRUMENTS = (
    Instrument('US:NASDAQ:MSFT','MSFT','Microsoft','US','NASDAQ','USD','MSFT'),
    Instrument('US:NASDAQ:NVDA','NVDA','NVIDIA','US','NASDAQ','USD','NVDA'),
    Instrument('US:NASDAQ:AAPL','AAPL','Apple','US','NASDAQ','USD','AAPL'),
    Instrument('US:NASDAQ:GOOGL','GOOGL','Alphabet','US','NASDAQ','USD','GOOGL'),
    Instrument('US:NYSE:BRK-B','BRK.B','Berkshire Hathaway','US','NYSE','USD','BRK-B'),
    Instrument('US:NASDAQ:AMZN','AMZN','Amazon','US','NASDAQ','USD','AMZN'),
    Instrument('US:NASDAQ:META','META','Meta Platforms','US','NASDAQ','USD','META'),
    Instrument('US:NASDAQ:TSLA','TSLA','Tesla','US','NASDAQ','USD','TSLA'),
    Instrument('IDX:IDX:BBCA','BBCA','Bank Central Asia','IDX','IDX','IDR','BBCA.JK'),
    Instrument('IDX:IDX:BBRI','BBRI','Bank Rakyat Indonesia','IDX','IDX','IDR','BBRI.JK'),
    Instrument('IDX:IDX:BMRI','BMRI','Bank Mandiri','IDX','IDX','IDR','BMRI.JK'),
    Instrument('IDX:IDX:TLKM','TLKM','Telkom Indonesia','IDX','IDX','IDR','TLKM.JK'),
    Instrument('IDX:IDX:ASII','ASII','Astra International','IDX','IDX','IDR','ASII.JK'),
    Instrument('IDX:IDX:ICBP','ICBP','Indofood CBP','IDX','IDX','IDR','ICBP.JK'),
    Instrument('CRYPTO:BINANCE:BTCUSDT','BTCUSDT','Bitcoin / Tether','CRYPTO','BINANCE','USDT','BTCUSDT','SPOT'),
    Instrument('CRYPTO:BINANCE:ETHUSDT','ETHUSDT','Ethereum / Tether','CRYPTO','BINANCE','USDT','ETHUSDT','SPOT'),
    Instrument('CRYPTO:BINANCE:SOLUSDT','SOLUSDT','Solana / Tether','CRYPTO','BINANCE','USDT','SOLUSDT','SPOT'),
    Instrument('CRYPTO:BINANCE:BNBUSDT','BNBUSDT','BNB / Tether','CRYPTO','BINANCE','USDT','BNBUSDT','SPOT'),
    Instrument('CRYPTO:BINANCE:LINKUSDT','LINKUSDT','Chainlink / Tether','CRYPTO','BINANCE','USDT','LINKUSDT','SPOT'),
)

ADV_LIMIT = {'US':10_000_000., 'IDX':10_000_000_000., 'CRYPTO':10_000_000.}
SPREAD_LIMIT = {'US':0.30, 'IDX':0.50, 'CRYPTO':0.15}


def validate_candles(bars: Sequence[Candle]) -> None:
    """Fail closed, never silently clean or invent data."""
    previous = None
    for b in bars:
        stamp = datetime.fromisoformat(b.at.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise ValueError('bar timestamps must be UTC')
        if previous is not None and stamp <= previous:
            raise ValueError('candles not strictly chronological')
        previous = stamp
        numbers = (b.open, b.high, b.low, b.close, b.volume)
        if not all(isfinite(v) for v in numbers):
            raise ValueError('non-finite OHLCV')
        if min(b.open,b.high,b.low,b.close) <= 0 or b.volume < 0:
            raise ValueError('non-positive price or negative volume')
        if b.low > min(b.open,b.close) or b.high < max(b.open,b.close) or b.high < b.low:
            raise ValueError('OHLC structure invalid')
        if b.turnover is not None and (not isfinite(b.turnover) or b.turnover < 0):
            raise ValueError('invalid turnover')


def ema(values: list[float], period: int) -> list[float | None]:
    """Seed with SMA(period) for reproducible values and warmup."""
    result: list[float | None] = [None] * len(values)
    if len(values) < period: return result
    e = sum(values[:period]) / period
    result[period-1] = e
    alpha=2/(period+1)
    for i in range(period,len(values)):
        e=(values[i]-e)*alpha+e
        result[i]=e
    return result


def atr_wilder(bars: Sequence[Candle], period: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(bars)
    tr=[]
    for i,b in enumerate(bars):
        prior=bars[i-1].close if i else b.close
        tr.append(max(b.high-b.low, abs(b.high-prior), abs(b.low-prior)))
    if len(bars)<period:return result
    value=sum(tr[:period])/period
    result[period-1]=value
    for i in range(period,len(tr)):
        value=(value*(period-1)+tr[i])/period
        result[i]=value
    return result


def tick_size(market: str, price: float) -> float:
    """Research rounding only. IDX uses conservative sample bands, NOT official trading rules."""
    if market=='IDX':
        if price<200:return 1.
        if price<500:return 2.
        if price<2000:return 5.
        if price<5000:return 10.
        return 25.
    if market=='US': return 0.01
    return max(0.00000001, price*0.000001)  # Crypto requires exchangeInfo precision for actual orders


def snap_price(price: float, market: str, direction: str) -> float:
    # Research levels only; actual order rounding needs versioned market/exchange rules.
    d=Decimal(str(tick_size(market, price)))
    value=Decimal(str(price))/d
    rounding=ROUND_FLOOR if direction=='down' else 'ROUND_CEILING'
    return float(value.to_integral_value(rounding=rounding)*d)


def calculate_features(bars: Sequence[Candle]) -> dict:
    validate_candles(bars)
    if len(bars)<60: raise ValueError('insufficient bars: minimum 60 to inspect features')
    closes=[b.close for b in bars]
    fast=ema(closes,20); slow=ema(closes,50); atrs=atr_wilder(bars)
    i=len(bars)-1; atr=atrs[i]
    assert atr is not None and fast[i] is not None and slow[i] is not None
    previous_turnovers=[b.turnover if b.turnover is not None else b.close*b.volume for b in bars[i-20:i]]
    adv=sum(previous_turnovers)/20
    med=median(previous_turnovers)
    prev_vol=sum(b.volume for b in bars[i-20:i])/20
    rvol=bars[i].volume/prev_vol if prev_vol>0 else None
    prior_resistance=max(b.high for b in bars[i-20:i])  # EXCLUDES current candle
    ema50_before=slow[i-5]
    return {
        'close':closes[i], 'open':bars[i].open, 'high':bars[i].high,'low':bars[i].low,
        'ema_20':fast[i], 'ema_50':slow[i], 'ema50_5ago':ema50_before,
        'atr_14':atr, 'atr_pct':100*atr/closes[i], 'rvol_20':rvol,
        'roc_10':100*(closes[i]/closes[i-10]-1),'adv_20':adv,
        'median_turnover_20':med, 'resistance_20':prior_resistance,
        'base_width_20':max(b.high for b in bars[i-20:i])/min(b.low for b in bars[i-20:i])-1,
        'swing_low_6':min(b.low for b in bars[i-5:i+1]),
        'high_1ago':bars[i-1].high, 'close_1ago':bars[i-1].close,
        'as_of':bars[i].at,
    }


def liquidity(instrument: Instrument, bars: Sequence[Candle], f: dict, quote: Quote | None) -> dict:
    reasons=[]
    minimum=180 if instrument.market=='CRYPTO' else 200
    if len(bars)<minimum:reasons.append('NO_HISTORY')
    if f['adv_20']<ADV_LIMIT[instrument.market]:reasons.append('LOW_ADV')
    if f['median_turnover_20']<ADV_LIMIT[instrument.market]*.35:reasons.append('INCONSISTENT_TURNOVER')
    if instrument.market=='US' and f['close']<5:reasons.append('BELOW_MIN_PRICE')
    passed=not reasons
    spread=None
    if quote is not None and quote.ask>=quote.bid>0:
        spread=100*(quote.ask-quote.bid)/((quote.ask+quote.bid)/2)
    execution='UNKNOWN'
    execution_reasons=['NO_LIVE_QUOTE']
    if spread is not None:
        execution='PASS' if spread<=SPREAD_LIMIT[instrument.market] else 'FAIL'
        execution_reasons=[] if execution=='PASS' else ['WIDE_SPREAD']
    # A wide quoted spread is evidence of risk, not execution eligibility.
    # Even if spread passes, market status and executable rules remain unverified.
    return {'historical': 'PASS' if passed else 'FAIL','execution':'UNKNOWN',
            'reasons':reasons,'execution_reasons':execution_reasons + ['RULES_UNVERIFIED'],
            'adv20':round(f['adv_20'],2),'adv20_basis':'ACTUAL' if all(b.turnover is not None for b in bars[-21:-1]) else 'ESTIMATED_CLOSE_X_VOLUME',
            'median_turnover20':round(f['median_turnover_20'],2),'spread_pct':round(spread,4) if spread is not None else None}


def detect_strategy(ins: Instrument, bars: Sequence[Candle], f: dict, strat: str) -> dict:
    close=f['close']; atr=f['atr_14']; fast=f['ema_20']; slow=f['ema_50']
    trend=close>slow and fast>slow and (f['ema50_5ago'] is not None and slow>f['ema50_5ago'])
    criteria=[]; reason=[]
    if strat=='PULLBACK':
        d=(close-fast)/atr if atr>0 else None
        near=d is not None and -.5<=d<=.8
        structure=f['swing_low_6']>slow-atr
        confirmed=close>f['open'] and close>f['close_1ago']
        entry=snap_price(f['high']+tick_size(ins.market,f['high']),ins.market,'up')
        stop=snap_price(f['swing_low_6']-.25*atr,ins.market,'down')
        criteria=[('TREND',trend),('PULLBACK_ZONE',near),('HIGHER_LOW',structure),('CONFIRMATION',confirmed)]
        if not near:reason.append('PULLBACK_NOT_NEAR_SUPPORT')
        if not confirmed:reason.append('CONFIRMATION_PENDING')
        setup_pts=10*near+8*(d is not None and abs(d)<=.5)+7*structure+5*confirmed
        extended=False
    else:
        resistance=f['resistance_20']
        buffer=max(tick_size(ins.market,resistance),.1*atr)
        breakout=close>resistance+buffer
        volume=f['rvol_20'] is not None and f['rvol_20']>=1.5
        not_extended=close-resistance<=1.5*atr
        consolidation=f['base_width_20']<=.20
        entry=snap_price(max(close,f['high'])+tick_size(ins.market,f['high']),ins.market,'up')
        stop=snap_price(min(f['low'], resistance-.5*atr)-tick_size(ins.market,close),ins.market,'down')
        criteria=[('TREND',trend),('BREAKOUT_CONFIRMED',breakout),('RVOL_CONFIRMED',volume),('NOT_EXTENDED',not_extended)]
        if not breakout:reason.append('BREAKOUT_NOT_CONFIRMED')
        if not volume:reason.append('RVOL_LOW')
        if not not_extended:reason.append('EXTENDED')
        setup_pts=10*(f['base_width_20']<=.12)+8*consolidation+7*breakout+5*not_extended
        extended=not not_extended
    if not trend:reason.append('TREND_NOT_ALIGNED')
    if stop<=0 or stop>=entry:reason.append('INVALID_STOP')
    # Structural target: preceding 60 bars, excluding signal bar. Historical resistance
    # for breakout is usually BELOW entry; therefore hypothetical 2R MUST be non-ready.
    structural=[b.high for b in bars[-61:-1] if b.high>entry]
    structural_target=min(structural) if structural else None
    theoretical_rr=2.0 if entry>stop>0 else None
    target=snap_price(structural_target,ins.market,'down') if structural_target is not None else None
    if target is None or target<=entry:
        reason.append('TARGET_UNSUPPORTED')
        target=None
    rr=(target-entry)/(entry-stop) if target is not None and entry>stop>0 else None
    if rr is not None and rr<2:reason.append('RR_BELOW_MIN')
    trend_pts=7*(close>slow)+7*(fast>slow)+6*(f['ema50_5ago'] is not None and slow>f['ema50_5ago'])
    # relative strength missing; no default positive points; score remains interpretable
    rvol=f['rvol_20']; vol_pts=0 if rvol is None or rvol<1 else (3 if rvol<1.5 else (5 if rvol<2 else 7))
    location=0 if f['high']==f['low'] else (close-f['low'])/(f['high']-f['low'])
    momentum_pts=vol_pts+5*(location>.7)+3*(f['roc_10']>0)
    risk_pts=7*(stop>0 and stop<entry)+7*(target is not None)+6*(rr is not None and rr>=2)
    score=int(trend_pts+setup_pts+momentum_pts+risk_pts)
    # Market regime and independent relative strength unavailable: upper bound currently 85.
    status='WATCH' if any(ok for _,ok in criteria) else 'DISCOVERED'
    if all(ok for _,ok in criteria) and 'INVALID_STOP' not in reason and 'TARGET_UNSUPPORTED' not in reason and 'RR_BELOW_MIN' not in reason:
        status='QUALIFIED'  # execution gate applied later; NOT READY
    return {'strategy':strat,'score':score,'score_max':100,'score_status':'PARTIAL_CONTEXT',
            'score_breakdown':{'trend':int(trend_pts),'setup_structure':int(setup_pts),'momentum_volume':int(momentum_pts),'risk_geometry':int(risk_pts),'market_regime':0},
            'status':status,'criteria':[{'code':code,'pass':bool(ok)} for code,ok in criteria],
            'reason_codes':list(dict.fromkeys(reason)),
            'entry':round(entry,8),'stop':round(stop,8),'target':round(target,8) if target else None,
            'hypothetical_2r_target':round(entry+2*(entry-stop),8) if entry>stop>0 else None,
            'reward_risk':round(rr,2) if rr is not None else None,
            'entry_readiness':int(100*sum(ok for _,ok in criteria)/len(criteria)),
            'forecast_status':'NOT_VALIDATED','forecast_probabilities':None,'forecast_note':'Price forecasts withheld until OOS validation passes.',
            'research_baseline':True}



def evaluate_research_gate(setup: dict, historical_liquidity: str, atr: float) -> dict:
    """Conservative, pure EOD research screening; never certifies execution.

    This gate uses only already-computed signal-bar fields. 0.1% per side is
    an *illustrative* friction assumption, not an exchange/broker fee quote.
    Status PASS here means research criteria passed, NEVER trade-ready.
    """
    entry, stop, target = setup['entry'], setup['stop'], setup['target']
    valid_geometry = (all(isfinite(v) for v in (entry, stop, atr))
                      and entry > stop > 0 and atr > 0)
    stop_atr = (entry - stop) / atr if valid_geometry else None
    # Explicit, research-only stop range; too tight risks market noise, too far
    # creates excessive unit risk. These are NOT official exchange rules.
    stop_range_ok = stop_atr is not None and 0.5 <= stop_atr <= 4.0
    structural_target_ok = (valid_geometry and target is not None
                            and isfinite(target) and target > entry)
    gross_rr = ((target - entry) / (entry - stop)) if structural_target_ok else None
    # Fixed proxy assumes 0.1% on both entry and exit, including slippage.
    # Risk denominator includes the friction of a stop-out, too.
    net_rr = None
    if structural_target_ok:
        gain = target - entry - 0.001 * (entry + target)
        risk = entry - stop + 0.001 * (entry + stop)
        net_rr = gain / risk
    rr_ok = net_rr is not None and net_rr >= 2.0
    technique_ok = bool(setup['criteria']) and all(c['pass'] for c in setup['criteria'])
    liquid_ok = historical_liquidity == 'PASS'
    checks = [
        {'code': 'TECHNICAL_CONFIRMATION', 'pass': technique_ok},
        {'code': 'HISTORICAL_LIQUIDITY', 'pass': liquid_ok},
        {'code': 'VALID_ENTRY_STOP', 'pass': valid_geometry},
        {'code': 'STOP_DISTANCE_ATR_0_5_TO_4', 'pass': stop_range_ok},
        {'code': 'STRUCTURAL_TARGET', 'pass': structural_target_ok},
        {'code': 'MODELED_NET_RR_AT_LEAST_2', 'pass': rr_ok},
    ]
    if not liquid_ok:
        status = 'EXCLUDED'
    elif not valid_geometry or not stop_range_ok:
        status = 'BLOCKED'
    elif not all(c['pass'] for c in checks):
        status = 'WAIT'
    else:
        status = 'PASS'
    return {
        'status': status,
        'checks': checks,
        'reason_codes': [c['code'] for c in checks if not c['pass']],
        'stop_atr': round(stop_atr, 3) if stop_atr is not None else None,
        'gross_reward_risk': round(gross_rr, 3) if gross_rr is not None else None,
        'modeled_net_reward_risk': round(net_rr, 3) if net_rr is not None else None,
        'friction_assumption_pct_per_side': 0.1,
        'trade_ready': False,
        'execution_validated': False,
        'note': 'Research gate only. Broker fees, market rules, spread, session, and fills not verified.',
    }


def analyze(ins: Instrument, bars: Sequence[Candle], quote: Quote | None = None) -> dict:
    f=calculate_features(bars)
    liq=liquidity(ins,bars,f,quote)
    strategies=[detect_strategy(ins,bars,f,s) for s in ('PULLBACK','BREAKOUT')]
    for s in strategies:
        s['research_gate'] = evaluate_research_gate(s, liq['historical'], f['atr_14'])
        if liq['historical']!='PASS':
            s['status']='EXCLUDED';s['reason_codes']+=liq['reasons']
        elif s['status']=='QUALIFIED':
            s['status']='WATCH' # no verified exchange-rule / quote / session, regardless of high score
            s['reason_codes']+=['EXECUTION_NOT_VERIFIED']
        s['reason_codes']=list(dict.fromkeys(s['reason_codes']))
    best=sorted(strategies,key=lambda v:(-v['score'],v['strategy']))[0]
    return {'instrument_id':ins.instrument_id,'symbol':ins.symbol,'name':ins.name,'market':ins.market,
            'venue':ins.venue,'currency':ins.currency,'kind':ins.kind,
            'as_of':f['as_of'],'last_price':round(f['close'],8),'data_status':'EOD',
            'features':{k:(round(v,6) if isinstance(v,float) else v) for k,v in f.items()},
            'liquidity':liq,'strategies':strategies,'best_strategy':best,'source':None,
            'data_quality':'VALID','forecast_status':'NOT_VALIDATED'}


def position_size(capital: Decimal, entry: Decimal, stop: Decimal, risk_pct: Decimal,
                  market: str, max_position_pct: Decimal = Decimal('20'), fee_pct: Decimal = Decimal('0')) -> dict:
    if any(not x.is_finite() for x in (capital,entry,stop,risk_pct,max_position_pct,fee_pct)):
        raise ValueError('nonfinite number')
    if not (capital>0 and entry>stop>0 and Decimal('0')<risk_pct<=Decimal('2') and
            0<max_position_pct<=100 and Decimal('0')<=fee_pct<=Decimal('2')):
        raise ValueError('invalid capital, stop, risk or fee')
    if market not in ('US','IDX','CRYPTO'):raise ValueError('unsupported market')
    risk_budget=capital*risk_pct/100
    unit_cost=entry-stop + (entry+stop)*fee_pct/100
    max_by_risk=int((risk_budget/unit_cost).to_integral_value(rounding=ROUND_FLOOR))
    max_by_cash=int((capital/entry).to_integral_value(rounding=ROUND_FLOOR))
    max_by_exposure=int((capital*max_position_pct/100/entry).to_integral_value(rounding=ROUND_FLOOR))
    if market=='IDX':
        quantity=(min(max_by_risk,max_by_cash,max_by_exposure)//100)*100
        unit='shares (100/lot)'
    elif market=='US':
        quantity=min(max_by_risk,max_by_cash,max_by_exposure)
        unit='whole shares'
    else:
        # Decimal spot amount rounded to 6 dp for research. Actual stepSize per exchange is required.
        amount=min(risk_budget/unit_cost,capital/entry,capital*max_position_pct/100/entry)
        quantity=float(amount.quantize(Decimal('0.000001'),rounding=ROUND_FLOOR));unit='units (estimated precision)'
    q=Decimal(str(quantity))
    return {'quantity':str(quantity),'unit':unit,'position_value':str(q*entry),
            'risk_budget':str(risk_budget),'modeled_max_loss':str(q*unit_cost),
            'max_exposure_pct':str(max_position_pct),'risk_pct':str(risk_pct),
            'execution_verified':False,'warning':'Research-only. Fees approximated; gaps/slippage and exchange lot/tick filters may exceed planned risk.'}
