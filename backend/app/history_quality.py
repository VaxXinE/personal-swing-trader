"""Fail-closed, provider-free audit of an immutable observed-candle snapshot.

All reports remain RESEARCH_ONLY. A user-provided session list is EVIDENCE, never
an official exchange-calendar certification. No network, shell or price rewrite.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

from .domain import Instrument, Candle, validate_candles
from .history import HistoryError, _session, _timestamp

MAX_CALENDAR_BYTES = 512 * 1024
MAX_CALENDAR_SESSIONS = 5000
MAX_FINDINGS = 100
_SOURCE_ZONES = {'US': 'America/New_York', 'IDX': 'Asia/Jakarta', 'CRYPTO': 'UTC'}


@dataclass(frozen=True)
class SessionCalendar:
    """Explicit observed provider-session evidence; NOT guaranteed to be correct."""
    market: str
    source: str
    observed_at: str
    coverage_start: date
    coverage_end: date
    sessions: tuple[date, ...]
    sha256: str


def _date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise HistoryError('Session date must be strict YYYY-MM-DD') from exc
    if not isinstance(value, str) or len(value) != 10 or value != parsed.isoformat():
        raise HistoryError('Session date must be strict YYYY-MM-DD')
    return parsed


def load_session_calendar(path: Path, market: str) -> SessionCalendar:
    """Read bounded JSON calendar evidence; never auto-download untrusted files."""
    if market not in ('US', 'IDX'):
        raise HistoryError('External session list is only supported for equities')
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_CALENDAR_BYTES:
        raise HistoryError('Session calendar missing or exceeds 512 KiB limit')
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError, OSError) as exc:
        raise HistoryError('Invalid session calendar JSON') from exc
    expected = {'market', 'source', 'observed_at', 'coverage_start', 'coverage_end', 'sessions'}
    if not isinstance(raw, dict) or set(raw) != expected or raw['market'] != market:
        raise HistoryError('Session calendar schema or market mismatch')
    source = raw['source']
    if not isinstance(source, str) or not 1 <= len(source) <= 100 or any(ord(c)<32 for c in source):
        raise HistoryError('Invalid calendar evidence source')
    _timestamp(raw['observed_at'])
    start, end = _date(raw['coverage_start']), _date(raw['coverage_end'])
    values = raw['sessions']
    if (start > end or not isinstance(values, list) or
            not 1 <= len(values) <= MAX_CALENDAR_SESSIONS):
        raise HistoryError('Invalid calendar coverage or session count')
    sessions = tuple(_date(s) for s in values)
    if list(sessions) != sorted(set(sessions)) or not all(start <= s <= end for s in sessions):
        raise HistoryError('Calendar sessions must be sorted, unique and covered')
    if any(s.weekday() >= 5 for s in sessions):
        raise HistoryError('Weekend equity sessions require separate reviewed special-session source')
    canonical = json.dumps(raw, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return SessionCalendar(market, source, raw['observed_at'], start, end, sessions, sha256(canonical).hexdigest())


def audit_snapshot(instrument: Instrument, snapshot: Mapping, *,
                   calendar: SessionCalendar | None = None,
                   actions: list[dict] | None = None,
                   reference: Mapping | None = None) -> dict:
    """Evaluate OHLC+session fidelity and external evidence, with no data mutation.

    Critical defects block archived replay. Missing official calendar/CA/PIT facts
    remain explicit research limitations, even if the structural audit passes.
    """
    market = instrument.market
    if market not in _SOURCE_ZONES or snapshot.get('instrument_id') != instrument.instrument_id:
        raise HistoryError('Snapshot instrument/market mismatch')
    records = snapshot.get('candles')
    if not isinstance(records, list) or len(records) > 2500:
        raise HistoryError('Snapshot requires at most 2500 archived candles')
    if calendar is not None and calendar.market != market:
        raise HistoryError('Calendar market mismatch')
    findings: list[dict] = []
    counts: dict[str, int] = {}
    has_blocker = False
    has_review = False

    def add(code: str, severity: str, session: str | None = None):
        nonlocal has_blocker, has_review
        counts[code] = counts.get(code, 0) + 1
        has_blocker = has_blocker or severity == 'BLOCK'
        has_review = has_review or severity == 'REVIEW'
        if len(findings) < MAX_FINDINGS:
            findings.append({'code': code, 'severity': severity, 'session_date': session})

    bars: list[Candle] = []
    seen_dates: set[date] = set()
    previous = None
    suspicious_sessions: set[date] = set()
    cutoff = _timestamp(snapshot['as_of_observation'])
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get('candle'), dict):
            raise HistoryError('Invalid snapshot observation row')
        try:
            bar = Candle(**row['candle'])
            stamp = _timestamp(bar.at)
            session_string = _session(market, bar.at)
            session = _date(session_string)
            declared = _date(row['session_date'])
            observed_at = _timestamp(row['first_observed_at'])
        except (ValueError, TypeError, KeyError) as exc:
            raise HistoryError('Malformed candle/session/observation metadata') from exc
        if observed_at > cutoff:
            add('OBSERVATION_AFTER_CUTOFF', 'BLOCK', session_string)
        if declared != session:
            add('SESSION_DATE_MISMATCH', 'BLOCK', session_string)
        if session in seen_dates:
            add('DUPLICATE_MARKET_SESSION', 'BLOCK', session_string)
        seen_dates.add(session)
        if market in ('US', 'IDX') and session.weekday() >= 5:
            add('WEEKEND_EQUITY_SESSION', 'BLOCK', session_string)
        if market == 'CRYPTO':
            # Binance daily close: 23:59:59.999 UTC; synthetic: 23:59:59 UTC.
            moment = stamp.timetz().replace(tzinfo=None)
            if not (moment.hour == 23 and moment.minute == 59 and moment.second == 59):
                add('CRYPTO_DAILY_CLOSE_MISMATCH', 'BLOCK', session_string)
        if bar.volume == 0:
            add('ZERO_BASE_VOLUME', 'REVIEW', session_string)
        if previous is not None:
            prev_bar, prev_session = previous
            gap = (session - prev_session).days
            if gap <= 0:
                add('OUT_OF_ORDER_SESSION', 'BLOCK', session_string)
            if market == 'CRYPTO' and gap > 1:
                add('MISSING_CRYPTO_DAILY_CANDLE', 'BLOCK', session_string)
            if market != 'CRYPTO' and gap > 7:
                add('LONG_GAP_REQUIRES_CALENDAR_REVIEW', 'BLOCK', session_string)
            if market != 'CRYPTO' and prev_bar.close > 0 and abs(bar.close / prev_bar.close - 1) > 0.35:
                add('SPLIT_OR_OUTLIER_SUSPECTED', 'BLOCK', session_string)
                suspicious_sessions.add(session)
        bars.append(bar)
        previous = (bar, session)
    try:
        validate_candles(bars)
    except (ValueError, TypeError) as exc:
        add('INVALID_OHLC_CHRONOLOGY', 'BLOCK')

    coverage = 'NOT_PROVIDED'
    calendar_details = None
    if market == 'CRYPTO':
        coverage = 'CONTINUOUS_UTC_RULE_ONLY'
    elif calendar is not None:
        coverage = 'PROVIDED_UNVERIFIED'
        calendar_details = {'source': calendar.source, 'observed_at': calendar.observed_at,
                            'sha256': calendar.sha256, 'coverage_start': calendar.coverage_start.isoformat(),
                            'coverage_end': calendar.coverage_end.isoformat()}
        if seen_dates:
            first, last = min(seen_dates), max(seen_dates)
            if first < calendar.coverage_start or last > calendar.coverage_end:
                add('CALENDAR_WINDOW_NOT_COVERED', 'REVIEW')
            else:
                expected = {d for d in calendar.sessions if first <= d <= last}
                for d in sorted(expected - seen_dates):
                    add('MISSING_DECLARED_SESSION', 'BLOCK', d.isoformat())
                for d in sorted(seen_dates - expected):
                    add('NOT_IN_DECLARED_SESSION_CALENDAR', 'BLOCK', d.isoformat())

    matching_evidence = 0
    if actions is not None:
        for record in actions:
            if not isinstance(record, dict) or not isinstance(record.get('evidence'), dict):
                raise HistoryError('Invalid corporate action evidence')
            data = record['evidence']
            if data.get('action_type') == 'SPLIT' and isinstance(data.get('effective_on'), str):
                action_date = _date(data['effective_on'])
                if any(abs((action_date - session).days) <= 2 for session in suspicious_sessions):
                    matching_evidence += 1
        if matching_evidence:
            add('SPLIT_EVIDENCE_UNVERIFIED', 'REVIEW')

    reference_details = None
    if reference is not None:
        if (reference.get('instrument_id') != instrument.instrument_id or
                reference.get('price_basis') != snapshot.get('price_basis') or
                reference.get('source') == snapshot.get('source')):
            raise HistoryError('Independent reference must match instrument and price basis but have different source')
        if reference.get('currency') is not None and reference['currency'] != instrument.currency:
            raise HistoryError('Reference currency mismatch; provide explicit as-of FX conversion')
        ref_rows = reference.get('candles')
        if not isinstance(ref_rows, list) or len(ref_rows)>2500:
            raise HistoryError('Invalid independent reference rows')
        mapped = {r['session_date']: r['candle']['close'] for r in ref_rows}
        compared = 0
        for row in records:
            key = row['session_date']
            if key not in mapped:
                continue
            left = row['candle']['close']
            right = mapped[key]
            if not all(isinstance(v, (int, float)) and isfinite(v) and v > 0 for v in (left,right)):
                add('INVALID_REFERENCE_CLOSE', 'BLOCK', key)
                continue
            compared += 1
            if abs(left / right - 1) > 0.02:
                add('INDEPENDENT_SOURCE_PRICE_CONFLICT', 'BLOCK', key)
        reference_details = {'source': reference['source'], 'overlap_sessions': compared,
                             'independent_source_verified': False}
        if compared == 0:
            add('REFERENCE_HAS_NO_OVERLAP', 'REVIEW')

    return {'status': 'BLOCKED' if has_blocker else 'REVIEW_REQUIRED' if has_review else 'STRUCTURAL_PASS',
            'research_only': True, 'execution_verified': False, 'point_in_time_validated': False,
            'corporate_actions_verified': False, 'calendar_validated': False,
            'instrument_id': instrument.instrument_id, 'price_basis': snapshot.get('price_basis'),
            'source': snapshot.get('source'), 'rows': len(records),
            'calendar_coverage': coverage, 'calendar_evidence': calendar_details,
            'split_evidence_matches': matching_evidence,
            'reference_comparison': reference_details,
            'finding_counts': dict(sorted(counts.items())), 'findings': findings,
            'findings_truncated': sum(counts.values())>len(findings),
            'limitations': ['Calendar input is evidence, not official certification',
                            'Corporate actions are not automatically adjusted or verified',
                            'Backfilled first-observed timestamps are not market publication timestamps',
                            'No complete historical/delisted universe or trading execution verification']}
