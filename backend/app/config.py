"""Configuration — defaults are explicitly demo-only, private and non-executable."""
import os
from dataclasses import dataclass, field
from pathlib import Path

def load_local_env() -> None:
    """Minimal .env reader; explicit environment always takes priority."""
    env_path = Path(__file__).resolve().parents[2] / '.env'
    if not env_path.is_file(): return
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        name, value = line.split('=', 1)
        name = name.strip()
        if name not in ('SWING_DATA_MODE','SWING_DB_PATH','SWING_API_TOKEN','SWING_HOST','SWING_PORT'):
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(name, value)

load_local_env()

@dataclass(frozen=True)
class Settings:
    data_mode: str = field(default_factory=lambda: os.getenv('SWING_DATA_MODE', 'demo').strip().lower())
    db_path: Path = field(default_factory=lambda: Path(os.getenv('SWING_DB_PATH', str(Path(__file__).resolve().parents[2] / 'data' / 'swing.db'))))
    api_token: str = field(default_factory=lambda: os.getenv('SWING_API_TOKEN', ''))
    host: str = field(default_factory=lambda: os.getenv('SWING_HOST', '127.0.0.1'))

    def __post_init__(self):
        if self.data_mode not in ('demo', 'live'):
            raise ValueError('SWING_DATA_MODE must be demo or live')
        if self.host not in ('127.0.0.1', 'localhost', '::1') and len(self.api_token) < 32:
            raise ValueError('Non-loopback requires SWING_API_TOKEN at least 32 chars')

settings = Settings()
