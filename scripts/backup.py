"""Consistent local SQLite snapshots and verified, non-destructive restoration."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

MANIFEST = 'manifest.json'
ALLOWED = {'swing.db', 'history.sqlite'}
MAX_FILE_BYTES = 64 * 1024**3


class BackupError(ValueError):
    pass


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def check_database(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise BackupError(f'Not a regular SQLite backup: {path.name}')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise BackupError(f'SQLite integrity check failed: {path.name}')
        if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise BackupError(f'SQLite foreign-key check failed: {path.name}')


def create_backup(db_path: Path, history_path: Path, backup_root: Path) -> Path:
    """Use SQLite's backup API so active WAL files are captured consistently per DB."""
    db_path, history_path, backup_root = map(Path, (db_path, history_path, backup_root))
    if db_path.is_symlink() or not db_path.is_file():
        raise BackupError('Primary swing database missing or is a symbolic link')
    if history_path.is_symlink():
        raise BackupError('Historical database cannot be a symbolic link')
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if backup_root.is_symlink():
        raise BackupError('Backup root cannot be a symbolic link')
    destination = backup_root / ('swing-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid4().hex[:8])
    pending = Path(tempfile.mkdtemp(prefix='.pending-backup-', dir=backup_root))
    os.chmod(pending, 0o700)
    try:
        files = {}
        for name, original in (('swing.db', db_path), ('history.sqlite', history_path)):
            if not original.exists():
                if name == 'swing.db':
                    raise BackupError('Primary swing database missing')
                continue
            if not original.is_file() or original.is_symlink():
                raise BackupError('Unsafe SQLite source path')
            dest = pending / name
            with closing(sqlite3.connect(original.as_uri() + '?mode=ro', uri=True)) as source:
                with closing(sqlite3.connect(dest)) as output:
                    source.backup(output)
            os.chmod(dest, 0o600)
            check_database(dest)
            files[name] = {'sha256': checksum(dest), 'bytes': dest.stat().st_size}
        payload = {
            'schema_version': 1,
            'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'files': files,
            'note': 'Each SQLite file is a consistent snapshot; cross-database atomicity is not guaranteed.',
        }
        manifest = pending / MANIFEST
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        os.chmod(manifest, 0o600)
        os.rename(pending, destination)
        return destination
    except Exception:
        shutil.rmtree(pending, ignore_errors=True)
        raise


def verify_backup(backup_dir: Path) -> dict:
    backup_dir = Path(backup_dir)
    if backup_dir.is_symlink() or not backup_dir.is_dir():
        raise BackupError('Backup directory missing or is a symbolic link')
    manifest = backup_dir / MANIFEST
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 64 * 1024:
        raise BackupError('Backup manifest missing or oversized')
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError, OSError) as exc:
        raise BackupError('Invalid backup manifest') from exc
    if (not isinstance(data, dict) or data.get('schema_version') != 1 or
            not isinstance(data.get('files'), dict) or
            not data['files'] or 'swing.db' not in data['files'] or
            not set(data['files']).issubset(ALLOWED)):
        raise BackupError('Unknown backup format or file paths')
    for name, meta in data['files'].items():
        file = backup_dir / name
        if (not isinstance(meta, dict) or not isinstance(meta.get('bytes'), int) or
                isinstance(meta['bytes'], bool) or not 0 < meta['bytes'] <= MAX_FILE_BYTES or
                not isinstance(meta.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', meta['sha256']) or
                file.is_symlink() or not file.is_file() or file.stat().st_size != meta['bytes']):
            raise BackupError(f'Invalid or missing backup file: {name}')
        if not hmac.compare_digest(checksum(file), meta['sha256']):
            raise BackupError(f'Backup checksum mismatch: {name}')
        try:
            check_database(file)
        except sqlite3.DatabaseError as exc:
            raise BackupError(f'Invalid SQLite backup: {name}') from exc
    return data


def restore_backup(backup_dir: Path, target_dir: Path) -> Path:
    """Restore only to a new directory; never overwrite a working database."""
    backup_dir, target_dir = Path(backup_dir), Path(target_dir)
    data = verify_backup(backup_dir)
    if target_dir.exists() or target_dir.is_symlink():
        raise BackupError('Restore target already exists; choose a new directory')
    parent = target_dir.parent
    if not parent.is_dir():
        raise BackupError('Restore parent directory does not exist')
    if backup_dir.resolve() in target_dir.resolve().parents:
        raise BackupError('Restore target cannot be nested inside backup directory')
    pending = Path(tempfile.mkdtemp(prefix='.pending-restore-', dir=parent))
    os.chmod(pending, 0o700)
    try:
        for name in data['files']:
            destination = pending / name
            shutil.copyfile(backup_dir / name, destination)
            os.chmod(destination, 0o600)
            check_database(destination)
        if target_dir.exists():
            raise BackupError('Restore target already exists')
        os.rename(pending, target_dir)
        return target_dir
    except Exception:
        shutil.rmtree(pending, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    from app.config import settings
    parser = argparse.ArgumentParser(description='Offline SQLite backup, verification and safe restore')
    parser.add_argument('--db', type=Path, default=settings.db_path)
    parser.add_argument('--history-db', type=Path, default=settings.db_path.parent / 'history.sqlite')
    parser.add_argument('--backup-root', type=Path, default=ROOT / 'backups')
    parser.add_argument('--verify', type=Path, metavar='BACKUP_DIRECTORY')
    parser.add_argument('--restore', type=Path, metavar='BACKUP_DIRECTORY')
    parser.add_argument('--target', type=Path, help='New, nonexistent directory for restored databases')
    args = parser.parse_args(argv)
    if args.verify and args.restore:
        parser.error('Choose --verify OR --restore')
    if (args.restore is None) != (args.target is None):
        parser.error('--target is required only with --restore')
    try:
        if args.verify:
            data = verify_backup(args.verify)
            print(f"VERIFIED {args.verify} databases={','.join(sorted(data['files']))}")
        elif args.restore:
            restored = restore_backup(args.restore, args.target)
            print(f"RESTORED {restored} (existing databases untouched)")
        else:
            folder = create_backup(args.db, args.history_db, args.backup_root)
            print(f"BACKED_UP {folder} databases={','.join(sorted(verify_backup(folder)['files']))}")
        print('Backups are NOT encrypted. Store on encrypted/private media, never in Git.')
        return 0
    except (BackupError, sqlite3.DatabaseError, OSError) as exc:
        print(f'Backup operation rejected: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
