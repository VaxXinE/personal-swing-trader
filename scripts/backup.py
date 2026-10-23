"""SQLite online consistent backup, no network/upload. Keep backup directory private."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.config import settings
root=Path(__file__).resolve().parents[1]
if not settings.db_path.exists():raise SystemExit('Database not found. Run the app first.')
output=root/'backups'/('swing-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.db')
output.parent.mkdir(exist_ok=True)
with sqlite3.connect(settings.db_path) as db, sqlite3.connect(output) as b:db.backup(b)
print('Backup:',output,'SHA256:',hashlib.sha256(output.read_bytes()).hexdigest())
print('Backup is NOT encrypted. Store on encrypted media; never commit.')
