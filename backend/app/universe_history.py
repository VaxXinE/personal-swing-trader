"""Observed candidate-universe history, not a historical listing certification.

The current registry is a sampled research roster. A later observation can never
establish eligibility for an earlier market session.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Callable, Sequence
from uuid import uuid4

from .domain import Candle, Instrument
from .history import HistoryError, _iso, _timestamp, _canonical

MAX_CAPTURES = 1000


def _fingerprint(value: object) -> str:
    return sha256(_canonical(value).encode('utf-8')).hexdigest()


class UniverseHistory:
    """Persist explicit observations; reads do not create or modify tables."""

    def __init__(self, path: Path, *, clock: Callable[[], datetime] | None = None):
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=10000')
        return db

    def capture(self, instruments: Sequence[Instrument], *, mode: str) -> dict:
        if mode not in ('demo', 'live'):
            raise HistoryError('Unsupported universe observation mode')
        if not 1 <= len(instruments) <= 250:
            raise HistoryError('Candidate roster must have 1..250 instruments')
        stamp = self.clock()
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise HistoryError('Observation clock must be UTC')
        observed_at = _iso(stamp)
        ids = [i.instrument_id for i in instruments]
        if len(set(ids)) != len(ids):
            raise HistoryError('Duplicate candidate instrument ID')
        for item in instruments:
            if (item.market not in ('US', 'IDX', 'CRYPTO') or
                    not item.instrument_id.startswith(item.market + ':')):
                raise HistoryError('Invalid candidate market or instrument ID')
        # Do not save speculative historical listing dates in this observation.
        payload = {'mode': mode, 'source': 'CURRENT_REGISTRY_SAMPLE',
                   'instruments': sorted(ids)}
        digest = _fingerprint({'observed_at': observed_at, 'payload': payload})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS history_universe_observations (
                id TEXT PRIMARY KEY,
                observed_at TEXT NOT NULL,
                mode TEXT NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                UNIQUE(mode, observed_at)
            )''')
            db.execute('''CREATE INDEX IF NOT EXISTS idx_history_universe_observed
                          ON history_universe_observations(mode, observed_at)''')
            # An identical capture at the exact same clock tick is idempotent.
            current = db.execute('''SELECT id, sha256 FROM history_universe_observations
                WHERE observed_at=? AND mode=? LIMIT 1''',
                (observed_at, mode)).fetchone()
            if current and current['sha256'] != digest:
                raise HistoryError('Conflicting candidate roster at the same observation time')
            if current:
                capture_id = current['id']
                unchanged = True
            else:
                capture_id = uuid4().hex
                db.execute('''INSERT INTO history_universe_observations
                            (id, observed_at, mode, source, payload_json, sha256)
                            VALUES(?,?,?,?,?,?)''',
                           (capture_id, observed_at, mode, payload['source'],
                            _canonical(payload), digest))
                unchanged = False
        return {'id': capture_id, 'observed_at': observed_at, 'mode': mode,
                'source': payload['source'], 'candidate_count': len(ids),
                'sha256': digest, 'unchanged': unchanged,
                'historical_membership_verified': False,
                'scope': 'OBSERVED_REGISTRY_SAMPLE'}

    def _observations(self, mode: str, cutoff: str) -> list[dict]:
        if mode not in ('demo', 'live'):
            raise HistoryError('Invalid universe mode')
        cutoff_iso = _iso(_timestamp(cutoff))
        if not self.path.is_file():
            return []
        with self._connect() as db:
            found = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history_universe_observations'").fetchone()
            if not found:
                return []
            rows = db.execute('''SELECT observed_at, mode, source, payload_json, sha256
                        FROM history_universe_observations
                        WHERE mode=? AND observed_at<=?
                        ORDER BY observed_at, id LIMIT ?''',
                        (mode, cutoff_iso, MAX_CAPTURES + 1)).fetchall()
        if len(rows) > MAX_CAPTURES:
            raise HistoryError('Universe observation history exceeds supported audit window')
        captures = []
        for row in rows:
            if _fingerprint({'observed_at': row['observed_at'], 'payload': json.loads(row['payload_json'])}) != row['sha256']:
                raise HistoryError('Universe observation checksum mismatch')
            payload = json.loads(row['payload_json'])
            if payload.get('mode') != mode or payload.get('source') != row['source'] or \
                    payload.get('source') != 'CURRENT_REGISTRY_SAMPLE':
                raise HistoryError('Universe observation provenance mismatch')
            ids = payload.get('instruments')
            if not isinstance(ids, list) or not ids or len(ids) > 250 or \
                    any(not isinstance(x, str) or len(x) > 80 for x in ids) or \
                    ids != sorted(set(ids)):
                raise HistoryError('Malformed universe observation membership')
            captures.append({'observed_at': row['observed_at'],
                             'sha256': row['sha256'], 'instruments': ids})
        return captures

    def report(self, instrument: Instrument, bars: Sequence[Candle], *,
               mode: str, as_of: str) -> dict:
        captures = self._observations(mode, as_of)
        times = [_timestamp(x['observed_at']) for x in captures]
        counts = {'UNKNOWN_BEFORE_OBSERVATION': 0,
                  'OBSERVED_CANDIDATE': 0,
                  'UNKNOWN_NOT_IN_SAMPLE': 0}
        for candle in bars:
            bar_at = _timestamp(candle.at)
            idx = bisect_right(times, bar_at) - 1
            if idx < 0:
                counts['UNKNOWN_BEFORE_OBSERVATION'] += 1
            elif instrument.instrument_id in captures[idx]['instruments']:
                counts['OBSERVED_CANDIDATE'] += 1
            else:
                counts['UNKNOWN_NOT_IN_SAMPLE'] += 1
        # Absent from a sampled roster does NOT mean unlisted, delisted or ineligible.
        evidence = [{'observed_at': x['observed_at'], 'sha256': x['sha256']}
                    for x in captures]
        return {'status': 'OBSERVATION_ONLY' if captures else 'NO_UNIVERSE_EVIDENCE',
                'instrument_id': instrument.instrument_id,
                'captured_rosters': len(captures),
                'latest_observed_at': captures[-1]['observed_at'] if captures else None,
                'candidate_observation_counts': counts,
                'evidence_sha256': _fingerprint({'instrument_id': instrument.instrument_id,
                                                  'mode': mode, 'captures': evidence}),
                'historical_membership_verified': False,
                'point_in_time_universe_validated': False,
                'survivorship_bias_resolved': False,
                'note': 'Current candidate rosters do not prove full historic listings, IPO/delisting dates or past eligibility.'}

    def captures(self, *, mode: str, as_of: str, limit: int = 20) -> list[dict]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise HistoryError('Universe capture limit must be 1..100')
        captures = self._observations(mode, as_of)
        return [{'observed_at': item['observed_at'], 'sha256': item['sha256'],
                 'candidate_count': len(item['instruments']),
                 'historical_membership_verified': False}
                for item in reversed(captures[-limit:])]
