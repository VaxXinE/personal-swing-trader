"""Data sources. Demo is explicitly synthetic; live source errors never trigger silent demo fallback."""
from __future__ import annotations
import math
import random
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
import httpx
from .domain import Instrument,Candle,Quote

class ProviderError(RuntimeError): pass


def demo_bars(ins:Instrument, count:int=310) -> list[Candle]:
    import hashlib
    seed=int.from_bytes(hashlib.sha256(ins.instrument_id.encode()).digest()[:8], 'big')
    rng=random.Random(seed)
    now=datetime.now(timezone.utc)
    days=[]; day=now.date()-timedelta(days=1)
    while len(days)<count:
        if ins.market=='CRYPTO' or day.weekday()<5: days.append(day)
        day-=timedelta(days=1)
    days.reverse()
    base={'US':135.,'IDX':4600.,'CRYPTO':950.}[ins.market]
    base*=.7+(seed%100)/180
    price=base
    bars=[]
    for i,d in enumerate(days):
        t=i/count
        movement=(.0007+.002*math.sin(i/19+seed%5)) + rng.gauss(0,.013 if ins.market!='CRYPTO' else .022)
        previous=price; price=max(.1,price*(1+movement))
        opening=previous*(1+rng.gauss(0,.003))
        high=max(opening,price)*(1+abs(rng.gauss(.006,.003)))
        low=min(opening,price)*(1-abs(rng.gauss(.006,.003)))
        if ins.market=='IDX':
            # Synthetic IDX prices use integer Rupiah, never fractional cents.
            opening,high,low,price=(round(v) for v in (opening,high,low,price))
            high=max(high,opening,price);low=max(1,min(low,opening,price))
        # provide enough liquidity for a subset but not all; keep synthetic values obvious
        quote_turnover=({'US':20_000_000.,'IDX':20_000_000_000.,'CRYPTO':20_000_000.}[ins.market]
                        *(.25 + (seed%9)/7)*(.75+rng.random()*.5))
        volume=quote_turnover/max(1,price)
        if ins.market=='CRYPTO': dt=datetime.combine(d,time(23,59,59),tzinfo=timezone.utc)
        elif ins.market=='IDX': dt=datetime.combine(d,time(16),tzinfo=ZoneInfo('Asia/Jakarta')).astimezone(timezone.utc)
        else: dt=datetime.combine(d,time(16),tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
        # Historical fixture may be run before a market's close on the same day; days end yesterday.
        bars.append(Candle(dt.isoformat().replace('+00:00','Z'),round(opening,6),round(high,6),round(low,6),round(price,6),round(volume,2),round(quote_turnover,2)))
    return bars


def fetch_yfinance(ins:Instrument) -> tuple[list[Candle],Quote|None]:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ProviderError('Install live extras: pip install -r backend/requirements-live.txt') from exc
    try:
        frame=yf.Ticker(ins.provider_symbol).history(period='2y',interval='1d',auto_adjust=False,actions=True)
        if frame.empty:raise ProviderError('Equity provider returned no data')
        import pandas as pd
        now=datetime.now(timezone.utc)
        market_zone=ZoneInfo('America/New_York' if ins.market=='US' else 'Asia/Jakarta')
        cutoff=time(17) if ins.market=='US' else time(16,30)
        output=[]
        for index,row in frame.iterrows():
            dt=pd.Timestamp(index).to_pydatetime().astimezone(market_zone)
            session_date=dt.date()
            close_dt=datetime.combine(session_date,cutoff,tzinfo=market_zone).astimezone(timezone.utc)
            if close_dt>=now: continue # protect against in-progress daily bars
            if any(pd.isna(row[x]) for x in ('Open','High','Low','Close','Volume')):continue
            # Reinvestment-adjusted bars are NOT used as raw execution prices.
            # Historical splits may require adjustment during a production-quality backtest.
            output.append(Candle(close_dt.isoformat().replace('+00:00','Z'),float(row['Open']),float(row['High']),float(row['Low']),float(row['Close']),float(row['Volume'])))
        if not output:raise ProviderError('No FINAL daily equity candles')
        return output,None  # yfinance historical alone does not validate live bid/ask
    except ProviderError:raise
    except Exception as exc:raise ProviderError(f'Equity data unavailable: {type(exc).__name__}') from exc


def fetch_binance(ins:Instrument) -> tuple[list[Candle],Quote|None]:
    base='https://data-api.binance.vision'
    try:
        with httpx.Client(timeout=12,headers={'User-Agent':'PersonalSwingIntelligence/0.1'}) as client:
            info=client.get(base+'/api/v3/exchangeInfo',params={'symbol':ins.provider_symbol})
            info.raise_for_status(); symbols=info.json().get('symbols',[])
            if not symbols or symbols[0].get('status')!='TRADING' or not symbols[0].get('isSpotTradingAllowed',False):
                raise ProviderError('Crypto pair not spot-tradable on selected source')
            response=client.get(base+'/api/v3/klines',params={'symbol':ins.provider_symbol,'interval':'1d','limit':350})
            response.raise_for_status()
            now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
            bars=[]
            for k in response.json():
                if int(k[6])>=now_ms:continue
                closed=datetime.fromtimestamp(int(k[6])/1000,tz=timezone.utc).isoformat().replace('+00:00','Z')
                bars.append(Candle(closed,float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5]),float(k[7])))
            book=client.get(base+'/api/v3/ticker/bookTicker',params={'symbol':ins.provider_symbol})
            book.raise_for_status(); j=book.json()
            quote=Quote(float(j['bidPrice']),float(j['askPrice']),datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'binance_bookTicker')
            return bars,quote
    except ProviderError:raise
    except Exception as exc:raise ProviderError(f'Crypto provider unavailable: {type(exc).__name__}') from exc


def load_bars(ins:Instrument,mode:str) -> tuple[list[Candle],Quote|None,str,str]:
    if mode=='demo':return demo_bars(ins),None,'SYNTHETIC_FIXTURE','DEMO'
    if ins.market=='CRYPTO':
        bars,quote=fetch_binance(ins)
        return bars,quote,'BINANCE_SPOT_EOD','EOD'
    bars,quote=fetch_yfinance(ins)
    return bars,quote,'YFINANCE_RESEARCH_RAW','EOD'
