from fastapi.testclient import TestClient
import app.main as main
from app.storage import Store
from app.rules import ScreenerConfig
from app.service import scan
from app.domain import INSTRUMENTS
from app.providers import demo_bars
from app.backtest import replay


def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'store',Store(tmp_path/'app.db'))
    return TestClient(main.app)

def test_http_home_meta_and_scan(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    assert c.get('/').status_code==200
    assert 'SWING' in c.get('/').text
    assert c.get('/health/live').json()['status']=='ok'
    assert c.get('/v1/meta').json()['order_execution']=='DISABLED'
    r=c.get('/v1/opportunities')
    assert r.status_code==200 and r.json()['total']>0
    assert r.json()['mode']=='demo'
    assert len(r.json()['errors'])==0
    assert all(x['data_status']=='DEMO' for x in r.json()['items'])

def test_custom_rule_save_version_and_run(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    cfg={'name':'Research Filter','strategy':'PULLBACK','markets':['US','IDX'],
         'rules':{'op':'AND','children':[{'field':'close','operator':'GT_FIELD','value':'ema_20'}]}}
    assert c.post('/v1/screeners/validate',json=cfg).status_code==200
    a=c.post('/v1/screeners',json=cfg).json();b=c.post('/v1/screeners',json=cfg).json()
    assert a['version']==1 and b['version']==2
    run=c.post('/v1/screeners/runs',json=cfg).json()
    assert run['data_mode']=='demo'
    original=c.get('/v1/screeners/runs/'+run['run_id']).json()
    assert original['result']['items']==run['items']
    if run['items']:
        sid=run['items'][0]['signal_id']
        snap=c.get('/v1/signals/'+sid).json()
        assert snap['snapshot']['instrument_id']==run['items'][0]['instrument_id']

def test_rule_errors_and_auth(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    assert c.post('/v1/screeners/validate',json={'rules':{'field':'close','operator':'EVAL','value':10}}).status_code==422
    class AuthSettings:
        api_token='x'*40
        data_mode='demo'
    monkeypatch.setattr(main,'settings',AuthSettings())
    assert c.get('/v1/meta').status_code==401
    assert c.get('/v1/meta',headers={'Authorization':'Bearer '+'x'*40}).status_code==200

def test_watch_journal_risk(tmp_path,monkeypatch):
    c=client(tmp_path,monkeypatch)
    id='IDX:IDX:BBCA'
    assert c.post('/v1/watchlist',json={'instrument_id':id}).status_code==200
    assert c.get('/v1/watchlist').json()['items'][0]['instrument_id']==id
    assert c.delete('/v1/watchlist/'+id).status_code==200
    bad=c.post('/v1/journal/trades',json={'instrument_id':id,'mode':'PAPER','side':'SHORT','entry':2000,'quantity':100})
    assert bad.status_code==422
    r=c.post('/v1/journal/trades',json={'instrument_id':id,'mode':'PAPER','side':'LONG','entry':2000,'exit':2100,'quantity':100,'fees':100})
    assert r.status_code==200
    assert r.json()['payload']['realized_pnl']=='9900'
    s=c.post('/v1/risk/size',json={'capital':'10000000','entry':'2000','stop':'1900','market':'IDX'})
    assert s.status_code==200 and s.json()['execution_verified']==False
    assert c.get('/v1/forecast/'+id).json()['probabilities'] is None

def test_backtest_research_only():
    ins=INSTRUMENTS[0]
    r=replay(ins,demo_bars(ins),strategy='BREAKOUT')
    assert r['validated'] is False
    assert r['status']=='RESEARCH_ONLY'
