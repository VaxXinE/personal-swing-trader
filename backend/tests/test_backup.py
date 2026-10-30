"""Offline recovery drills, including WAL, tampering and non-destructive restore."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from scripts.backup import BackupError, create_backup, restore_backup, verify_backup, main


def seed(path: Path, value: str) -> None:
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE items (v TEXT NOT NULL)')
        db.execute('INSERT INTO items VALUES (?)', (value,))


def test_backup_restore_both_databases_and_checksums(tmp_path):
    db, history = tmp_path/'swing.db', tmp_path/'history.sqlite'
    seed(db, 'journal')
    seed(history, 'market')
    backup = create_backup(db, history, tmp_path/'backups')
    manifest = verify_backup(backup)
    assert set(manifest['files']) == {'swing.db', 'history.sqlite'}
    restored = restore_backup(backup, tmp_path/'restored')
    with sqlite3.connect(restored/'swing.db') as c:
        assert c.execute('SELECT v FROM items').fetchone()[0] == 'journal'
    with sqlite3.connect(restored/'history.sqlite') as c:
        assert c.execute('SELECT v FROM items').fetchone()[0] == 'market'
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT v FROM items').fetchone()[0] == 'journal'


def test_online_wal_backup_contains_uncheckpointed_commits(tmp_path):
    db = tmp_path/'swing.db'
    connection = sqlite3.connect(db)
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('CREATE TABLE events (id INTEGER PRIMARY KEY)')
        connection.execute('INSERT INTO events VALUES (9)')
        connection.commit()
        backup = create_backup(db, tmp_path/'no-history.sqlite', tmp_path/'backups')
        assert set(verify_backup(backup)['files']) == {'swing.db'}
        with sqlite3.connect(backup/'swing.db') as saved:
            assert saved.execute('SELECT id FROM events').fetchone()[0] == 9
    finally:
        connection.close()


def test_modified_backup_is_rejected_without_creating_restore_target(tmp_path):
    db = tmp_path/'swing.db'
    seed(db, 'private')
    backup = create_backup(db, tmp_path/'absent.sqlite', tmp_path/'backups')
    with (backup/'swing.db').open('ab') as stream:
        stream.write(b'corruption')
    with pytest.raises(BackupError, match='bytes|checksum|backup file'):
        restore_backup(backup, tmp_path/'restored')
    assert not (tmp_path/'restored').exists()


def test_manifest_traversal_and_wrong_format_rejected(tmp_path):
    db = tmp_path/'swing.db'
    seed(db, 'x')
    backup = create_backup(db, tmp_path/'none.sqlite', tmp_path/'backups')
    manifest = backup/'manifest.json'
    payload = json.loads(manifest.read_text())
    payload['files']['../../outside.db'] = payload['files']['swing.db']
    manifest.write_text(json.dumps(payload))
    with pytest.raises(BackupError, match='file paths'):
        verify_backup(backup)
    assert not (tmp_path/'outside.db').exists()


def test_existing_restore_target_is_never_overwritten(tmp_path):
    db = tmp_path/'swing.db'
    seed(db, 'original')
    backup = create_backup(db, tmp_path/'none.sqlite', tmp_path/'backups')
    target = tmp_path/'restored'
    target.mkdir()
    sentinel = target/'important.txt'
    sentinel.write_text('do not touch')
    with pytest.raises(BackupError, match='already exists'):
        restore_backup(backup, target)
    assert sentinel.read_text() == 'do not touch'


def test_backup_does_not_follow_source_symlink(tmp_path):
    db = tmp_path/'swing.db'
    seed(db, 'x')
    link = tmp_path/'link.sqlite'
    link.symlink_to(db)
    with pytest.raises(BackupError, match='symbolic link'):
        create_backup(link, tmp_path/'none.sqlite', tmp_path/'backups')


def test_cli_backup_verify_restore(tmp_path, capsys):
    db = tmp_path/'swing.db'
    seed(db, 'x')
    folder = tmp_path/'backups'
    assert main(['--db',str(db),'--history-db',str(tmp_path/'missing'),
                 '--backup-root',str(folder)]) == 0
    backups = list(folder.iterdir())
    assert len(backups) == 1
    assert main(['--verify',str(backups[0])]) == 0
    assert main(['--restore',str(backups[0]),'--target',str(tmp_path/'restored')]) == 0
    assert main(['--restore',str(backups[0]),'--target',str(tmp_path/'restored')]) == 2
    assert 'RESTORED' in capsys.readouterr().out


def test_relative_input_paths_are_supported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    seed(tmp_path/'swing.db', 'local')
    backup = create_backup(Path('swing.db'), Path('missing.sqlite'), Path('backups'))
    assert 'swing.db' in verify_backup(backup)['files']
