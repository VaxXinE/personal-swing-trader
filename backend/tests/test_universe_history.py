"""Offline universe-observation contracts: sample membership never proves historical eligibility."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.domain import Candle, INSTRUMENTS
from app.history import HistoryError, HistoryStore
from app.universe_history import UniverseHistory
from app.archive_backtest import SnapshotMismatch, replay_from_archive
from app import history_api
import app.main as main


class Clock:
    def __init__(self, when):
        self.when = when

    def __call__(self):
        return self.when


def candle(day):
    return Candle(day.isoformat().replace('+00:00', 'Z'), 100, 104, 98, 101, 500000)


def test_capture_is_idempotent_with_same_clock_and_append_only(tmp_path):
    when = datetime(2026, 1, 5, 20, tzinfo=timezone.utc)
    history = UniverseHistory(tmp_path/'observations.sqlite', clock=Clock(when))
    instrument = INSTRUMENTS[0]
    first = history.capture([instrument], mode='demo')
    again = history.capture([instrument], mode='demo')
    assert not first['unchanged'] and again['unchanged']
    assert first['sha256'] == again['sha256'] and first['id'] == again['id']
    with sqlite3.connect(history.path) as db:
        assert db.execute('SELECT COUNT(*) FROM history_universe_observations').fetchone()[0] == 1
    assert not first['historical_membership_verified']
    with pytest.raises(HistoryError, match='Conflicting candidate roster'):
        history.capture([INSTRUMENTS[1]], mode='demo')


def test_as_of_bar_prevents_current_registry_from_backdating(tmp_path):
    instrument = INSTRUMENTS[0]
    clock = Clock(datetime(2026, 1, 5, 20, tzinfo=timezone.utc))
    history = UniverseHistory(tmp_path/'archive.sqlite', clock=clock)
    before = candle(datetime(2026, 1, 2, 20, tzinfo=timezone.utc))
    on = candle(datetime(2026, 1, 5, 21, tzinfo=timezone.utc))
    history.capture([instrument], mode='demo')
    clock.when = datetime(2026, 1, 6, 20, tzinfo=timezone.utc)
    history.capture([INSTRUMENTS[1]], mode='demo')
    after = candle(datetime(2026, 1, 7, 21, tzinfo=timezone.utc))
    counts = history.report(instrument, [before, on, after], mode='demo', as_of='2026-01-08T00:00:00Z')
    assert counts['candidate_observation_counts'] == {
        'UNKNOWN_BEFORE_OBSERVATION': 1, 'OBSERVED_CANDIDATE': 1, 'UNKNOWN_NOT_IN_SAMPLE': 1,
    }
    assert counts['historical_membership_verified'] is False
    assert counts['survivorship_bias_resolved'] is False
    assert history.report(instrument, [on], mode='demo', as_of='2026-01-05T19:59:59Z')['status'] == 'NO_UNIVERSE_EVIDENCE'


def test_mode_isolation_pinned_cutoff_and_digest_change(tmp_path):
    ins = INSTRUMENTS[0]
    clock = Clock(datetime(2026, 2, 1, tzinfo=timezone.utc))
    history = UniverseHistory(tmp_path/'u.sqlite', clock=clock)
    history.capture([ins], mode='demo')
    bar = candle(datetime(2026, 2, 3, tzinfo=timezone.utc))
    old = history.report(ins, [bar], mode='demo', as_of='2026-02-02T00:00:00Z')
    assert old['captured_rosters'] == 1
    assert history.report(ins, [bar], mode='live', as_of='2026-02-02T00:00:00Z')['status'] == 'NO_UNIVERSE_EVIDENCE'
    clock.when = datetime(2026, 2, 2, tzinfo=timezone.utc)
    history.capture([INSTRUMENTS[1]], mode='demo')
    pinned = history.report(ins, [bar], mode='demo', as_of='2026-02-01T23:59:59Z')
    latest = history.report(ins, [bar], mode='demo', as_of='2026-02-03T00:00:00Z')
    assert pinned['evidence_sha256'] == old['evidence_sha256']
    assert latest['evidence_sha256'] != old['evidence_sha256']
    assert latest['captured_rosters'] == 2
    assert not latest['point_in_time_universe_validated']


def test_corrupted_universe_payload_fails_closed(tmp_path):
    ins = INSTRUMENTS[0]
    history = UniverseHistory(tmp_path/'u.sqlite',clock=Clock(datetime(2026,1,1,tzinfo=timezone.utc)))
    history.capture([ins], mode='demo')
    with sqlite3.connect(history.path) as db:
        db.execute('UPDATE history_universe_observations SET payload_json=?', ('{}',))
    with pytest.raises(HistoryError, match='checksum mismatch'):
        history.report(ins, [], mode='demo', as_of='2026-02-01T00:00:00Z')


def test_mutated_observation_timestamp_detected(tmp_path):
    history=UniverseHistory(tmp_path/'u.sqlite',clock=Clock(datetime(2026,1,1,tzinfo=timezone.utc)))
    history.capture([INSTRUMENTS[0]], mode='demo')
    with sqlite3.connect(history.path) as db:
        db.execute("UPDATE history_universe_observations SET observed_at='2020-01-01T00:00:00Z'")
    with pytest.raises(HistoryError, match='checksum mismatch'):
        history.report(INSTRUMENTS[0], [],mode='demo',as_of='2026-02-01T00:00:00Z')


def test_read_without_capture_has_no_side_effects(tmp_path):
    empty = tmp_path/'not-created.sqlite'
    result = UniverseHistory(empty).report(INSTRUMENTS[0], [], mode='demo', as_of='2026-02-01T00:00:00Z')
    assert result['status'] == 'NO_UNIVERSE_EVIDENCE'
    assert not empty.exists()


def test_reject_duplicate_invalid_clock_and_registry_cap(tmp_path):
    ins=INSTRUMENTS[0]
    history=UniverseHistory(tmp_path/'u.sqlite',clock=Clock(datetime(2026,1,1,tzinfo=timezone.utc)))
    with pytest.raises(HistoryError, match='Duplicate'):
        history.capture([ins,ins], mode='demo')
    with pytest.raises(HistoryError, match='1..250'):
        history.capture([], mode='demo')
    history.clock=Clock(datetime(2026,1,1))
    with pytest.raises(HistoryError, match='UTC'):
        history.capture([ins], mode='demo')
    with pytest.raises(HistoryError, match='mode'):
        history.report(ins, [], mode='unknown', as_of='2026-02-01T00:00:00Z')


def test_archive_replay_discloses_historical_unknown_and_fingerprint(tmp_path):
    ins = INSTRUMENTS[0]
    tick = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = HistoryStore(tmp_path/'history.sqlite', clock=Clock(tick))
    start = datetime(2025, 1, 1, 20, tzinfo=timezone.utc)
    days=[]
    for offset in range(350):
        d=start+timedelta(days=offset)
        if d.weekday()<5:
            days.append(d)
    bars=[candle(d) for d in days[:230]]
    store.ingest(ins, bars, source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC')
    history = UniverseHistory(store.path,clock=Clock(tick))
    history.capture([ins], mode='demo')
    result = replay_from_archive(store, ins, mode='demo',source='SYNTHETIC_FIXTURE',price_basis='SYNTHETIC')
    evidence = result['archive_snapshot']['universe_evidence']
    assert evidence['candidate_observation_counts']['UNKNOWN_BEFORE_OBSERVATION'] == 230
    assert evidence['candidate_observation_counts']['OBSERVED_CANDIDATE'] == 0
    assert evidence['historical_membership_verified'] is False
    assert result['validated'] is False
    cutoff=result['archive_snapshot']['as_of_observation']
    pinned = replay_from_archive(store, ins, mode='demo',source='SYNTHETIC_FIXTURE',
                                 price_basis='SYNTHETIC', as_of=cutoff,
                                 expected_universe_evidence_sha256=evidence['evidence_sha256'])
    assert pinned['archive_snapshot']['universe_evidence']['evidence_sha256']==evidence['evidence_sha256']
    with pytest.raises(SnapshotMismatch,match='universe'):
        replay_from_archive(store,ins,mode='demo',source='SYNTHETIC_FIXTURE',
            price_basis='SYNTHETIC',expected_universe_evidence_sha256='0'*64)


def test_universe_capture_api_private_mode_isolated(tmp_path, monkeypatch):
    history = UniverseHistory(tmp_path/'api.sqlite',clock=Clock(datetime(2026,1,1,tzinfo=timezone.utc)))
    history.capture([INSTRUMENTS[0]],mode='demo')
    monkeypatch.setattr(history_api,'store',HistoryStore(history.path))
    monkeypatch.setattr(history_api,'settings',type('Settings',(),{'data_mode':'demo'})())
    client=TestClient(main.app)
    response=client.get('/v1/history/universe/captures')
    assert response.status_code==200, response.text
    assert response.json()['items'][0]['candidate_count']==1
    assert response.json()['historical_membership_verified'] is False
    assert client.post('/v1/history/universe/captures',json={}).status_code==405
    assert client.get('/v1/history/universe/captures',params={'limit':101}).status_code==422


def test_cli_capture_without_provider(tmp_path, monkeypatch, capsys):
    from scripts.universe_capture import main as capture_cli
    import scripts.universe_capture as cli_mod
    monkeypatch.setattr(cli_mod,'get_instruments', lambda _mode:(INSTRUMENTS[0],))
    rc=capture_cli(['--db',str(tmp_path/'history.sqlite'),'--mode','demo'])
    assert rc==0
    out=capsys.readouterr().out
    assert 'RESEARCH_ONLY' in out and 'observed_candidates=1' in out
