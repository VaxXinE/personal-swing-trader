"""Historical Data Engine offline acceptance and adverse-input tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.domain import Candle, INSTRUMENTS
from app.history import HistoryStore, HistoryError, CorporateAction
from app.providers import demo_bars
from app import history_api
import app.main as main


class Clock:
    def __init__(self, at): self.at = at
    def __call__(self): return self.at


def make_bars(n=3):
    return [Candle((datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)).isoformat().replace('+00:00','Z'),
                   100+i, 105+i, 95+i, 102+i, 2000000.0) for i in range(n)]


def make_store(tmp_path):
    clock=Clock(datetime(2025, 2, 1, tzinfo=timezone.utc))
    return HistoryStore(tmp_path/'history.sqlite', clock=clock), clock


def test_append_idempotency_revision_and_as_of_snapshot(tmp_path):
    store,clock=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    bars=make_bars()
    first=store.ingest(ins,bars,source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    assert (first['inserted'],first['unchanged'],first['corrected'])==(3,0,0)
    again=store.ingest(ins,bars,source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    assert (again['inserted'],again['unchanged'],again['corrected'])==(0,3,0)
    clock.at=datetime(2025, 2, 2, tzinfo=timezone.utc)
    changed=bars[:-1]+[replace(bars[-1], close=bars[-1].close+1)]
    update=store.ingest(ins,changed,source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    assert (update['inserted'],update['unchanged'],update['corrected'])==(1,2,1)
    source='YFINANCE_RESEARCH_RAW'; basis='VENDOR_UNVERIFIED'
    old=store.read(ins.instrument_id,source=source,price_basis=basis,as_of='2025-02-01T12:00:00Z')
    new=store.read(ins.instrument_id,source=source,price_basis=basis)
    assert old['candles'][-1]['candle']['close']==bars[-1].close
    assert new['candles'][-1]['candle']['close']==changed[-1].close
    assert old['candles'][-1]['revision']==1 and new['candles'][-1]['revision']==2
    assert len(store.batches())==3
    assert new['point_in_time_validated'] is False
    assert 'BACKFILLED_FIRST_OBSERVED_NOW' in new['quality_flags']


def test_rejects_spoofed_price_basis_and_provider_mapping(tmp_path):
    store,_=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    with pytest.raises(HistoryError,match='self-certified'):
        store.ingest(ins, make_bars(),source='YFINANCE_RESEARCH_RAW',price_basis='RAW_VERIFIED')
    with pytest.raises(HistoryError,match='Synthetic'):
        store.ingest(ins, make_bars(),source='SYNTHETIC_FIXTURE',price_basis='VENDOR_UNVERIFIED')
    with pytest.raises(HistoryError,match='provider'):
        store.ingest(ins, make_bars(),source='BINANCE_SPOT_EOD',price_basis='VENDOR_UNVERIFIED')
    with pytest.raises(HistoryError,match='Source'):
        store.ingest(ins, make_bars(),source='EVIL_SCRIPT',price_basis='VENDOR_UNVERIFIED')


def test_rejects_invalid_ohlc_duplicate_dates_future_and_out_of_order(tmp_path):
    store,_=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    bars=make_bars()
    with pytest.raises(HistoryError,match='OHLC'):
        store.ingest(ins, bars[:1]+[replace(bars[1], high=1)]+bars[2:],source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    with pytest.raises(HistoryError,match='Duplicate market session'):
        store.ingest(ins, [bars[0],replace(bars[0],at='2025-01-01T01:00:00Z')],source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    with pytest.raises(HistoryError,match='chronological'):
        store.ingest(ins, list(reversed(bars)),source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    with pytest.raises(HistoryError,match='Unfinished'):
        store.ingest(ins, [replace(bars[0],at='2027-01-01T00:00:00Z')],source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    assert store.batches()==[]


def test_suspected_split_is_flagged_not_silently_adjusted(tmp_path):
    store,_=make_store(tmp_path)
    bars=make_bars(2)
    # Valid synthetic 50% gap, as if split, not automatically repaired.
    second=replace(bars[1],open=50,high=55,low=45,close=51)
    store.ingest(INSTRUMENTS[0],[bars[0],second],source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    snap=store.read(INSTRUMENTS[0].instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    assert 'SPLIT_OR_OUTLIER_SUSPECTED' in snap['quality_flags']
    assert snap['candles'][1]['candle']['close']==51
    assert snap['corporate_actions_verified'] is False


def test_corporate_action_evidence_is_immutable_and_never_changes_prices(tmp_path):
    store,clock=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    store.ingest(ins,make_bars(),source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    event=CorporateAction('SPLIT','2025-01-20','2',announced_at='2025-01-18T00:00:00Z')
    assert store.record_action(ins,event,source='YFINANCE_RESEARCH_RAW')['revision']==1
    assert store.record_action(ins,event,source='YFINANCE_RESEARCH_RAW')['status']=='UNCHANGED'
    clock.at=datetime(2025,2,2,tzinfo=timezone.utc)
    assert store.record_action(ins,replace(event,value='3'),source='YFINANCE_RESEARCH_RAW')['revision']==2
    assert len(store.actions(ins.instrument_id,source='YFINANCE_RESEARCH_RAW'))==2
    assert len(store.actions(ins.instrument_id,source='YFINANCE_RESEARCH_RAW',as_of='2025-02-01T01:00:00Z'))==1
    assert store.read(ins.instrument_id,source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')['candles'][0]['candle']['close']==102


def test_archive_is_atomic_and_metadata_is_bounded(tmp_path):
    store,_=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    with pytest.raises(HistoryError,match='Secret'):
        store.ingest(ins,make_bars(),source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC',metadata={'api_key':'secret'})
    assert not store.batches()
    with pytest.raises(HistoryError,match='Invalid read limit'):
        store.read(ins.instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC',limit=5000000)


def test_api_read_only_with_same_guard_and_no_external_calls(tmp_path,monkeypatch):
    store,_=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    store.ingest(ins,make_bars(),source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    monkeypatch.setattr(history_api,'store',store)
    client=TestClient(main.app)
    base='/v1/history/observations/'+ins.instrument_id
    params={'source':'SYNTHETIC_FIXTURE','price_basis':'SYNTHETIC'}
    ok=client.get(base,params=params)
    assert ok.status_code==200 and ok.json()['rows']==3
    assert client.get('/v1/history/batches').json()['items'][0]['received']==3
    assert client.get(base,params={'source':'MALWARE','price_basis':'RAW_VERIFIED'}).status_code==422
    assert client.post('/v1/history/batches',json={}).status_code==405
    assert client.get('/v1/history/actions/'+ins.instrument_id,params={'source':'YFINANCE_RESEARCH_RAW'}).json()['adjustment_applied'] is False


def test_demo_fixture_captures_without_provider_or_process(tmp_path, monkeypatch):
    from scripts import history_ingest
    monkeypatch.setattr(history_ingest, 'get_instruments', lambda mode: INSTRUMENTS)
    run = history_ingest.main
    archive=tmp_path/'manual.sqlite'
    assert run(['--mode','demo','--limit','1','--db',str(archive)])==0
    store=HistoryStore(archive)
    snap=store.read(INSTRUMENTS[0].instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    assert snap['rows']==310
    assert snap['point_in_time_validated'] is False


def test_live_never_runs_without_explicit_opt_in(tmp_path):
    from scripts.history_ingest import main as run
    with pytest.raises(SystemExit):
        run(['--mode','live','--limit','1','--db',str(tmp_path/'no.sqlite')])
    assert not (tmp_path/'no.sqlite').exists()


def test_archive_mutation_is_detected_when_reading(tmp_path):
    store,_=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    store.ingest(ins,make_bars(),source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE history_candles SET payload_json='{}' WHERE revision=1")
    with pytest.raises(HistoryError,match='checksum mismatch'):
        store.read(ins.instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')


def test_conflicting_market_close_marker_is_rejected(tmp_path):
    store,_=make_store(tmp_path)
    ins=INSTRUMENTS[0]
    bars=make_bars()
    store.ingest(ins,bars,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    # One canonical US session, two different provider close timestamps.
    altered=replace(bars[0],at='2025-01-01T01:00:00Z')
    with pytest.raises(HistoryError,match='Conflicting close marker'):
        store.ingest(ins,[altered],source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')


def test_api_enforces_existing_bearer_guard(tmp_path, monkeypatch):
    from types import SimpleNamespace
    store,_=make_store(tmp_path)
    monkeypatch.setattr(history_api,'store',store)
    monkeypatch.setattr(main,'settings',SimpleNamespace(api_token='a'*40))
    c=TestClient(main.app)
    assert c.get('/v1/history/batches').status_code==401
    assert c.get('/v1/history/batches',headers={'Authorization':'Bearer '+'a'*40}).status_code==200
