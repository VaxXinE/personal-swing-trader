"""Cold LIVE pages must never trigger hidden provider network calls."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main, service
from app.storage import Store


def test_live_get_latest_does_not_auto_scan(tmp_path, monkeypatch):
    store = Store(tmp_path / 'empty.db')
    monkeypatch.setattr(service, 'scan', lambda *a, **kw: pytest.fail('Unexpected LIVE scan'))
    result = service.get_latest(store, 'live')
    assert result['no_cached_run'] is True
    assert result['run_id'] is None and result['items'] == []
    assert result['forecast_status'] == 'NOT_VALIDATED'
    assert store.list_runs() == []


def test_live_readonly_api_does_not_contact_providers_on_cold_start(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'store', Store(tmp_path / 'live.db'))
    monkeypatch.setattr(main, 'settings', SimpleNamespace(data_mode='live', api_token=''))
    monkeypatch.setattr(service, 'scan', lambda *a, **kw: pytest.fail('Unexpected LIVE scan'))
    client = TestClient(main.app)
    result = client.get('/v1/opportunities')
    assert result.status_code == 200
    assert result.json()['no_cached_run'] is True
    assert result.json()['items'] == []
    universe = client.get('/v1/universe')
    assert universe.status_code == 200
    assert universe.json()['run_id'] is None
    analysis = client.get('/v1/instruments/US:NASDAQ:MSFT/analysis')
    assert analysis.status_code == 404


def test_demo_get_latest_keeps_initial_fixture_scan(tmp_path):
    store = Store(tmp_path / 'demo.db')
    result = service.get_latest(store, 'demo')
    assert result['data_mode'] == 'demo'
    assert result['count'] >= 0
    assert store.list_runs()
