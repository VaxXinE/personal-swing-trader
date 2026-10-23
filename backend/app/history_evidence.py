"""Bounded, offline evidence import for comparing archived research prices.

A second file is not proof of an independent vendor or original publication time.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import isfinite
import json
from pathlib import Path
import re

from .history import HistoryError, _timestamp, _canonical

MAX_REFERENCE_BYTES = 512 * 1024
_SOURCE_NAME = re.compile(r'[A-Z][A-Z0-9_]{2,63}\Z')
_INSTRUMENT_ID = re.compile(r'(?:US|IDX|CRYPTO):[A-Z0-9_-]{2,30}:[A-Z0-9.-]{1,30}\Z')


def _date_text(value: object) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise HistoryError('Reference session must be YYYY-MM-DD') from exc
    if not isinstance(value, str) or value != parsed.isoformat():
        raise HistoryError('Reference session must be YYYY-MM-DD')
    return value


def load_close_reference(path: Path) -> dict:
    """Load user-selected evidence; never fetch URLs or infer a verified price basis."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_REFERENCE_BYTES:
        raise HistoryError('Reference file missing or exceeds 512 KiB')
    def reject_nonfinite(_value):
        raise ValueError('Nonfinite JSON number')

    try:
        raw = json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_nonfinite)
    except (ValueError, UnicodeError, OSError) as exc:
        raise HistoryError('Invalid reference JSON') from exc
    keys = {'instrument_id', 'source', 'price_basis', 'currency', 'observed_at', 'candles'}
    if not isinstance(raw, dict) or set(raw) != keys:
        raise HistoryError('Reference evidence schema mismatch')
    if not isinstance(raw['instrument_id'], str) or not _INSTRUMENT_ID.fullmatch(raw['instrument_id']):
        raise HistoryError('Invalid reference instrument ID')
    if not isinstance(raw['source'], str) or not _SOURCE_NAME.fullmatch(raw['source']):
        raise HistoryError('Invalid reference source label')
    if raw['price_basis'] not in ('SYNTHETIC', 'VENDOR_UNVERIFIED'):
        raise HistoryError('Reference basis must be explicitly unverified or synthetic')
    if not isinstance(raw['currency'], str) or not re.fullmatch(r'[A-Z]{3,5}', raw['currency']):
        raise HistoryError('Invalid reference currency')
    _timestamp(raw['observed_at'])
    observations = raw['candles']
    if not isinstance(observations, list) or not 1 <= len(observations) <= 2500:
        raise HistoryError('Reference requires 1..2500 close observations')
    rows = []
    prior = ''
    for item in observations:
        if not isinstance(item, dict) or set(item) != {'session_date', 'close'}:
            raise HistoryError('Invalid reference candle shape')
        session = _date_text(item['session_date'])
        if session <= prior:
            raise HistoryError('Reference sessions must be strictly increasing')
        prior = session
        price = item['close']
        if not isinstance(price, str) or len(price) > 40:
            raise HistoryError('Reference close must be a positive decimal string')
        try:
            number = Decimal(price)
        except InvalidOperation as exc:
            raise HistoryError('Invalid reference close') from exc
        if not number.is_finite() or number <= 0:
            raise HistoryError('Reference close must be positive and finite')
        converted = float(number)
        if not isfinite(converted) or converted <= 0:
            raise HistoryError('Reference close outside supported numeric range')
        rows.append({'session_date': session, 'candle': {'close': converted}})
    return {**{key: raw[key] for key in keys - {'candles'}}, 'candles': rows,
            'sha256': sha256(_canonical(raw).encode('utf-8')).hexdigest(),
            'independent_source_verified': False}
