"""Offline contract tests for bounded exchange discovery and preserved snapshots."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import httpx
from app import universe, registry, service
from app.rules import ScreenerConfig
from app.storage import Store


class FakeResponse:
    def __init__(self, data, text=None, status=200):
        self.data=data
        self.text=text or ''
        self.status_code=status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('HTTP status',request=httpx.Request('GET','https://mock.example'),response=httpx.Response(self.status_code))
    def json(self):return self.data


class FakeClient:
    def __init__(self, responses): self.responses=responses;self.calls=[]
    def get(self,url):
        self.calls.append(url)
        value=self.responses.get(url)
        if isinstance(value,Exception):raise value
        if value is None:raise RuntimeError('Unexpected URL')
        return value


def nasdaq_files():
    a='Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\nAAA|AAA Corporation|Q|N|N|100|N|N\nETF1|Some ETF|Q|N|N|100|Y|N\nTEST|Test Company|S|Y|N|100|N|N\nWRNT|Company Warrants|S|N|N|100|N|N\nBAD|Bad Co|S|N|D|100|N|N\nFile Creation Time: 10232026|\n'
    b='ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\nNYSE1|NYSE Common|N|NYSE1|N|100|N|NYSE1\nPREF|Some Preferred Stock|N|PREF|N|100|N|PREF\nOTC1|Regional Exchange|Z|OTC1|N|100|N|OTC1\n'
    return a,b


def crypto_responses():
    symbols=[
        {'symbol':'BTCUSDT','baseAsset':'BTC','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True},
        {'symbol':'ETHUSDT','baseAsset':'ETH','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True},
        {'symbol':'XRPUSDT','baseAsset':'XRP','quoteAsset':'USDT','status':'HALT','isSpotTradingAllowed':True},
        {'symbol':'BTCUSDC','baseAsset':'BTC','quoteAsset':'USDC','status':'TRADING','isSpotTradingAllowed':True},
        {'symbol':'FOOUPUSDT','baseAsset':'FOOUP','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True},
        {'symbol':'USDCUSDT','baseAsset':'USDC','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True},
        {'symbol':'NOLIQUSDT','baseAsset':'NOLIQ','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True},
        {'symbol':'MARGINUSDT','baseAsset':'MARGIN','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':False},
    ]
    tick=[{'symbol':s['symbol'],'quoteVolume':n} for s,n in zip(symbols,['150000000','50000000','250000000','100000000','100000000','200000000','100000','300000000'])]
    return {universe.BINANCE+'/api/v3/exchangeInfo':FakeResponse({'symbols':symbols}),
            universe.BINANCE+'/api/v3/ticker/24hr':FakeResponse(tick)}


def test_us_parser_excludes_etf_tests_warrants_and_restricted():
    a,b=nasdaq_files()
    inputs={universe.DIRECTORIES['nasdaq']:FakeResponse(None,a),universe.DIRECTORIES['other']:FakeResponse(None,b)}
    found,count=universe.discover_us(FakeClient(inputs), 25, '2026-10')
    assert count==2
    assert {x.symbol for x in found}=={'AAA','NYSE1'}
    assert next(x for x in found if x.symbol=='NYSE1').venue=='NYSE'
    assert [x.symbol for x in universe.discover_us(FakeClient(inputs),1,'2026-10')[0]]==[x.symbol for x in universe.discover_us(FakeClient(inputs),1,'2026-10')[0]]


def test_us_parser_rejects_schema_changes():
    with pytest.raises(universe.DiscoveryError,match='format changed'):
        universe._rows_from_directory('Symbol|Whatever\nAAA|hello',other=False)


def test_crypto_screening_does_not_confuse_24h_with_adv20():
    found,count=universe.discover_crypto(FakeClient(crypto_responses()),10)
    assert count==3  # BTC, ETH and NOLIQ are listed as active spot candidates
    assert [x.symbol for x in found]==['BTCUSDT','ETHUSDT']


def test_crypto_fails_closed_without_ticker_volume():
    fake=crypto_responses()
    fake[universe.BINANCE+'/api/v3/ticker/24hr']=FakeResponse([])
    with pytest.raises(universe.DiscoveryError,match='no usable'):
        universe.discover_crypto(FakeClient(fake),20)


def test_idx_import_and_invalid_csv(tmp_path):
    path=tmp_path/'saham.csv'
    path.write_text('Kode;Nama Perusahaan;Papan Pencatatan\nBBCA;Bank Central Asia;Utama\nTEST;Test Company;Pemantauan Khusus\nBBRI;Bank Rakyat Indonesia;Pengembangan\nX123;Invalid;Utama\n',encoding='utf-8')
    found,count=universe.discover_idx_csv(path,20)
    assert count==2 and {x.provider_symbol for x in found}=={'BBCA.JK','BBRI.JK'}
    path.write_text('foo,bar\nx,y\n')
    with pytest.raises(universe.DiscoveryError,match='Kode'):
        universe.discover_idx_csv(path,20)


def test_partial_fail_preserves_previous_market(tmp_path):
    snap=tmp_path/'discovery.json'
    base={
      'version':1,'generated_at':'2026-01-01T00:00:00Z',
      'markets':{'US':{'selected':1,'synced_at':'2026-01-01T00:00:00Z'}},
      'instruments':[dict(vars(universe._instrument('US','OLD','Existing Corp','NASDAQ')))]}
    universe._atomic_write(snap,base)
    responses=crypto_responses()
    responses[universe.DIRECTORIES['nasdaq']]=httpx.ConnectError('test outage')
    result=universe.sync_discovery(['US','CRYPTO'],path=snap,client=FakeClient(responses))
    assert result['snapshot_updated'] and len(result['errors'])==1
    saved=universe._read_snapshot(snap)
    assert any(x['symbol']=='OLD' for x in saved['instruments'])
    assert any(x['symbol']=='BTCUSDT' for x in saved['instruments'])
    assert saved['markets']['US']['synced_at']=='2026-01-01T00:00:00Z'
    # If all fail, don't rewrite snapshot at all.
    old=snap.read_bytes()
    failed=universe.sync_discovery(['US'],path=snap,client=FakeClient(responses))
    assert failed['snapshot_updated'] is False and snap.read_bytes()==old


def test_manual_priority_and_demo_isolation(tmp_path,monkeypatch):
    import app.universe as m
    monkeypatch.setattr(m,'SNAPSHOT_PATH',tmp_path/'snapshot.json')
    baseline=tmp_path/'universe.json'
    baseline.write_text(json.dumps({'instruments':[dict(vars(universe._instrument('US','AAA','MANUAL','NASDAQ')))]}))
    monkeypatch.setattr(registry,'REGISTRY_FILE',baseline)
    universe._atomic_write(m.SNAPSHOT_PATH,{'version':1,'generated_at':'2026-10-23T00:00:00Z',
       'markets':{},'instruments':[dict(vars(universe._instrument('US','AAA','DISCOVERED','NASDAQ'))),
                                   dict(vars(universe._instrument('CRYPTO','BTCUSDT','BTC / USDT','BINANCE')))]})
    assert len(registry.get_instruments('demo'))==1
    result=registry.get_instruments('live')
    assert len(result)==2 and result[0].name=='MANUAL'


def test_api_reports_discovery_and_coverage(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main
    monkeypatch.setattr(main,'store',Store(tmp_path/'universe.db'))
    c=TestClient(main.app)
    r=c.get('/v1/universe/discovery')
    assert r.status_code==200 and 'discovered_candidate_count' in r.json()
    opp=c.get('/v1/opportunities').json()
    assert opp['coverage']['US']['attempted']>=1
    assert opp['coverage']['US']['analyzed']>=1
