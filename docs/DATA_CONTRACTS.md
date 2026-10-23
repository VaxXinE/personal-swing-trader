# DATA_CONTRACTS — Canonical Market Data and Point-in-Time Rules

**Status:** LOCKED invariants and versioning; concrete storage format subject to implementation tests.

## 1. Instrument identity

`instrument_id` **immutable ID in internal registry**, not ticker string. Example aliases: `US:NASDAQ:MSFT`, `ID:IDX:BBCA`, `CRYPTO:BINANCE:BTCUSDT`. Registry may use UUID plus human-readable canonical key; preserve `symbol_aliases(valid_from,valid_to,provider)`. Exchange/venue + currency + asset_type + quote currency required. Symbol collisions must be impossible.

Asset type: `US_COMMON`, `US_ADR`, `US_ETF`, `IDX_EQUITY`, `CRYPTO_SPOT`. ETF P1 requires its own analytic logic, not corporate EPS scoring.

## 2. Canonical candle

| Field | Type | Rule |
|---|---|---|
| `instrument_id` | string | registry key |
| `timeframe` | enum | `1d`, `4h`, `1h` initially |
| `open_at`, `close_at` | UTC ISO8601 | fixed `[open_at,close_at)` interval; `close_at` boundary exclusive |
| `session_date` | market-local date | exchange-calendar session (crypto daily UTC) |
| `open, high, low, close` | numeric | positive, same price basis, currency explicit |
| `base_volume` | numeric | nonnegative in units of base instrument |
| `quote_volume`/`traded_value` | numeric nullable | turnover in quote currency, *not* quantity |
| `price_basis` | enum | `RAW`, `SPLIT_ADJUSTED`, `TOTAL_RETURN_ADJUSTED` |
| `is_final` | boolean | false bars excluded from EOD features/signals |
| `source`, `source_record_id` | text | lineage |
| `event_at`, `available_at`, `ingested_at` | UTC | event, earliest availability, received time distinguished |
| `quality` | enum | `VALID`, `SUSPECT`, `STALE`, `INVALID`, `UNKNOWN` |
| `revision`, `content_hash` | metadata | corrections append/version, no silent rewrite |

OHLC invariants: `high >= max(open,close)`, `low <= min(open,close)`, `low <= high`, all finite, positive where instrument >0; volume >=0. Reject overlapping/duplicate `(instrument,timeframe,open_at,price_basis,revision)` in published snapshot. Trading calendar governs missing sessions; a holiday is **not** a missing candle. Suspensions/halts are instrument events.

**Raw vs adjusted:** technical research may use split-adjusted series for comparability, but entry/stop/target and tick validation refer to **actual tradable RAW price** at event time. Dividends/splits/rights and exchange mechanics must be applied consistently; do not mix adjustment basis. Corporate action history has publication and ex/effective dates.

## 3. Quote

```json
{
  "instrument_id": "CRYPTO:BINANCE:BTCUSDT",
  "bid": "65000.10",
  "ask": "65001.30",
  "last": "65000.80",
  "currency": "USDT",
  "feed_type": "REALTIME",
  "event_at": "2026-10-23T12:00:00Z",
  "received_at": "2026-10-23T12:00:01Z",
  "source": "binance-public",
  "quality": "VALID"
}
```

Numbers in JSON as decimal **strings** for money/executable levels; parser uses `Decimal`. Example illustrative and non-current.

Freshness uses `now - event_at` alongside feed entitlement, market trading session and configured thresholds. If bid or ask missing, spread is `UNKNOWN` rather than guessed. Don't infer a venue-wide real-time claim from a local timestamp alone.

## 4. Event & fundamentals

Represent events with **both** `economic_period_end` and `published_at/available_at`. Earnings for fiscal quarter Q2 cannot enter a backtest before actual release time. Source URL, version, revision, currency, unit, filed/accepted timestamps and normalizer rules stored. News may be corrected or retracted; attach status and original revision.

## 5. Time and calendar

- Compute/storage: UTC. UI: Asia/Jakarta as default device preference; show exchange-local session where relevant.
- US market sessions in `America/New_York` with DST, official holidays and half-days.
- IDX calendar in `Asia/Jakarta`, exchange holidays and special sessions; load current calendar and archive versions.
- Crypto canonical daily candles **UTC midnight boundary**; explicitly distinguish exchange UTC+8 variants and reject mixed candle conventions.
- `available_at <= scan_evaluated_at` for any feature included; finalized bars only. A scan scheduled 'after market close' also waits for source delivery + finality buffer.

## 6. Data quality flags

`MISSING_BAR`, `DUPLICATE_BAR`, `OUT_OF_ORDER`, `BAD_OHLC`, `NONFINITE`, `CURRENCY_MISMATCH`, `BASIS_MISMATCH`, `STALE_QUOTE`, `INCOMPLETE_CANDLE`, `SPLIT_SUSPECTED`, `SOURCE_CONFLICT`, `UNKNOWN_SESSION`, `UNSUPPORTED_MARKET_RULE`.

Severity: reject invalid bars; quarantine suspicious until resolved; show user warnings for degraded coverage; no execution-ready result from required unknown data.

## 7. Partition and retention

Parquet suggested layout `data/market/<provider>/<asset_type>/<timeframe>/year=YYYY/...parquet`; partition by date/market to avoid small-files explosion. Raw immutable provider exports separated from canonical curated data; materialized snapshot manifest includes checksum, row count, min/max timestamp, schema version. Back up SQLite and manifests/Parquet consistently. No price series tracked in git.

## 8. Contract tests

- Verify BBRI.JK and another `.JK` ticker map to IDX symbols without collision.
- Split event doesn't create fake 50% drawdown in adjusted research or wrong trade-level fill in raw mode.
- Mixed USD/IDR/USDT comparisons require explicit conversions + FX as-of, otherwise forbid arithmetic.
- Crypto interim kline (`x=false`) cannot trigger daily signal.
- US Thanksgiving/half-day and IDX holiday do not generate false gap repair.
- Provider correction increments revision, old signal still reproducible from its snapshot.


## Implementation mapping (2026-10-23)

Historical Data Engine v1 now implements the **observation archive** subset in `backend/app/history.py` (see [HISTORICAL_DATA_ENGINE](HISTORICAL_DATA_ENGINE.md)). Original provider and adjustment-time facts that predate the first archive observation **remain unknown**; the new API never returns them as certified. The full contract above (exchange calendars, corrected raw/adjusted series, source-time point-in-time facts, delisted historical universe and snapshot calibration) is still incomplete, and the archive must not be used to assert a validated OOS strategy.


## Research quality-gate implementation (2026-10-23)

`backend/app/history_quality.py` provides a provider-free snapshot QC layer for TSK-007/008/012 partial: candle/session metadata consistency, chronological crypto completeness, preliminary equity weekday guard, suspicious price moves, optional manually provided session lists, and optional source-comparison evidence. Its `STRUCTURAL_PASS` status is **not** the same as `calendar_validated=true`. Until an authoritative, archived, reviewed trading calendar and corporate-action/RAW-price history are integrated, quality remains research-only; missing equity sessions cannot be inferred from weekdays alone. See [HISTORY_QUALITY](HISTORY_QUALITY.md).
