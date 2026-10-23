"""Append-only research OHLC archive with point-in-time *observation* provenance.

No provider requests, process execution, stock split inference, or automatic trading.
Historical backfills are NEVER claimed to have been available at historical bar time.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import sqlite3
from typing import Callable, Sequence
from uuid import uuid4
from zoneinfo import ZoneInfo

from .domain import Candle, Instrument, validate_candles

MAX_BATCH_BARS = 2500
MAX_READ_BARS = 2500
PRICE_BASES = frozenset({'SYNTHETIC', 'VENDOR_UNVERIFIED', 'RAW_VERIFIED', 'SPLIT_ADJUSTED_VERIFIED'})
_ALLOWED_SOURCES = frozenset({'SYNTHETIC_FIXTURE', 'YFINANCE_RESEARCH_RAW', 'BINANCE_SPOT_EOD'})
_ID = re.compile(r'(?:US|IDX|CRYPTO):[A-Z0-9_-]{2,30}:[A-Z0-9.-]{1,30}\Z')
_SOURCE = re.compile(r'[A-Z][A-Z0-9_]{2,63}\Z')


class HistoryError(ValueError):
    """Invalid or unverified history cannot be silently turned into trading data."""


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HistoryError('Invalid ISO-8601 timestamp') from exc
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result):
        raise HistoryError('History timestamps must be UTC')
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _digest(obj: object) -> str:
    return sha256(_canonical(obj).encode('utf-8')).hexdigest()


def _session(market: str, at: str) -> str:
    zone = {'US': 'America/New_York', 'IDX': 'Asia/Jakarta', 'CRYPTO': 'UTC'}[market]
    return _timestamp(at).astimezone(ZoneInfo(zone)).date().isoformat()


@dataclass(frozen=True)
class CorporateAction:
    """Evidence-only event; never automatically alters execution OHLC."""
    action_type: str  # SPLIT or CASH_DIVIDEND
    effective_on: str
    value: str  # positive decimal as string; split ratio numerator/denominator
    announced_at: str | None = None
    currency: str | None = None


def _validate_action(event: CorporateAction) -> None:
    from decimal import Decimal, InvalidOperation
    if event.action_type not in ('SPLIT', 'CASH_DIVIDEND'):
        raise HistoryError('Unsupported corporate action type')
    try:
        date.fromisoformat(event.effective_on)
        amount = Decimal(event.value)
        if not amount.is_finite() or amount <= 0:
            raise ValueError('action value must be positive')
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise HistoryError('Invalid corporate action date or amount') from exc
    if event.announced_at is not None:
        _timestamp(event.announced_at)
    if event.action_type == 'CASH_DIVIDEND' and (not event.currency or not re.fullmatch(r'[A-Z]{3,5}', event.currency)):
        raise HistoryError('Dividend must have a currency')


class HistoryStore:
    def __init__(self, path: Path, *, clock: Callable[[], datetime] | None = None):
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS history_batches (
                id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL, market TEXT NOT NULL,
                source TEXT NOT NULL, price_basis TEXT NOT NULL, recorded_at TEXT NOT NULL,
                first_bar TEXT NOT NULL, last_bar TEXT NOT NULL,
                received INTEGER NOT NULL, inserted INTEGER NOT NULL, unchanged INTEGER NOT NULL,
                corrected INTEGER NOT NULL, manifest_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history_candles (
                instrument_id TEXT NOT NULL, market TEXT NOT NULL, source TEXT NOT NULL,
                price_basis TEXT NOT NULL, bar_at TEXT NOT NULL, session_date TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK(revision >= 1),
                first_observed_at TEXT NOT NULL, batch_id TEXT NOT NULL,
                payload_json TEXT NOT NULL, content_hash TEXT NOT NULL,
                flags_json TEXT NOT NULL,
                PRIMARY KEY(instrument_id, source, price_basis, bar_at, revision),
                FOREIGN KEY(batch_id) REFERENCES history_batches(id)
            );
            CREATE INDEX IF NOT EXISTS idx_history_observation ON history_candles
                (instrument_id, source, price_basis, first_observed_at, bar_at);
            CREATE TABLE IF NOT EXISTS history_actions (
                instrument_id TEXT NOT NULL, source TEXT NOT NULL, action_type TEXT NOT NULL,
                effective_on TEXT NOT NULL, revision INTEGER NOT NULL,
                first_observed_at TEXT NOT NULL, evidence_json TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                PRIMARY KEY(instrument_id, source, action_type, effective_on, revision)
            );
            ''')

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=10000')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        return db

    def _observe(self) -> str:
        instant = self.clock()
        if instant.tzinfo is None or instant.utcoffset() != timezone.utc.utcoffset(instant):
            raise HistoryError('Observation clock must be timezone-aware UTC')
        return _iso(instant)

    @staticmethod
    def _validate_identity(ins: Instrument, source: str, price_basis: str) -> None:
        if (ins.market not in ('US', 'IDX', 'CRYPTO') or not _ID.fullmatch(ins.instrument_id)
                or not ins.instrument_id.startswith(ins.market + ':')):
            raise HistoryError('Invalid instrument identity')
        if source not in _ALLOWED_SOURCES or not _SOURCE.fullmatch(source):
            raise HistoryError('Source must be an explicitly supported provider')
        if price_basis not in PRICE_BASES:
            raise HistoryError('Unsupported price basis')
        if source == 'SYNTHETIC_FIXTURE' and price_basis != 'SYNTHETIC':
            raise HistoryError('Synthetic fixtures may not be labeled as real prices')
        if source != 'SYNTHETIC_FIXTURE' and price_basis != 'VENDOR_UNVERIFIED':
            raise HistoryError('Provider prices cannot be self-certified as adjusted or raw')
        if source == 'YFINANCE_RESEARCH_RAW' and ins.market not in ('US', 'IDX'):
            raise HistoryError('Wrong provider for market')
        if source == 'BINANCE_SPOT_EOD' and ins.market != 'CRYPTO':
            raise HistoryError('Wrong provider for market')

    def ingest(self, ins: Instrument, bars: Sequence[Candle], *, source: str,
               price_basis: str, metadata: dict | None = None) -> dict:
        """Store a provider observation atomically; identical rows are idempotent.

        Corrected candles append a new revision, preserving historical versions.
        A backfilled candle is first observed NOW, not at its past close timestamp.
        """
        self._validate_identity(ins, source, price_basis)
        if not 1 <= len(bars) <= MAX_BATCH_BARS:
            raise HistoryError('Batch requires 1..2500 candles')
        try:
            validate_candles(bars)
        except (ValueError, TypeError) as exc:
            raise HistoryError(str(exc)) from exc
        observed_at = self._observe()
        session_dates = [_session(ins.market, b.at) for b in bars]
        if len(session_dates) != len(set(session_dates)):
            raise HistoryError('Duplicate market session within a batch')
        if any(_timestamp(b.at) > _timestamp(observed_at) for b in bars):
            raise HistoryError('Unfinished/future candle not archived as final')
        if metadata is not None:
            if not isinstance(metadata, dict) or len(_canonical(metadata)) > 4000:
                raise HistoryError('Provider metadata must be a small JSON object')
            allowed_metadata = {'capture_mode', 'timeframe', 'input_count', 'feed_category', 'provider_version'}
            if not set(metadata).issubset(allowed_metadata):
                raise HistoryError('Secret-like or unsupported provider metadata key rejected')
            if any(not isinstance(v, (str, int, bool)) for v in metadata.values()):
                raise HistoryError('Provider metadata must contain only scalar values')
        records = [asdict(b) for b in bars]
        manifest_hash = _digest({'instrument_id': ins.instrument_id, 'source': source,
                                 'price_basis': price_basis, 'records': records})
        batch_id = 'hist_' + uuid4().hex
        inserted = unchanged = corrected = 0
        previous: Candle | None = None
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''INSERT INTO history_batches
                (id,instrument_id,market,source,price_basis,recorded_at,first_bar,last_bar,
                 received,inserted,unchanged,corrected,manifest_hash,metadata_json)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 (batch_id, ins.instrument_id, ins.market, source, price_basis, observed_at,
                  bars[0].at, bars[-1].at, len(bars), 0, 0, 0, manifest_hash,
                  _canonical(metadata or {})))
            for bar, session_date, record in zip(bars, session_dates, records):
                payload = _canonical(record)
                content_hash = sha256(payload.encode('utf-8')).hexdigest()
                latest = db.execute('''SELECT revision,content_hash FROM history_candles
                    WHERE instrument_id=? AND source=? AND price_basis=? AND bar_at=?
                    ORDER BY revision DESC LIMIT 1''',
                    (ins.instrument_id, source, price_basis, bar.at)).fetchone()
                # A provider must not silently create two different close markers
                # for one exchange-local session. Such conflicts require review.
                collision = db.execute('''SELECT bar_at FROM history_candles
                    WHERE instrument_id=? AND source=? AND price_basis=? AND session_date=?
                    AND bar_at<>? LIMIT 1''',
                    (ins.instrument_id,source,price_basis,session_date,bar.at)).fetchone()
                if collision is not None:
                    raise HistoryError('Conflicting close marker for archived market session')
                if latest is not None and latest['content_hash'] == content_hash:
                    unchanged += 1
                    previous = bar
                    continue
                if latest is not None:
                    corrected += 1
                revision = (latest['revision'] + 1) if latest else 1
                flags = ['SYNTHETIC_NOT_MARKET_DATA'] if price_basis == 'SYNTHETIC' else [
                    'PRICE_BASIS_UNVERIFIED', 'CORPORATE_ACTIONS_UNVERIFIED',
                    'SESSION_CALENDAR_UNVERIFIED', 'BACKFILLED_FIRST_OBSERVED_NOW']
                if previous is not None:
                    gap = (date.fromisoformat(session_date) - date.fromisoformat(_session(ins.market, previous.at))).days
                    if gap > 7:
                        flags.append('LONG_GAP_REQUIRES_CALENDAR_REVIEW')
                    if ins.market != 'CRYPTO' and abs(bar.close / previous.close - 1) > .35:
                        flags.append('SPLIT_OR_OUTLIER_SUSPECTED')
                db.execute('''INSERT INTO history_candles
                    (instrument_id,market,source,price_basis,bar_at,session_date,revision,
                     first_observed_at,batch_id,payload_json,content_hash,flags_json)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (ins.instrument_id,ins.market,source,price_basis,bar.at,session_date,
                     revision,observed_at,batch_id,payload,content_hash,_canonical(flags)))
                inserted += 1
                previous = bar
            db.execute('''UPDATE history_batches SET inserted=?,unchanged=?,corrected=? WHERE id=?''',
                       (inserted, unchanged, corrected, batch_id))
        return {'batch_id': batch_id, 'instrument_id': ins.instrument_id,
                'source': source, 'price_basis': price_basis, 'first_observed_at': observed_at,
                'received': len(bars), 'inserted': inserted, 'unchanged': unchanged,
                'corrected': corrected, 'manifest_sha256': manifest_hash,
                'point_in_time_validated': False, 'execution_verified': False}

    def record_action(self, ins: Instrument, action: CorporateAction, *, source: str) -> dict:
        """Archive supplied event evidence; NEVER adjust candles automatically."""
        if ins.market not in ('US', 'IDX') or source != 'YFINANCE_RESEARCH_RAW':
            raise HistoryError('Corporate action source/market unsupported')
        self._validate_identity(ins, source, 'VENDOR_UNVERIFIED')
        _validate_action(action)
        observed = self._observe()
        if action.announced_at is not None and _timestamp(action.announced_at) > _timestamp(observed):
            raise HistoryError('Future corporate action announcement')
        evidence = asdict(action)
        content_hash = _digest(evidence)
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('''SELECT revision,content_hash FROM history_actions
                WHERE instrument_id=? AND source=? AND action_type=? AND effective_on=?
                ORDER BY revision DESC LIMIT 1''',
                (ins.instrument_id,source,action.action_type,action.effective_on)).fetchone()
            if latest is not None and latest['content_hash'] == content_hash:
                return {'status':'UNCHANGED','revision':latest['revision']}
            revision = latest['revision'] + 1 if latest else 1
            db.execute('''INSERT INTO history_actions VALUES(?,?,?,?,?,?,?,?)''',
                       (ins.instrument_id,source,action.action_type,action.effective_on,
                        revision,observed,_canonical(evidence),content_hash))
        return {'status':'RECORDED','revision':revision,'observed_at':observed}

    def actions(self, instrument_id: str, *, source: str, as_of: str | None = None) -> list[dict]:
        if not _ID.fullmatch(instrument_id) or source not in _ALLOWED_SOURCES:
            raise HistoryError('Invalid history lookup')
        cutoff = _timestamp(as_of) if as_of is not None else _timestamp(self._observe())
        with self._connect() as db:
            rows = db.execute('''WITH versions AS (
                SELECT action_type,effective_on,revision,first_observed_at,evidence_json,content_hash,
                       ROW_NUMBER() OVER (PARTITION BY action_type,effective_on
                                          ORDER BY revision DESC) AS rank
                FROM history_actions
                WHERE instrument_id=? AND source=? AND first_observed_at<=?
            ) SELECT action_type,effective_on,revision,first_observed_at,evidence_json,content_hash
              FROM versions WHERE rank=1 ORDER BY effective_on,action_type''',
              (instrument_id,source,_iso(cutoff))).fetchall()
        results = []
        for r in rows:
            if sha256(r['evidence_json'].encode('utf-8')).hexdigest() != r['content_hash']:
                raise HistoryError('Corporate action evidence checksum mismatch')
            results.append({'action_type':r['action_type'],'effective_on':r['effective_on'],
                            'revision':r['revision'],'first_observed_at':r['first_observed_at'],
                            'evidence':json.loads(r['evidence_json'])})
        return results

    def read(self, instrument_id: str, *, source: str, price_basis: str,
             as_of: str | None = None, limit: int = 2500) -> dict:
        """Reconstruct what had BEEN OBSERVED by as_of; not a true historical exchange PIT feed."""
        if not _ID.fullmatch(instrument_id) or source not in _ALLOWED_SOURCES or price_basis not in PRICE_BASES:
            raise HistoryError('Invalid history lookup identity/source/basis')
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=MAX_READ_BARS:
            raise HistoryError('Invalid read limit')
        cutoff = _timestamp(as_of) if as_of is not None else _timestamp(self._observe())
        with self._connect() as db:
            rows = db.execute('''WITH ranked AS (
                  SELECT bar_at,session_date,revision,first_observed_at,payload_json,
                         content_hash,flags_json,
                         ROW_NUMBER() OVER (PARTITION BY bar_at ORDER BY revision DESC) AS ranking
                  FROM history_candles
                  WHERE instrument_id=? AND source=? AND price_basis=? AND first_observed_at<=?
                ) SELECT * FROM ranked WHERE ranking=1 ORDER BY bar_at DESC LIMIT ?''',
                (instrument_id,source,price_basis,_iso(cutoff),limit)).fetchall()
        chosen = sorted(rows, key=lambda r:r['bar_at'])
        # Verify exact archived content on read, never silently use modified OHLC.
        if any(sha256(r['payload_json'].encode('utf-8')).hexdigest() != r['content_hash'] for r in chosen):
            raise HistoryError('Archive integrity check failed; candle checksum mismatch')
        seen_flags = sorted({flag for r in chosen for flag in json.loads(r['flags_json'])})
        return {'instrument_id':instrument_id,'source':source,'price_basis':price_basis,
                'as_of_observation':_iso(cutoff), 'rows':len(chosen),
                'first_bar':chosen[0]['bar_at'] if chosen else None,
                'last_bar':chosen[-1]['bar_at'] if chosen else None,
                'candles':[{'candle':json.loads(r['payload_json']),
                            'session_date':r['session_date'],
                            'revision':r['revision'],'first_observed_at':r['first_observed_at'],
                            'sha256':r['content_hash'], 'flags':json.loads(r['flags_json'])}
                           for r in chosen],
                'quality_flags':seen_flags,'calendar_validated':False,
                'corporate_actions_verified':False,'point_in_time_validated':False,
                'execution_verified':False,
                'note':'As-of means FIRST OBSERVED in this archive, not historically published market availability.'}

    def batches(self, *, limit: int = 50) -> list[dict]:
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=100:
            raise HistoryError('Invalid batch limit')
        with self._connect() as db:
            rows=db.execute('''SELECT * FROM history_batches ORDER BY recorded_at DESC,id DESC LIMIT ?''',
                            (limit,)).fetchall()
        return [{**dict(r), 'metadata':json.loads(r['metadata_json'])} for r in rows]
