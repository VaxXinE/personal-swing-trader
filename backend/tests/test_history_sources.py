"""LIVE adapter contract tests run with controlled responses; ZERO live provider requests."""
from datetime import date, datetime, timezone
from types import SimpleNamespace
import sys
import pandas as pd
import pytest
from app.domain import INSTRUMENTS, Candle
from app.history import HistoryError
from app.history_sources import fetch_historical_range, BINANCE_BASE
from app.providers import ProviderError


NOW=datetime(2025,2,15,tzinfo=timezone.utc)


def test_date_window_fails_closed_without_network():
    ins=INSTRUMENTS[0]
    with pytest.raises(HistoryError,match='oversized'):
        fetch_historical_range(ins,date(2012,1,1),date(2025,1,1),now=NOW)
    with pytest.raises(HistoryError,match='Future'):
        fetch_historical_range(ins,date(2025,1,1),date(2026,1,1),now=NOW)
    with pytest.raises(HistoryError,match='Invalid'):
        fetch_historical_range(ins,date(2025,1,2),date(2025,1,1),now=NOW)


def test_equities_respect_exchange_close_and_exclude_not_final(monkeypatch):
    rows=pd.DataFrame({'Open':[100.,103.], 'High':[104.,106.], 'Low':[99.,102.],
                       'Close':[102.,105.], 'Volume':[1_000_000.,2_000_000.]},
                      index=pd.DatetimeIndex(['2025-02-13','2025-02-14'],tz='America/New_York'))
    seen=[]
    def history(**kw):
        seen.append(kw)
        return rows
    monkeypatch.setitem(sys.modules,'yfinance',SimpleNamespace(Ticker=lambda symbol:SimpleNamespace(history=history)))
    bars,source=fetch_historical_range(INSTRUMENTS[0],date(2025,2,13),date(2025,2,14),now=NOW)
    assert source=='YFINANCE_RESEARCH_RAW' and len(bars)==2
    assert bars[0].at=='2025-02-13T21:00:00Z'
    assert seen[0]['auto_adjust'] is False
    assert seen[0]['end']=='2025-02-15'
    # Publication/finality guard still excludes the last bar at NY 4:15pm.
    early=datetime(2025,2,14,21,15,tzinfo=timezone.utc)
    subset,_=fetch_historical_range(INSTRUMENTS[0],date(2025,2,13),date(2025,2,14),now=early)
    assert len(subset)==1


class Response:
    def __init__(self,payload): self.payload=payload
    def raise_for_status(self): pass
    def json(self): return self.payload


class BinanceClient:
    calls=[]
    def __init__(self, *, timeout,follow_redirects,headers):
        assert follow_redirects is False
        assert timeout<=12
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def get(self,url,params):
        self.calls.append((url,params))
        assert url.startswith(BINANCE_BASE+'/api/v3/')
        if url.endswith('exchangeInfo'):
            return Response({'symbols':[{'symbol':'BTCUSDT','status':'TRADING','isSpotTradingAllowed':True}]})
        dt=datetime(2025,1,1,tzinfo=timezone.utc)
        opened=int(dt.timestamp()*1000)
        return Response([[opened,'100','105','95','102','200',opened+86400000-1,'210000']])


def test_crypto_fixed_origin_bounded_and_final_only():
    BinanceClient.calls=[]
    ins=next(x for x in INSTRUMENTS if x.market=='CRYPTO')
    bars,source=fetch_historical_range(ins,date(2025,1,1),date(2025,1,2),
                                       now=NOW,client_factory=BinanceClient)
    assert source=='BINANCE_SPOT_EOD'
    assert len(bars)==1 and bars[0].close==102
    assert len(BinanceClient.calls)==2
    assert all(url.startswith(BINANCE_BASE) for url,_ in BinanceClient.calls)


def test_crypto_untradable_symbol_rejected():
    class Forbidden(BinanceClient):
        def get(self,url,params):
            if url.endswith('exchangeInfo'):
                return Response({'symbols':[{'symbol':'BTCUSDT','status':'BREAK','isSpotTradingAllowed':False}]})
            return super().get(url,params)
    ins=next(x for x in INSTRUMENTS if x.market=='CRYPTO')
    with pytest.raises(ProviderError,match='Not a confirmed'):
        fetch_historical_range(ins,date(2025,1,1),date(2025,1,2),
                               now=NOW,client_factory=Forbidden)


def test_cli_live_date_capture_only_after_consent(tmp_path,monkeypatch):
    from scripts import history_ingest
    ins=INSTRUMENTS[0]
    monkeypatch.setattr(history_ingest,'get_instruments',lambda mode: (ins,))
    recorded=[]
    def fake_history(instrument,start,end):
        recorded.append((instrument.instrument_id,start,end))
        return [Candle('2025-01-01T21:00:00Z',100,105,95,102,2000)], 'YFINANCE_RESEARCH_RAW'
    monkeypatch.setattr(history_ingest,'fetch_historical_range',fake_history)
    db=tmp_path/'history.sqlite'
    assert history_ingest.main(['--mode','live','--allow-live','--limit','1',
        '--start-date','2025-01-01','--end-date','2025-01-02','--db',str(db)])==0
    assert len(recorded)==1 and db.exists()
