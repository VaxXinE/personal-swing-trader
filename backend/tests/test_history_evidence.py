"""Evidence review is offline and does not certify vendor timestamps or execution."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json

import pytest

from app.domain import Candle, INSTRUMENTS
from app.history import HistoryError, HistoryStore, CorporateAction
from app.history_evidence import load_close_reference
from app.history_quality import audit_snapshot, load_session_calendar
from scripts.history_quality_audit import main as quality_cli


class Clock:
    def __init__(self):
        self.time = datetime(2026, 9, 1, tzinfo=timezone.utc)
    def __call__(self):
        return self.time


def store_and_snapshot(tmp_path):
    clock=Clock()
    ins=INSTRUMENTS[0]
    store=HistoryStore(tmp_path/'history.sqlite',clock=clock)
    first = date(2025,1,2)
    sessions=[]
    d=first
    while len(sessions)<230:
        if d.weekday()<5:
            sessions.append(d)
        d+=timedelta(days=1)
    candles=[Candle(f'{d}T20:00:00Z',100,105,95,101,200000) for d in sessions]
    store.ingest(ins,candles,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    snap=store.read(ins.instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    return ins,store,snap,clock


def reference_json(ins,snap,*,observed_at='2026-08-30T00:00:00Z'):
    return {'instrument_id':ins.instrument_id,'source':'SECOND_PROVIDER_FIXTURE',
            'price_basis':'SYNTHETIC','currency':ins.currency,
            'observed_at':observed_at,
            'candles':[{'session_date':r['session_date'],'close':str(r['candle']['close'])}
                       for r in snap['candles']]}


def test_reference_compare_without_false_provider_certification(tmp_path):
    ins,_,snap,_=store_and_snapshot(tmp_path)
    path=tmp_path/'external.json'
    path.write_text(json.dumps(reference_json(ins,snap)))
    ref=load_close_reference(path)
    report=audit_snapshot(ins,snap,reference=ref)
    assert report['status']=='STRUCTURAL_PASS'
    assert report['reference_comparison']['overlap_sessions']==230
    assert report['reference_comparison']['independent_source_verified'] is False
    assert report['source_evidence_sha256']==ref['sha256']
    assert len(report['evidence_sha256'])==64
    assert report['point_in_time_validated'] is False
    assert audit_snapshot(ins,snap,reference=ref)['evidence_sha256']==report['evidence_sha256']


def test_mismatching_close_blocks_and_changes_evidence_fingerprint(tmp_path):
    ins,_,snap,_=store_and_snapshot(tmp_path)
    path=tmp_path/'external.json'
    raw=reference_json(ins,snap)
    path.write_text(json.dumps(raw))
    base=audit_snapshot(ins,snap,reference=load_close_reference(path))
    raw['candles'][14]['close']='150.0'
    path.write_text(json.dumps(raw))
    report=audit_snapshot(ins,snap,reference=load_close_reference(path))
    assert report['status']=='BLOCKED'
    assert report['finding_counts']['INDEPENDENT_SOURCE_PRICE_CONFLICT']==1
    assert report['evidence_sha256']!=base['evidence_sha256']


def test_future_external_evidence_is_blocked_not_backdated(tmp_path):
    ins,_,snap,_=store_and_snapshot(tmp_path)
    path=tmp_path/'external.json'
    path.write_text(json.dumps(reference_json(ins,snap,observed_at='2026-09-02T00:00:00Z')))
    audit=audit_snapshot(ins,snap,reference=load_close_reference(path))
    assert audit['status']=='BLOCKED'
    assert 'REFERENCE_EVIDENCE_AFTER_SNAPSHOT' in audit['finding_counts']
    cal=tmp_path/'calendar.json'
    cal.write_text(json.dumps({'market':'US','source':'Test-only sessions',
        'observed_at':'2026-09-02T00:00:00Z',
        'coverage_start':snap['candles'][0]['session_date'],
        'coverage_end':snap['candles'][-1]['session_date'],
        'sessions':[r['session_date'] for r in snap['candles']]}))
    report=audit_snapshot(ins,snap,calendar=load_session_calendar(cal,'US'))
    assert report['status']=='BLOCKED'
    assert 'CALENDAR_EVIDENCE_AFTER_SNAPSHOT' in report['finding_counts']


@pytest.mark.parametrize('edit',[
    lambda x:x.update(source=''),
    lambda x:x.update(currency='IDR'),
    lambda x:x.update(price_basis='RAW_VERIFIED'),
    lambda x:x['candles'][1].update(session_date=x['candles'][0]['session_date']),
    lambda x:x['candles'][1].update(close='NaN'),
    lambda x:x['candles'][1].update(close='1e999'),
    lambda x:x['candles'][1].update(close='-1'),
    lambda x:x.update(candles=[]),
])
def test_invalid_or_incompatible_reference_fails_closed(tmp_path,edit):
    ins,_,snap,_=store_and_snapshot(tmp_path)
    raw=reference_json(ins,snap)
    edit(raw)
    path=tmp_path/'external.json'
    path.write_text(json.dumps(raw))
    if raw['currency']=='IDR':
        with pytest.raises(HistoryError,match='currency'):
            audit_snapshot(ins,snap,reference=load_close_reference(path))
    else:
        with pytest.raises(HistoryError):
            load_close_reference(path)


def test_cli_loads_reference_without_touching_network(tmp_path,capsys,monkeypatch):
    ins,store,snap,_=store_and_snapshot(tmp_path)
    path=tmp_path/'external.json'
    path.write_text(json.dumps(reference_json(ins,snap)))
    import app.providers as providers
    monkeypatch.setattr(providers,'load_bars',lambda *_a,**_k: pytest.fail('Network must stay off'))
    code=quality_cli(['--mode','demo','--db',str(store.path),'--instrument-id',ins.instrument_id,
                      '--reference',str(path),'--json'])
    report=json.loads(capsys.readouterr().out)
    assert code==0
    assert report['reference_comparison']['overlap_sessions']==230
    assert report['evidence_sha256']


def test_evidence_asof_action_revisions_do_not_change_old_snapshot(tmp_path):
    ins,store,snap,clock=store_and_snapshot(tmp_path)
    action=CorporateAction('SPLIT','2025-05-01','2',announced_at='2025-04-20T00:00:00Z')
    store.record_action(ins,action,source='YFINANCE_RESEARCH_RAW')
    old='2026-09-01T00:00:00Z'
    clock.time=datetime(2026,9,2,tzinfo=timezone.utc)
    store.record_action(ins,replace(action,value='3'),source='YFINANCE_RESEARCH_RAW')
    before=store.actions(ins.instrument_id,source='YFINANCE_RESEARCH_RAW',as_of=old)
    after=store.actions(ins.instrument_id,source='YFINANCE_RESEARCH_RAW')
    assert len(before)==len(after)==1
    assert before[0]['revision']==1 and after[0]['revision']==2
    assert before[0]['evidence']['value']=='2' and after[0]['evidence']['value']=='3'


def test_evidence_hash_does_not_change_with_clock_only(tmp_path):
    ins,store,snap,clock=store_and_snapshot(tmp_path)
    before=audit_snapshot(ins,snap)
    clock.time=datetime(2026,9,2,tzinfo=timezone.utc)
    later=store.read(ins.instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    after=audit_snapshot(ins,later)
    assert later['as_of_observation']!=snap['as_of_observation']
    assert before['evidence_sha256']==after['evidence_sha256']
