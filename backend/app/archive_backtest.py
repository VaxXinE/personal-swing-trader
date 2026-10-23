"""Research-only backtest on an explicitly selected, previously archived candle snapshot.

NEVER calls a provider or starts a subprocess. This archive stores the timestamp
when *we observed* candles, not their first market availability or certified RAW
execution prices. The existing replay logic and strategy criteria are unchanged.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re

from .backtest import MIN_WARMUP, replay
from .domain import Candle, Instrument
from .history import HistoryError, HistoryStore
from .history_quality import audit_snapshot
from .universe_history import UniverseHistory


class SnapshotMismatch(HistoryError):
    """Optimistic snapshot fingerprint check failed: do not return a changed replay."""


class ArchiveNotFound(HistoryError):
    """No observed archive candles for the requested identity and source."""


_BLOCKING_FLAGS = frozenset({
    'SPLIT_OR_OUTLIER_SUSPECTED',
    'LONG_GAP_REQUIRES_CALENDAR_REVIEW',
})
_ALLOWED_FLAGS = frozenset({
    'SYNTHETIC_NOT_MARKET_DATA', 'PRICE_BASIS_UNVERIFIED',
    'CORPORATE_ACTIONS_UNVERIFIED', 'SESSION_CALENDAR_UNVERIFIED',
    'BACKFILLED_FIRST_OBSERVED_NOW',
})
_HASH = re.compile(r'[0-9a-f]{64}\Z')


def replay_from_archive(
    store: HistoryStore,
    instrument: Instrument,
    *,
    mode: str,
    source: str,
    price_basis: str,
    strategy: str = 'PULLBACK',
    horizon: int = 10,
    as_of: str | None = None,
    limit: int = 2500,
    expected_snapshot_sha256: str | None = None,
    expected_universe_evidence_sha256: str | None = None,
) -> dict:
    """Replay a bounded archive snapshot; never silently switch to live prices.

    `as_of` describes the time of *first observation by our software*.
    For stable replays, reuse the returned cutoff and fingerprint on future calls.
    """
    if mode not in ('demo', 'live'):
        raise HistoryError('Invalid research mode')
    if strategy not in ('PULLBACK', 'BREAKOUT'):
        raise HistoryError('Unsupported strategy')
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 2 <= horizon <= 20:
        raise HistoryError('Horizon must be 2..20')
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 2500:
        raise HistoryError('Invalid archive limit')
    if expected_snapshot_sha256 is not None and not _HASH.fullmatch(expected_snapshot_sha256):
        raise HistoryError('Snapshot fingerprint must be 64 lowercase hex characters')
    if expected_universe_evidence_sha256 is not None and not _HASH.fullmatch(expected_universe_evidence_sha256):
        raise HistoryError('Universe fingerprint must be 64 lowercase hex characters')

    expected_source = 'SYNTHETIC_FIXTURE' if mode == 'demo' else (
        'BINANCE_SPOT_EOD' if instrument.market == 'CRYPTO' else 'YFINANCE_RESEARCH_RAW')
    expected_basis = 'SYNTHETIC' if mode == 'demo' else 'VENDOR_UNVERIFIED'
    if (source, price_basis) != (expected_source, expected_basis):
        raise HistoryError('Source and price basis must match active data mode and instrument market')

    snapshot = store.read(
        instrument.instrument_id, source=source, price_basis=price_basis,
        as_of=as_of, limit=limit,
    )
    if not snapshot['rows']:
        raise ArchiveNotFound('No archived observations match the selected source and cutoff')

    # Fingerprint includes every candle revision, content hash, observation time,
    # and market identity. The archive validates underlying SHA-256 on each read.
    evidence = {
        'instrument_id': instrument.instrument_id,
        'source': source,
        'price_basis': price_basis,
        'candles': [
            {'at': row['candle']['at'], 'revision': row['revision'],
             'sha256': row['sha256'], 'first_observed_at': row['first_observed_at']}
            for row in snapshot['candles']
        ],
    }
    fingerprint = sha256(json.dumps(
        evidence, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
    ).encode('utf-8')).hexdigest()
    if expected_snapshot_sha256 is not None and fingerprint != expected_snapshot_sha256:
        raise SnapshotMismatch('Archived candle snapshot differs from expected fingerprint')

    quality = audit_snapshot(instrument, snapshot,
                             actions=store.actions(instrument.instrument_id, source=source,
                                                   as_of=snapshot['as_of_observation']))
    if quality['status'] == 'BLOCKED':
        raise HistoryError('Archive quality requires manual review: ' + ', '.join(
            code for code, count in quality['finding_counts'].items() if count))

    flags = set(snapshot['quality_flags'])
    # Independently check adjacent archived rows. The current archive's per-row
    # checksum covers payload_json, not flags_json or market session metadata;
    # therefore metadata flags alone are NOT a sufficient quality gate.
    for prev, current in zip(snapshot['candles'], snapshot['candles'][1:]):
        days = (date.fromisoformat(current['session_date']) -
                date.fromisoformat(prev['session_date'])).days
        if days > 7:
            flags.add('LONG_GAP_REQUIRES_CALENDAR_REVIEW')
        if instrument.market != 'CRYPTO':
            prior_close = prev['candle']['close']
            if prior_close <= 0 or abs(current['candle']['close'] / prior_close - 1) > .35:
                flags.add('SPLIT_OR_OUTLIER_SUSPECTED')
    blocked = sorted(flags & _BLOCKING_FLAGS)
    unexpected = sorted(flags - _BLOCKING_FLAGS - _ALLOWED_FLAGS)
    if blocked or unexpected:
        raise HistoryError('Archive quality requires manual review: ' + ', '.join(blocked + unexpected))

    if snapshot['rows'] < MIN_WARMUP + horizon + 1:
        raise HistoryError(f'Insufficient archived candles: need at least {MIN_WARMUP + horizon + 1}')

    bars = [Candle(**row['candle']) for row in snapshot['candles']]
    universe_evidence = UniverseHistory(store.path).report(
        instrument, bars, mode=mode, as_of=snapshot['as_of_observation'])
    if (expected_universe_evidence_sha256 is not None and
            expected_universe_evidence_sha256 != universe_evidence['evidence_sha256']):
        raise SnapshotMismatch('Archived universe evidence differs from expected fingerprint')
    result = replay(instrument, bars, strategy=strategy, horizon=horizon)
    result['archive_snapshot'] = {
        'source': source, 'price_basis': price_basis,
        'quality_report': quality,
        'universe_evidence': universe_evidence,
        'as_of_observation': snapshot['as_of_observation'],
        'sha256': fingerprint,
        'rows': snapshot['rows'],
        'first_bar': snapshot['first_bar'], 'last_bar': snapshot['last_bar'],
        'quality_flags': sorted(flags),
        'window_may_be_truncated': snapshot['rows'] == limit,
        'point_in_time_validated': False,
        'calendar_validated': False,
        'corporate_actions_verified': False,
        'execution_verified': False,
        'note': 'Snapshot as_of is first-observed by this archive, NOT original historical market availability. Provider price basis remains unverified.',
    }
    result['validated'] = False
    result['status'] = 'RESEARCH_ONLY'
    return result
