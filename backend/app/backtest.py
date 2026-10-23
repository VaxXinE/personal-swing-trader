"""Simple conservative historical replay lab. NOT validated or a trade recommendation."""
from __future__ import annotations
from .domain import Instrument,Candle,calculate_features,detect_strategy

def replay(ins:Instrument,bars:list[Candle],strategy:str='PULLBACK',horizon:int=10)->dict:
    if not 2<=horizon<=20:raise ValueError('horizon must be 2..20')
    trades=[]
    # Warmup required for strategy resistance and indicators. All calculations use <= signal bar.
    for i in range(210,len(bars)-horizon-1):
        prefix=bars[:i+1]
        features=calculate_features(prefix)
        setup=detect_strategy(ins,prefix,features,strategy)
        if setup['status']!='QUALIFIED' or setup['target'] is None:continue
        entry=setup['entry'];stop=setup['stop'];target=setup['target']
        if not entry>stop>0 or target<=entry:continue
        nextbar=bars[i+1]
        if nextbar.open>entry+.5*features['atr_14']:continue  # no chasing gaps
        if nextbar.open>=entry:fill=nextbar.open
        elif nextbar.high>=entry:fill=entry
        else:continue
        if fill>=target:continue
        outcome='TIMEOUT';exit_price=bars[i+horizon].close;exit_at=bars[i+horizon].at
        for bar in bars[i+1:i+horizon+1]:
            # stop wins when both barriers touched in same OHLC bar (conservative)
            if bar.low<=stop:
                outcome='STOP';exit_price=min(stop,bar.open);exit_at=bar.at;break
            if bar.high>=target:
                outcome='TARGET';exit_price=target;exit_at=bar.at;break
        # Research commission+slippage 0.1% per side, not broker fees
        net_r=(exit_price-fill-0.002*fill)/(fill-stop) if fill>stop else None
        if net_r is not None:
            trades.append({'signal_at':bars[i].at,'entry_at':nextbar.at,'exit_at':exit_at,
                           'entry':round(fill,5),'exit':round(exit_price,5),'outcome':outcome,'net_r':round(net_r,4)})
    expectancy=sum(t['net_r'] for t in trades)/len(trades) if trades else None
    return {'instrument_id':ins.instrument_id,'strategy':strategy,'horizon':horizon,
            'assumption':'EOD signal, next-bar entry, stop first on ambiguous OHLC, 0.1% fee/slippage per side; no delist data.',
            'trades':trades,'samples':len(trades),'net_expectancy_r':round(expectancy,4) if expectancy is not None else None,
            'status':'RESEARCH_ONLY','validated':False,
            'limitations':['Survivorship bias possible with current symbol registry','No exchange halt/corporate-action adjustment','Not out-of-sample']}
