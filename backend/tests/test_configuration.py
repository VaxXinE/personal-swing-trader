"""Protect CLI environment overrides from stale dataclass defaults."""
from app.config import Settings


def test_settings_read_environment_when_instantiated(monkeypatch, tmp_path):
    monkeypatch.setenv('SWING_DATA_MODE', 'live')
    monkeypatch.setenv('SWING_DB_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setenv('SWING_HOST', '127.0.0.1')
    configured = Settings()
    assert configured.data_mode == 'live'
    assert configured.db_path == tmp_path / 'test.db'


def test_private_binding_requires_random_token(monkeypatch):
    monkeypatch.setenv('SWING_HOST', '0.0.0.0')
    monkeypatch.setenv('SWING_API_TOKEN', '')
    try:
        Settings()
    except ValueError as exc:
        assert 'SWING_API_TOKEN' in str(exc)
    else:
        raise AssertionError('Server must not allow publicly routable bind without token')
