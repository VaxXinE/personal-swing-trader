"""Bounded, explicit discovery for a *candidate* universe (never an approved trading list).

US: Nasdaq Trader directory (listings, NOT liquidity). Crypto: Binance active spot
pairs prioritized by rolling 24h quote turnover (NOT ADV20). IDX: user-imported
IDX CSV (no undocumented exchange scraping). Actual liquid status is derived
only after final historical candles are scanned by the existing domain engine.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .domain import Instrument

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / 'data' / 'discovered_universe.json'
DIRECTORIES = {
    'nasdaq': 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt',
    'other': 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt',
}
BINANCE = 'https://data-api.binance.vision'
SYMBOL_RE = re.compile(r'[A-Z0-9][A-Z0-9.-]{0,18}\Z')
IDX_RE = re.compile(r'[A-Z]{4}\Z')
EXCLUDED_BASES = {'USDT', 'USDC', 'BUSD', 'TUSD', 'FDUSD', 'DAI', 'USDP', 'PAX', 'EUR', 'USD', 'TRY'}
EXCLUDED_SUFFIXES = ('UP', 'DOWN', 'BULL', 'BEAR', '3L', '3S', '5L', '5S')
BAD_NAMES = re.compile(r'\b(warrants?|rights?|preferred|depositary shares?|units?|notes?|bonds?|etf|exchange.traded|closed.end fund|acquisition rights)\b', re.I)

class DiscoveryError(ValueError):
    pass


def _safe_name(value: object) -> str:
    return ''.join(ch for ch in str(value) if ch.isprintable()).strip()[:130]


def _instrument(market: str, symbol: str, name: str, venue: str,
                provider: str | None = None) -> Instrument:
    if not SYMBOL_RE.fullmatch(symbol):
        raise DiscoveryError('Invalid symbol')
    return Instrument(f'{market}:{venue}:{symbol}', symbol, _safe_name(name) or symbol,
                      market, venue, {'US':'USD', 'IDX':'IDR', 'CRYPTO':'USDT'}[market],
                      provider or symbol, 'SPOT' if market == 'CRYPTO' else 'EQUITY')


def _rows_from_directory(text: str, *, other: bool) -> list[Instrument]:
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')), delimiter='|')
    needed = {'ETF', 'Test Issue'} | ({'ACT Symbol', 'Exchange', 'Security Name'} if other else {'Symbol', 'Security Name'})
    if not reader.fieldnames or not needed.issubset(set(reader.fieldnames)):
        raise DiscoveryError('Nasdaq directory format changed; refusing unverified parse')
    found: dict[str, Instrument] = {}
    for row in reader:
        symbol = (row.get('ACT Symbol' if other else 'Symbol') or '').strip().upper()
        name = _safe_name(row.get('Security Name') or '')
        if not SYMBOL_RE.fullmatch(symbol) or not name:
            continue
        if row.get('ETF', '').strip() != 'N' or row.get('Test Issue', '').strip() != 'N':
            continue
        if row.get('Financial Status', 'N').strip() not in ('', 'N') or BAD_NAMES.search(name):
            continue
        if other:
            exchange = (row.get('Exchange') or '').strip()
            if exchange not in ('N', 'A'):
                continue
            venue = {'N': 'NYSE', 'A': 'NYSEAMERICAN'}[exchange]
        else:
            venue = 'NASDAQ'
        try:
            # Yahoo normally represents US class shares with '-'; retain symbol for UI.
            ticker = symbol.replace('.', '-')
            found[symbol] = _instrument('US', symbol, name, venue, ticker)
        except DiscoveryError:
            pass
    if not found:
        raise DiscoveryError('Nasdaq directory returned zero valid equity listings')
    return list(found.values())


def discover_us(client: httpx.Client, limit: int, cycle: str) -> tuple[list[Instrument], int]:
    symbols: dict[str, Instrument] = {}
    for label, url in DIRECTORIES.items():
        response = client.get(url)
        response.raise_for_status()
        for instrument in _rows_from_directory(response.text, other=label == 'other'):
            symbols.setdefault(instrument.symbol, instrument)
    # No turnover in these files. Cycle-stable hash rotation samples the directory
    # fairly; NEVER label this shortlist as liquid before OHLCV verification.
    pool = sorted(symbols.values(), key=lambda x: (hashlib.sha256(f'{cycle}:{x.instrument_id}'.encode()).hexdigest(), x.symbol))
    return pool[:limit], len(symbols)


def discover_crypto(client: httpx.Client, limit: int, minimum_quote_volume: float = 10_000_000) -> tuple[list[Instrument], int]:
    info = client.get(BINANCE + '/api/v3/exchangeInfo')
    info.raise_for_status()
    tickers = client.get(BINANCE + '/api/v3/ticker/24hr')
    tickers.raise_for_status()
    all_tickers = tickers.json()
    data = info.json()
    if not isinstance(data, dict) or not isinstance(data.get('symbols'), list) or not isinstance(all_tickers, list):
        raise DiscoveryError('Binance response schema changed')
    # 24-hour rolling turnover is *candidate prescreen only*, not ADV20.
    volumes: dict[str, float] = {}
    for row in all_tickers:
        try:
            value = float(row['quoteVolume'])
            if 0 <= value < float('inf'):
                volumes[str(row['symbol'])] = value
        except (ValueError, TypeError, KeyError):
            continue
    ranked: list[tuple[float, Instrument]] = []
    total_active = 0
    for row in data['symbols']:
        if not isinstance(row, dict):
            continue
        base = row.get('baseAsset', '')
        symbol = row.get('symbol', '')
        if (row.get('status') != 'TRADING' or row.get('isSpotTradingAllowed') is not True
                or row.get('quoteAsset') != 'USDT' or base in EXCLUDED_BASES
                or any(base.endswith(sfx) for sfx in EXCLUDED_SUFFIXES)
                or not SYMBOL_RE.fullmatch(symbol)):
            continue
        total_active += 1
        quote_volume = volumes.get(symbol)
        if quote_volume is None or quote_volume < minimum_quote_volume:
            continue
        ins = _instrument('CRYPTO', symbol, f'{base} / USDT', 'BINANCE')
        ranked.append((quote_volume, ins))
    if not volumes or not total_active:
        raise DiscoveryError('Binance returned no usable spot market universe')
    ranked.sort(key=lambda it: (-it[0], it[1].symbol))
    return [r[1] for r in ranked[:limit]], total_active


def _idx_columns(header: list[str]) -> tuple[int, int, int | None] | None:
    """Resolve column positions in an IDX official listing or user CSV export."""
    keys = {' '.join(str(item).strip().casefold().replace('_', ' ').split()): index
            for index, item in enumerate(header)}
    code = next((keys[k] for k in ('kode', 'kode saham', 'code', 'symbol', 'ticker', 'stock code') if k in keys), None)
    name = next((keys[k] for k in ('nama perusahaan', 'nama emiten', 'nama', 'name', 'company name',
                                  'company', 'company name (id)') if k in keys), None)
    board = next((keys[k] for k in ('papan pencatatan', 'papan', 'board', 'listing board') if k in keys), None)
    if code is None or name is None:
        return None
    return code, name, board


def _parse_idx_table(rows: list[list[str]]) -> list[Instrument]:
    """Find a valid IDX header within the first 40 rows and read subsequent entries."""
    fields = None
    start = 0
    for index, row in enumerate(rows[:40]):
        fields = _idx_columns(row)
        if fields is not None:
            start = index + 1
            break
    if fields is None:
        return []
    code_col, name_col, board_col = fields
    found: dict[str, Instrument] = {}
    for row in rows[start:]:
        code = row[code_col].strip().upper() if len(row) > code_col else ''
        name = row[name_col].strip() if len(row) > name_col else ''
        if not IDX_RE.fullmatch(code) or not name:
            continue
        if board_col is not None and len(row) > board_col and 'pemantauan khusus' in row[board_col].casefold():
            continue
        found[code] = _instrument('IDX', code, name, 'IDX', code + '.JK')
    return list(found.values())


def discover_idx_file(path: Path, limit: int) -> tuple[list[Instrument], int]:
    """Import IDX listing directly from official XLSX or optional CSV, without changing the input."""
    if not path.is_file():
        raise DiscoveryError('IDX listing file not found')
    suffix = path.suffix.lower()
    if suffix == '.xlsx':
        from .xlsx_rows import read_xlsx_tables, WorkbookFormatError
        try:
            tables = read_xlsx_tables(path)
        except WorkbookFormatError as exc:
            raise DiscoveryError(f'IDX XLSX could not be read: {exc}') from exc
    elif suffix == '.csv':
        if path.stat().st_size > 4_000_000:
            raise DiscoveryError('IDX CSV exceeds maximum allowed 4 MB')
        try:
            raw = path.read_text(encoding='utf-8-sig')
        except UnicodeError as exc:
            raise DiscoveryError('IDX CSV must be UTF-8') from exc
        try:
            dialect = csv.Sniffer().sniff(raw[:4096], delimiters=',;\t')
        except csv.Error:
            raise DiscoveryError('IDX CSV requires comma, semicolon or tab delimiter') from None
        tables = [list(csv.reader(io.StringIO(raw), dialect=dialect))]
    else:
        raise DiscoveryError('Unsupported IDX file; use .xlsx or .csv (not .xls or .xlsm)')
    # One workbook can contain explanatory/empty tabs. Choose the tab with the
    # highest number of valid IDX symbols, not the first arbitrary worksheet.
    candidates = [_parse_idx_table(rows) for rows in tables]
    pool = max(candidates, key=len, default=[])
    if not pool:
        raise DiscoveryError('IDX file must contain Kode and Nama Perusahaan columns with valid stock rows')
    symbols = sorted(pool, key=lambda x: x.symbol)
    return symbols[:limit], len(symbols)


def discover_idx_csv(path: Path, limit: int) -> tuple[list[Instrument], int]:
    """Backward-compatible CSV helper; new integrations should call discover_idx_file."""
    if path.suffix.lower() != '.csv':
        raise DiscoveryError('IDX CSV helper requires a .csv file')
    return discover_idx_file(path, limit)


def _read_snapshot(path: Path = SNAPSHOT_PATH) -> dict:
    if not path.exists():
        return {'version': 1, 'generated_at': None, 'markets': {}, 'instruments': []}
    if path.stat().st_size > 1_000_000:
        raise DiscoveryError('Universe snapshot exceeds 1MB, refusing')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload.get('version') != 1 or not isinstance(payload.get('instruments'), list) or not isinstance(payload.get('markets'), dict):
            raise DiscoveryError('Malformed discovered universe snapshot')
        return payload
    except (OSError, json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise DiscoveryError('Cannot parse discovered universe snapshot') from exc


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix='.universe-', delete=False) as fp:
            temp = Path(fp.name)
            json.dump(payload, fp, ensure_ascii=False, indent=2)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def sync_discovery(markets: list[str], *, us_limit: int = 24,
                   crypto_limit: int = 18, idx_limit: int = 35,
                   idx_csv: Path | None = None, idx_file: Path | None = None,
                   path: Path = SNAPSHOT_PATH,
                   client: httpx.Client | None = None) -> dict:
    """Refresh only requested markets. Preserve their last successful results on failure.

    Never uses user-provided URL. Deliberately CLI-only to avoid an unauthenticated
    expensive network sync through a browser endpoint.
    """
    if not markets or len(set(markets)) != len(markets) or any(x not in ('US','IDX','CRYPTO') for x in markets):
        raise DiscoveryError('Markets must be a nonempty unique subset of US, IDX, CRYPTO')
    if not all(1 <= x <= 75 for x in (us_limit, crypto_limit, idx_limit)):
        raise DiscoveryError('Each market candidate cap must be between 1 and 75')
    original = _read_snapshot(path)
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    by_market: dict[str, list[dict[str, Any]]] = {'US': [], 'IDX': [], 'CRYPTO': []}
    for item in original['instruments']:
        if isinstance(item, dict) and item.get('market') in by_market:
            by_market[item['market']].append(item)
    reports = dict(original['markets'])
    errors = []
    owned_client = client is None
    if owned_client:
        client = httpx.Client(timeout=18, follow_redirects=True,
                              headers={'User-Agent': 'PersonalSwingIntelligence/0.2 (private research)'})
    try:
        for market in markets:
            try:
                if market == 'US':
                    found, total = discover_us(client, us_limit, now[:7])
                    source = 'NASDAQ_TRADER_SYMBOL_DIRECTORY'
                    note = 'Directory sample rotated by month; liquidity not established until daily candles are screened'
                elif market == 'CRYPTO':
                    found, total = discover_crypto(client, crypto_limit)
                    source = 'BINANCE_EXCHANGEINFO_24HR'
                    note = 'Ranked on rolling 24h quote volume; not 20-session ADV'
                else:
                    if idx_csv is not None and idx_file is not None:
                        raise DiscoveryError('Choose only one IDX input file')
                    file = idx_file or idx_csv
                    if file is None:
                        raise DiscoveryError('IDX requires --idx-file /path/to/official-list.xlsx (or .csv)')
                    found, total = discover_idx_file(file, idx_limit)
                    source = 'IDX_USER_IMPORTED_XLSX' if file.suffix.lower() == '.xlsx' else 'IDX_USER_IMPORTED_CSV'
                    note = 'User-imported listing; board/status depends on file date; suspensions not independently verified'
                by_market[market] = [dict(vars(x)) for x in found]
                reports[market] = {'source': source, 'discovered': total, 'selected': len(found),
                                   'synced_at': now, 'note': note}
            except (DiscoveryError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                errors.append({'market': market, 'error': f'{type(exc).__name__}: {str(exc)[:180]}'})
    finally:
        if owned_client:
            client.close()
    if len(errors) != len(markets):
        snapshot = {'version': 1, 'generated_at': now, 'markets': reports,
                    'instruments': sum((by_market[m] for m in ('US', 'IDX', 'CRYPTO')), [])}
        _atomic_write(path, snapshot)
    return {'synced_at': now, 'markets': reports, 'errors': errors,
            'snapshot_updated': len(errors) != len(markets),
            'selected_total': sum(len(x) for x in by_market.values()),
            'snapshot_path': str(path)}


def snapshot_metadata(path: Path = SNAPSHOT_PATH) -> dict:
    snap = _read_snapshot(path)
    return {'generated_at': snap['generated_at'], 'markets': snap['markets'],
            'discovered_candidate_count': len(snap['instruments']),
            'manual_baseline': 'config/universe.json',
            'disclaimer': 'Discovery candidates are not liquid/verified until historical scanning; no execution verification.'}
