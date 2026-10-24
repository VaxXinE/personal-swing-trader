"""Quality gate contracts: deterministic, no provider/network calls or calendar fiction."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone, date
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.domain import INSTRUMENTS, Candle
from app.history import HistoryStore, HistoryError
from app.history_quality import audit_snapshot, load_session_calendar
from app.archive_backtest import replay_from_archive
from app import history_api
import app.main as main


class Clock:
    def __init__(self):
        self.at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    def __call__(self):
        return self.at


def equities(n=230):
    days = []
    current = date(2025, 1, 2)
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return [Candle(datetime(d.year,d.month,d.day,20,tzinfo=timezone.utc).isoformat().replace('+00:00','Z'),
                   100.,104.,97.,101.,500_000.) for d in days]


def archive(tmp_path, market='US', *, bars=None):
    clock = Clock()
    ins = next(i for i in INSTRUMENTS if i.market == market)
    store = HistoryStore(tmp_path/'history.sqlite', clock=clock)
    selected = bars or equities()
    store.ingest(ins,selected,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    return store, ins, clock


def snapshot(store, ins):
    return store.read(ins.instrument_id,source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')


def write_calendar(path, days, **kw):
    data = dict(market='US', source='Manual US holiday review (unverified)',
                observed_at='2026-09-01T00:00:00Z', coverage_start=min(days).isoformat(),
                coverage_end=max(days).isoformat(), sessions=[x.isoformat() for x in days])
    data.update(kw)
    path.write_text(json.dumps(data),encoding='utf-8')


def test_demo_structural_pass_is_not_market_calendar_certification(tmp_path):
    store,ins,_=archive(tmp_path)
    result=audit_snapshot(ins,snapshot(store,ins))
    assert result['status']=='STRUCTURAL_PASS'
    assert result['calendar_coverage']=='NOT_PROVIDED'
    assert result['calendar_validated'] is False
    assert result['point_in_time_validated'] is False
    assert result['execution_verified'] is False
    assert result['finding_counts']=={}


def test_calendar_marks_missing_equity_session_without_inventing_holidays(tmp_path):
    complete = equities()
    store,ins,_=archive(tmp_path,bars=complete[:15]+complete[16:])
    snap=snapshot(store,ins)
    dates=[date.fromisoformat(x['session_date']) for x in snap['candles']]
    extra=date.fromisoformat(complete[15].at[:10])
    # Insert a fictional open weekday explicitly; it becomes a SOURCE discrepancy, not proof.
    p=tmp_path/'calendar.json'
    write_calendar(p,sorted(set(dates+[extra])))
    source=load_session_calendar(p,'US')
    result=audit_snapshot(ins,snap,calendar=source)
    assert result['calendar_coverage']=='PROVIDED_UNVERIFIED'
    assert result['calendar_validated'] is False
    assert result['finding_counts']['MISSING_DECLARED_SESSION']>=1
    assert result['status']=='BLOCKED'


def test_calendar_validation_rejects_duplicate_weekend_oversize_and_wrong_market(tmp_path):
    p=tmp_path/'calendar.json'
    dates=[date(2025,1,2),date(2025,1,3)]
    write_calendar(p, dates, sessions=['2025-01-02','2025-01-02'])
    with pytest.raises(HistoryError,match='sorted, unique'):
        load_session_calendar(p,'US')
    write_calendar(p,dates,coverage_end='2025-01-04',sessions=['2025-01-02','2025-01-04'])
    with pytest.raises(HistoryError,match='Weekend'):
        load_session_calendar(p,'US')
    write_calendar(p,dates,market='IDX')
    with pytest.raises(HistoryError,match='schema or market'):
        load_session_calendar(p,'US')
    p.write_bytes(b'a'*(512*1024+1))
    with pytest.raises(HistoryError,match='512 KiB'):
        load_session_calendar(p,'US')


def test_detect_tampered_session_metadata_in_replay_even_when_payload_hash_matches(tmp_path):
    store,ins,_=archive(tmp_path)
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE history_candles SET session_date='2025-01-06' WHERE bar_at=(SELECT MIN(bar_at) FROM history_candles)")
    result=audit_snapshot(ins,snapshot(store,ins))
    assert result['status']=='BLOCKED' and 'SESSION_DATE_MISMATCH' in result['finding_counts']
    with pytest.raises(HistoryError,match='SESSION_DATE_MISMATCH'):
        replay_from_archive(store,ins,mode='demo',source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')


def test_detect_equity_weekend_when_session_dates_consistent(tmp_path):
    bars=equities(230)
    weekend=date(2025,1,4)
    saturday=Candle('2025-01-04T20:00:00Z',100.,104.,97.,101.,100.)
    bars=sorted([*bars,saturday],key=lambda b:b.at)
    store,ins,_=archive(tmp_path,bars=bars)
    report=audit_snapshot(ins,snapshot(store,ins))
    assert report['status']=='BLOCKED'
    assert 'WEEKEND_EQUITY_SESSION' in report['finding_counts']


def test_crypto_daily_missing_and_close_marker(tmp_path):
    dates=[date(2025,1,1)+timedelta(days=i) for i in range(231) if i != 6]
    bars=[Candle(f'{d.isoformat()}T23:59:59Z',100,104,97,101,1_000) for d in dates]
    store,ins,_=archive(tmp_path,'CRYPTO',bars=bars)
    report=audit_snapshot(ins,snapshot(store,ins))
    assert report['status']=='BLOCKED'
    assert 'MISSING_CRYPTO_DAILY_CANDLE' in report['finding_counts']


def test_extreme_equity_move_stays_blocked_even_with_unverified_split_evidence(tmp_path):
    bars=equities(230)
    bars[200]=replace(bars[200],open=50,low=45,high=55,close=51)
    store,ins,_=archive(tmp_path,bars=bars)
    snap=snapshot(store,ins)
    suspect=audit_snapshot(ins,snap)
    assert 'SPLIT_OR_OUTLIER_SUSPECTED' in suspect['finding_counts']
    split_on=snap['candles'][200]['session_date']
    evidence=[{'evidence':{'action_type':'SPLIT','effective_on':split_on,'value':'2'}}]
    result=audit_snapshot(ins,snap,actions=evidence)
    assert result['split_evidence_matches']==1
    assert result['status']=='BLOCKED'
    assert 'SPLIT_EVIDENCE_UNVERIFIED' in result['finding_counts']


def test_cross_source_mismatch_rejects_currency_basis_and_flags_price_conflict(tmp_path):
    store,ins,_=archive(tmp_path)
    snap=snapshot(store,ins)
    reference={**snap, 'source':'INDEPENDENT_FIXTURE', 'currency':'USD'}
    reference['candles']=[{**x,'candle':{**x['candle']}} for x in snap['candles']]
    reference['candles'][5]['candle']['close']*=1.08
    report=audit_snapshot(ins,snap,reference=reference)
    assert report['status']=='BLOCKED'
    assert report['finding_counts']['INDEPENDENT_SOURCE_PRICE_CONFLICT']==1
    with pytest.raises(HistoryError,match='Reference currency mismatch'):
        audit_snapshot(ins,snap,reference={**reference,'currency':'IDR'})
    with pytest.raises(HistoryError,match='different source'):
        audit_snapshot(ins,snap,reference={**reference,'source':snap['source']})
    with pytest.raises(HistoryError,match='different source'):
        audit_snapshot(ins,snap,reference={**reference,'price_basis':'VENDOR_UNVERIFIED'})


def test_live_research_with_no_calendar_remains_uncertified(tmp_path):
    ins=next(i for i in INSTRUMENTS if i.market=='US')
    store=HistoryStore(tmp_path/'live.sqlite',clock=Clock())
    store.ingest(ins,equities(),source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    snap=store.read(ins.instrument_id,source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    result=audit_snapshot(ins,snap)
    assert result['status']=='STRUCTURAL_PASS'
    assert not any(result[key] for key in ('calendar_validated','point_in_time_validated','execution_verified','corporate_actions_verified'))


def test_api_quality_endpoint_is_private_and_provider_free(tmp_path,monkeypatch):
    store,ins,_=archive(tmp_path)
    monkeypatch.setattr(history_api,'store',store)
    monkeypatch.setattr(main,'load_bars',lambda *_a,**_k: pytest.fail('LIVE provider unexpectedly called'))
    client=TestClient(main.app)
    url='/v1/history/quality/'+ins.instrument_id
    res=client.get(url,params={'source':'SYNTHETIC_FIXTURE','price_basis':'SYNTHETIC'})
    assert res.status_code==200,res.text
    assert res.json()['quality']['status']=='STRUCTURAL_PASS'
    assert res.json()['quality']['calendar_validated'] is False
    assert client.get(url,params={'source':'YFINANCE_RESEARCH_RAW','price_basis':'SYNTHETIC'}).status_code==422
    assert client.post(url,json={}).status_code==405


def test_cli_quality_audit_is_offline(tmp_path,capsys):
    from scripts.history_quality_audit import main as cli
    store,ins,_=archive(tmp_path)
    status=cli(['--mode','demo','--db',str(store.path),'--instrument-id',ins.instrument_id,'--json'])
    assert status==0
    report=json.loads(capsys.readouterr().out)
    assert report['status']=='STRUCTURAL_PASS'
    assert report['point_in_time_validated'] is False


def idx_market_bars(*, missing=frozenset(), add_holiday=False):
    from app.market_calendar import IDX_MARCH_2026_CLOSURES
    days = []
    day = date(2025, 5, 5)
    while day < date(2026, 5, 2):
        if day.weekday() < 5 and day not in IDX_MARCH_2026_CLOSURES and day not in missing:
            days.append(day)
        day += timedelta(days=1)
    if add_holiday:
        days.append(date(2026, 3, 20))
        days.sort()
    return [
        Candle(datetime(d.year,d.month,d.day,9,2,tzinfo=timezone.utc)
               .isoformat().replace('+00:00','Z'), 100., 104., 97., 101., 500_000.)
        for d in days
    ]


def test_idx_researched_nyepi_eid_gap_is_not_missing_history(tmp_path):
    ins = next(i for i in INSTRUMENTS if i.market == 'IDX')
    store = HistoryStore(tmp_path/'history.sqlite', clock=Clock())
    store.ingest(ins,idx_market_bars(),source='YFINANCE_RESEARCH_RAW',
                 price_basis='VENDOR_UNVERIFIED')
    snap = store.read(ins.instrument_id, source='YFINANCE_RESEARCH_RAW',
                      price_basis='VENDOR_UNVERIFIED')
    assert 'LONG_GAP_REQUIRES_CALENDAR_REVIEW' in snap['quality_flags']
    report = audit_snapshot(ins,snap)
    assert report['status'] == 'STRUCTURAL_PASS'
    assert report['reviewed_long_gap_count'] == 1
    assert report['calendar_validated'] is False
    assert report['calendar_coverage'] == 'PARTIAL_REVIEWED_IDX_CLOSURES'
    replay = replay_from_archive(store,ins,mode='live',source='YFINANCE_RESEARCH_RAW',
                                 price_basis='VENDOR_UNVERIFIED')
    assert replay['validated'] is False
    assert replay['archive_snapshot']['quality_report']['reviewed_long_gap_count'] == 1
    assert 'REVIEWED_IDX_MARCH_2026_HOLIDAY_GAP' in replay['archive_snapshot']['quality_flags']
    assert 'LONG_GAP_REQUIRES_CALENDAR_REVIEW' not in replay['archive_snapshot']['quality_flags']


def test_idx_unexplained_weekday_gap_still_blocks_replay(tmp_path):
    ins = next(i for i in INSTRUMENTS if i.market == 'IDX')
    store = HistoryStore(tmp_path/'history.sqlite', clock=Clock())
    store.ingest(ins, idx_market_bars(missing=frozenset({date(2026,3,17)})),
                 source='YFINANCE_RESEARCH_RAW', price_basis='VENDOR_UNVERIFIED')
    snap = store.read(ins.instrument_id,source='YFINANCE_RESEARCH_RAW',
                      price_basis='VENDOR_UNVERIFIED')
    assert audit_snapshot(ins,snap)['status'] == 'BLOCKED'
    with pytest.raises(HistoryError, match='LONG_GAP_REQUIRES_CALENDAR_REVIEW'):
        replay_from_archive(store, ins, mode='live',
                            source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')


def test_idx_candle_on_declared_exchange_closure_blocks(tmp_path):
    ins = next(i for i in INSTRUMENTS if i.market == 'IDX')
    store = HistoryStore(tmp_path/'history.sqlite', clock=Clock())
    store.ingest(ins, idx_market_bars(add_holiday=True),
                 source='YFINANCE_RESEARCH_RAW',price_basis='VENDOR_UNVERIFIED')
    snap = store.read(ins.instrument_id,source='YFINANCE_RESEARCH_RAW',
                      price_basis='VENDOR_UNVERIFIED')
    report = audit_snapshot(ins,snap)
    assert report['status'] == 'BLOCKED'
    assert report['finding_counts']['CANDLE_ON_REVIEWED_IDX_CLOSURE'] == 1


def test_reviewed_idx_exception_does_not_apply_to_us_or_outside_march():
    from app.market_calendar import reviewed_idx_gap
    assert reviewed_idx_gap('IDX',date(2026,3,17),date(2026,3,25))
    assert not reviewed_idx_gap('US',date(2026,3,17),date(2026,3,25))
    assert not reviewed_idx_gap('IDX',date(2026,3,16),date(2026,3,25))
    assert not reviewed_idx_gap('IDX',date(2026,4,1),date(2026,4,12))
