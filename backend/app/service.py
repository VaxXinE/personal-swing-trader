"""Application workflow: load complete candles, evaluate, persist immutable snapshots."""
from __future__ import annotations
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from .domain import Instrument, analyze,validate_candles
from .registry import get_instruments
from .providers import load_bars,ProviderError
from .rules import ScreenerConfig,evaluate_rule
from .storage import Store,utcnow


def scan(store:Store,mode:str,config:ScreenerConfig)->dict:
    items=[];errors=[];excluded=[]
    for ins in get_instruments():
        if ins.market not in config.markets:continue
        try:
            bars,quote,source,data_status=load_bars(ins,mode)
            validate_candles(bars)
            if len(bars)<60:raise ProviderError('Less than 60 valid daily candles')
            analysis=analyze(ins,bars,quote)
            analysis['source']=source
            analysis['data_status']=data_status
            close_at=datetime.fromisoformat(bars[-1].at.replace('Z','+00:00'))
            age_hours=max(0,(datetime.now(timezone.utc)-close_at).total_seconds()/3600)
            analysis['candle_metadata']={
                'timestamp_basis': ('SYNTHETIC' if mode=='demo' else
                                    'PROVIDER_KLINE_CLOSE' if ins.market=='CRYPTO' else
                                    'DERIVED_REGULAR_SESSION_CLOSE'),
                'finality_basis': ('SIMULATED' if mode=='demo' else
                                   'EXCHANGE_REPORTED_CLOSE' if ins.market=='CRYPTO' else
                                   'CONSERVATIVE_AVAILABILITY_GUARD'),
                'last_session_date': (close_at.astimezone(ZoneInfo(
                    'America/New_York' if ins.market=='US' else
                    'Asia/Jakarta' if ins.market=='IDX' else 'UTC')).date().isoformat()),
                'age_hours_at_scan':round(age_hours,2),
                'validation_scope':'OHLC_STRUCTURAL_ONLY',
                'calendar_validated':False,
            }
            analysis['quote']={'bid':quote.bid,'ask':quote.ask,'at':quote.at,'source':quote.source} if quote else None
            analysis['chart']=[{'at':b.at,'open':b.open,'high':b.high,'low':b.low,'close':b.close} for b in bars[-80:]]
            if analysis['liquidity']['historical']=='FAIL':excluded.append({'instrument_id':ins.instrument_id,'symbol':ins.symbol,'market':ins.market,'reasons':analysis['liquidity']['reasons']})
            for s in analysis['strategies']:
                if config.strategy!='BOTH' and s['strategy']!=config.strategy:continue
                contextual={**analysis['features'],'setup_score':s['score'],'entry_readiness':s['entry_readiness'],'reward_risk':s['reward_risk']}
                rule_result=evaluate_rule(config.rules,contextual)
                if rule_result is not True:continue
                items.append({**{k:v for k,v in analysis.items() if k!='strategies'},'setup':s,
                              'filter_status':'MATCH','scan_generated_at':utcnow()})
        except (ValueError,ProviderError) as exc:
            errors.append({'instrument_id':ins.instrument_id,'error':str(exc)[:240]})
        except Exception as exc:
            errors.append({'instrument_id':ins.instrument_id,'error':f'Unexpected {type(exc).__name__} — see backend logs'})
    # Stable deterministic order within each market, never claim calibrated ranking across markets.
    items.sort(key=lambda r:(r['market'],-r['setup']['score'],r['symbol'],r['setup']['strategy']))
    result={'generated_at':utcnow(),'data_mode':mode,'config':config.model_dump(), 'count':len(items),
            'items':items,'exclusions':excluded,'errors':errors,
            'analysis_notice':'Research baseline; score is not probability. Execution eligibility unverified. No investment advice.',
            'forecast_status':'NOT_VALIDATED'}
    rid=store.new_run(config.model_dump(),mode,result)
    result['run_id']=rid
    return result


def get_latest(store:Store,mode:str)->dict:
    stored=store.latest_run()
    if stored is None or stored['mode']!=mode:
        return scan(store,mode,ScreenerConfig(name='All Opportunities',strategy='BOTH'))
    return {**stored['result'],'run_id':stored['id']}
