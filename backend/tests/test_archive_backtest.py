"""Offline integration acceptance: real HistoryStore -> real replay via private API."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.archive_backtest import replay_from_archive, ArchiveNotFound, SnapshotMismatch
from app.domain import Candle, INSTRUMENTS
from app.history import HistoryStore, HistoryError
from app import history_api
import app.main as main


class Clock:
    def __init__(self):
        self.at = datetime(2026, 2, 1, tzinfo=timezone.utc)
    def __call__(self):
        return self.at


def make_bars(n=230):
    # Choose an EOD UTC marker whose New York session date matches the day.
    start = datetime(2025, 1, 1, 20, tzinfo=timezone.utc)
    # Equity fixtures use weekdays. Weekends are not ordinary US sessions.
    # These are still SYNTHETIC; official holidays are NOT certified here.
    sessions = []
    current = start
    while len(sessions) < n:
        if current.weekday() < 5:
            sessions.append(current)
        current += timedelta(days=1)
    return [
        Candle(session.isoformat().replace('+00:00', 'Z'),
               100.0, 105.0, 95.0, 101.0, 250000.0)
        for session in sessions
    ]


def make_archive(tmp_path, *, price_basis='SYNTHETIC', source='SYNTHETIC_FIXTURE', count=230):
    clock = Clock()
    archive = HistoryStore(tmp_path / 'history.sqlite', clock=clock)
    bars = make_bars(count)
    archive.ingest(INSTRUMENTS[0], bars, source=source, price_basis=price_basis)
    return archive, clock, bars


def replay_demo(archive, **kwargs):
    return replay_from_archive(archive, INSTRUMENTS[0], mode='demo',
                               source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC', **kwargs)


def test_archive_replay_reads_without_provider_and_retains_research_only(tmp_path, monkeypatch):
    archive, _, _ = make_archive(tmp_path)
    monkeypatch.setattr(main, 'load_bars', lambda *a, **k: pytest.fail('Provider must not be called'))
    result = replay_demo(archive)
    provenance = result['archive_snapshot']
    assert result['version'] == '2.0-research'
    assert result['validated'] is False and result['status'] == 'RESEARCH_ONLY'
    assert provenance['rows'] == 230
    assert len(provenance['sha256']) == 64
    assert provenance['point_in_time_validated'] is False
    assert provenance['corporate_actions_verified'] is False
    assert provenance['execution_verified'] is False
    assert provenance['source'] == 'SYNTHETIC_FIXTURE'
    assert result['samples'] == 0


def test_stable_cutoff_and_revision_change_fingerprint(tmp_path):
    archive, clock, bars = make_archive(tmp_path)
    first = replay_demo(archive)
    cutoff = first['archive_snapshot']['as_of_observation']
    digest = first['archive_snapshot']['sha256']
    unchanged = replay_demo(archive, as_of=cutoff, expected_snapshot_sha256=digest)
    assert unchanged['archive_snapshot']['sha256'] == digest
    assert unchanged['trades'] == first['trades']
    clock.at = datetime(2026, 2, 2, tzinfo=timezone.utc)
    corrected = bars[:-1] + [replace(bars[-1], close=102.0)]
    archive.ingest(INSTRUMENTS[0], corrected, source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC')
    historical = replay_demo(archive, as_of=cutoff, expected_snapshot_sha256=digest)
    latest = replay_demo(archive)
    assert historical['archive_snapshot']['sha256'] == digest
    assert latest['archive_snapshot']['sha256'] != digest
    with pytest.raises(SnapshotMismatch, match='fingerprint'):
        replay_demo(archive, expected_snapshot_sha256=digest)


def test_market_mode_and_price_basis_are_never_mixed(tmp_path):
    archive, _, _ = make_archive(tmp_path)
    with pytest.raises(HistoryError, match='Source and price basis'):
        replay_from_archive(archive, INSTRUMENTS[0], mode='live',
                            source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC')
    with pytest.raises(HistoryError, match='Source and price basis'):
        replay_from_archive(archive, INSTRUMENTS[0], mode='demo',
                            source='YFINANCE_RESEARCH_RAW', price_basis='VENDOR_UNVERIFIED')
    with pytest.raises(HistoryError, match='Source and price basis'):
        replay_from_archive(archive, INSTRUMENTS[0], mode='demo',
                            source='SYNTHETIC_FIXTURE', price_basis='VENDOR_UNVERIFIED')


def test_live_vendor_archive_is_research_only_and_never_fetches(tmp_path, monkeypatch):
    archive, _, _ = make_archive(tmp_path, source='YFINANCE_RESEARCH_RAW', price_basis='VENDOR_UNVERIFIED')
    monkeypatch.setattr(main, 'load_bars', lambda *a, **k: pytest.fail('No live network allowed'))
    result = replay_from_archive(archive, INSTRUMENTS[0], mode='live',
                                 source='YFINANCE_RESEARCH_RAW', price_basis='VENDOR_UNVERIFIED')
    assert result['validated'] is False
    assert 'PRICE_BASIS_UNVERIFIED' in result['archive_snapshot']['quality_flags']
    assert result['archive_snapshot']['point_in_time_validated'] is False


def test_refuse_suspected_splits_and_unexpected_quality_flags(tmp_path):
    archive, _, bars = make_archive(tmp_path, count=225)
    # Create a separate late correction with discontinuity and a valid OHLC structure.
    # The archive flags it; the bridge must not silently use it to simulate fills.
    broken = list(bars)
    broken[220] = replace(broken[220], open=50, high=54, low=47, close=51)
    newer = HistoryStore(tmp_path/'other.sqlite', clock=Clock())
    newer.ingest(INSTRUMENTS[0], broken, source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC')
    with pytest.raises(HistoryError, match='SPLIT_OR_OUTLIER_SUSPECTED'):
        replay_demo(newer)


def test_empty_or_too_short_archive_fails_closed(tmp_path):
    archive = HistoryStore(tmp_path / 'empty.sqlite', clock=Clock())
    with pytest.raises(ArchiveNotFound):
        replay_demo(archive)
    shorter, _, _ = make_archive(tmp_path / 'short', count=70)
    with pytest.raises(HistoryError, match='Insufficient'):
        replay_demo(shorter)


def test_tampering_detected_by_archive_read(tmp_path):
    archive, _, _ = make_archive(tmp_path)
    with sqlite3.connect(archive.path) as db:
        db.execute("UPDATE history_candles SET payload_json='{}' WHERE bar_at=(SELECT MIN(bar_at) FROM history_candles)")
    with pytest.raises(HistoryError, match='checksum mismatch'):
        replay_demo(archive)


def test_api_replay_requires_read_only_archive_and_provides_reproduction_token(tmp_path, monkeypatch):
    archive, _, _ = make_archive(tmp_path)
    monkeypatch.setattr(history_api, 'store', archive)
    monkeypatch.setattr(history_api, 'settings', SimpleNamespace(data_mode='demo'))
    client = TestClient(main.app)
    url = '/v1/history/backtests/' + INSTRUMENTS[0].instrument_id
    params = {'source':'SYNTHETIC_FIXTURE', 'price_basis':'SYNTHETIC', 'strategy':'PULLBACK'}
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    payload = response.json()
    snapshot = payload['archive_snapshot']
    stable = client.get(url, params={**params, 'as_of':snapshot['as_of_observation'],
                                     'expected_snapshot_sha256':snapshot['sha256']})
    assert stable.status_code == 200
    assert stable.json()['archive_snapshot']['sha256'] == snapshot['sha256']
    assert client.post(url, json=params).status_code == 405
    assert client.get(url, params={**params, 'source':'YFINANCE_RESEARCH_RAW'}).status_code == 422
    assert client.get(url, params={**params, 'expected_snapshot_sha256':'0'*64}).status_code == 409
    assert client.get(url, params={**params, 'limit':10}).status_code == 422


def test_api_authentication_applies_to_archive_replay(tmp_path, monkeypatch):
    archive, _, _ = make_archive(tmp_path)
    monkeypatch.setattr(history_api, 'store', archive)
    monkeypatch.setattr(history_api, 'settings', SimpleNamespace(data_mode='demo'))
    monkeypatch.setattr(main, 'settings', SimpleNamespace(api_token='s'*40))
    client = TestClient(main.app)
    url = '/v1/history/backtests/' + INSTRUMENTS[0].instrument_id
    params = {'source':'SYNTHETIC_FIXTURE', 'price_basis':'SYNTHETIC'}
    assert client.get(url, params=params).status_code == 401
    assert client.get(url, params=params, headers={'Authorization':'Bearer '+'s'*40}).status_code == 200


def test_derived_quality_blocks_if_unprotected_flags_json_were_changed(tmp_path):
    archive, _, bars = make_archive(tmp_path, count=225)
    broken = list(bars)
    broken[220] = replace(broken[220], open=50, high=54, low=47, close=51)
    extra = HistoryStore(tmp_path/'tamperflags.sqlite', clock=Clock())
    extra.ingest(INSTRUMENTS[0], broken, source='SYNTHETIC_FIXTURE', price_basis='SYNTHETIC')
    with sqlite3.connect(extra.path) as db:
        db.execute("UPDATE history_candles SET flags_json='[]'")
    with pytest.raises(HistoryError, match='SPLIT_OR_OUTLIER_SUSPECTED'):
        replay_demo(extra)


def test_offline_cli_reuses_archive_without_provider(tmp_path, monkeypatch, capsys):
    from scripts.archive_backtest import main as archive_main
    archive, _, _ = make_archive(tmp_path)
    monkeypatch.setattr(main, 'load_bars', lambda *a, **k: pytest.fail('Provider must not be called'))
    code = archive_main(['--db', str(archive.path), '--mode', 'demo',
                         '--instrument-id', INSTRUMENTS[0].instrument_id])
    out = capsys.readouterr().out
    assert code == 0
    assert 'snapshot_sha256=' in out
    assert 'RESEARCH_ONLY' in out
