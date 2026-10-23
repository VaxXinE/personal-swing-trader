"""Bounded, allowlisted, EOD-only archival provider adapters.

No user-provided URLs, shell execution, dynamic code imports from input, or
silent demo fallback. LIVE requires explicit opt-in at the CLI boundary.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Callable

import httpx

from .domain import Candle, Instrument, validate_candles
from .history import MAX_BATCH_BARS, HistoryError
from .providers import ProviderError, equity_session_markers

BINANCE_BASE = 'https://data-api.binance.vision'
MAX_WINDOW_DAYS = 365 * 10
MAX_CRYPTO_PAGES = 4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _window(start: date, end: date, *, now: datetime) -> None:
    if isinstance(start, datetime) or isinstance(end, datetime) or not isinstance(start, date) or not isinstance(end, date):
        raise HistoryError('Historical window requires calendar dates')
    if not start <= end or (end-start).days > MAX_WINDOW_DAYS:
        raise HistoryError('Invalid or oversized historical date window')
    if end > now.date():
        raise HistoryError('Future date range not allowed')


def fetch_historical_range(ins: Instrument, start: date, end: date,
                           *, now: datetime | None = None,
                           client_factory: Callable[..., httpx.Client] = httpx.Client) -> tuple[list[Candle], str]:
    """Return provider-reported *final* candles, capped at 2500 rows.

    Source adjustment basis remains UNVERIFIED. No signal or trade is created.
    """
    reference = now or _utc_now()
    if reference.tzinfo is None or reference.utcoffset() != timezone.utc.utcoffset(reference):
        raise HistoryError('Reference time must be UTC')
    _window(start,end,now=reference)
    if ins.market in ('US','IDX'):
        return _equities(ins,start,end,reference)
    if ins.market == 'CRYPTO':
        return _crypto(ins,start,end,reference,client_factory)
    raise HistoryError('Unsupported historical market')


def _equities(ins: Instrument,start: date,end: date,now: datetime) -> tuple[list[Candle],str]:
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError as exc:
        raise ProviderError('LIVE equities require reviewed yfinance and pandas dependencies') from exc
    try:
        # end is exclusive in the provider request; our CLI end is inclusive.
        frame=yf.Ticker(ins.provider_symbol).history(start=start.isoformat(),
            end=(end+timedelta(days=1)).isoformat(),interval='1d',
            auto_adjust=False,actions=True)
        if frame.empty:
            raise ProviderError('No equity historical rows in requested window')
        output=[]
        for index,row in frame.iterrows():
            stamp=pd.Timestamp(index)
            if stamp.tzinfo is None:
                raise ProviderError('Vendor returned a timezone-naive market date')
            # The provider index identifies exchange session, NOT first publication time.
            session_date=stamp.date()
            if not start <= session_date <= end:
                continue
            close_at, ready_after = equity_session_markers(ins.market,session_date)
            if ready_after >= now:
                continue  # never ingest the currently incomplete daily session
            if any(pd.isna(row[k]) for k in ('Open','High','Low','Close','Volume')):
                raise ProviderError('Vendor returned missing OHLCV; no gap filling')
            output.append(Candle(close_at.isoformat().replace('+00:00','Z'),
                   float(row['Open']),float(row['High']),float(row['Low']),
                   float(row['Close']),float(row['Volume'])))
            if len(output)>MAX_BATCH_BARS:
                raise ProviderError('History exceeds 2500 bars; split date window')
        if not output:
            raise ProviderError('No FINAL equity candles in requested window')
        validate_candles(output)
        return output,'YFINANCE_RESEARCH_RAW'
    except ProviderError:
        raise
    except Exception as exc:
        raise ProviderError(f'Historical equity data unavailable: {type(exc).__name__}') from exc


def _crypto(ins:Instrument,start:date,end:date,now:datetime,
            client_factory:Callable[...,httpx.Client]) -> tuple[list[Candle],str]:
    day=timedelta(days=1)
    start_ms=int(datetime.combine(start,time.min,tzinfo=timezone.utc).timestamp()*1000)
    end_ms=int(datetime.combine(end+day,time.min,tzinfo=timezone.utc).timestamp()*1000)-1
    result=[]
    try:
        # Never follow redirects to arbitrary domains; hostname is fixed.
        with client_factory(timeout=12, follow_redirects=False,
                            headers={'User-Agent':'SwingHistoryResearch/1.0'}) as client:
            info=client.get(BINANCE_BASE+'/api/v3/exchangeInfo',params={'symbol':ins.provider_symbol})
            info.raise_for_status()
            symbols=info.json().get('symbols',[])
            if (not isinstance(symbols,list) or len(symbols)!=1 or
                symbols[0].get('symbol') != ins.provider_symbol or
                symbols[0].get('status')!='TRADING' or
                not symbols[0].get('isSpotTradingAllowed',False)):
                raise ProviderError('Not a confirmed Binance spot research symbol')
            cursor=start_ms
            for _page in range(MAX_CRYPTO_PAGES):
                response=client.get(BINANCE_BASE+'/api/v3/klines',params={
                    'symbol':ins.provider_symbol,'interval':'1d','startTime':cursor,
                    'endTime':end_ms,'limit':1000})
                response.raise_for_status()
                klines=response.json()
                if not isinstance(klines,list):
                    raise ProviderError('Unexpected provider kline shape')
                if not klines:
                    break
                max_open=cursor-1
                for k in klines:
                    opened=int(k[0]); closed=int(k[6])
                    if opened < cursor or opened > end_ms or closed < opened:
                        raise ProviderError('Nonmonotonic or out-of-range kline')
                    max_open=max(max_open,opened)
                    if datetime.fromtimestamp(closed/1000,tz=timezone.utc)>=now:
                        continue
                    if len(result)>=MAX_BATCH_BARS:
                        raise ProviderError('History exceeds 2500 bars; split date window')
                    result.append(Candle(datetime.fromtimestamp(closed/1000,tz=timezone.utc)
                        .isoformat().replace('+00:00','Z'),float(k[1]),float(k[2]),
                        float(k[3]),float(k[4]),float(k[5]),float(k[7])))
                if max_open<cursor:
                    raise ProviderError('Provider pagination made no progress')
                cursor=max_open+1
                if cursor>end_ms or len(klines)<1000:
                    break
            if not result:
                raise ProviderError('No FINAL Binance spot candles in requested window')
            validate_candles(result)
            return result,'BINANCE_SPOT_EOD'
    except ProviderError:
        raise
    except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError) as exc:
        raise ProviderError(f'Historical crypto data unavailable: {type(exc).__name__}') from exc
