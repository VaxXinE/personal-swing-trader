# Historical Data Engine v1 — immutable observations (research-only)

**Task / scope:** HIST-01, HIST-02, HIST-03: preserve OHLCV evidence, provider lineage, capture time, revisions, integrity, and read-only API. This is a defensible historical **archive**, not an exchange-certified point-in-time market feed or a trading system.

## What is implemented

- SQLite (WAL) at `data/history.sqlite` by default, isolated from existing journal/screeners in `data/swing.db`. Tables created with `IF NOT EXISTS`: `history_batches`, `history_candles`, `history_actions`; no destructive migration, manual backups remain necessary.
- Explicit ingest only; existing `/v1/screeners/runs` and Run Scan behavior are **unchanged**. `HistoryStore.ingest` appends finalized daily OHLCV, validates UTC/OHLC chronology/session uniqueness/finite volume, bounds batches to 2,500, rejects unsupported provider/source or price-basis claims, and computes a SHA-256 batch manifest.
- Corrections append revisions, identical recaptures are idempotent; `read(..., as_of=UTC)` reconstructs the **latest version first observed by this archive** before the requested cutoff and verifies per-row SHA-256. A backfilled 2024 bar captured today was *not* recorded as historically available in 2024.
- Strict source segregation: `SYNTHETIC_FIXTURE` may use only `SYNTHETIC`; Yahoo/Binance capture must use `VENDOR_UNVERIFIED`, never self-proclaimed `RAW_VERIFIED`/`SPLIT_ADJUSTED_VERIFIED`. Source, market, and instrument ID must match.
- Flag large equity price discontinuities as `SPLIT_OR_OUTLIER_SUSPECTED`, long session gaps as `LONG_GAP_REQUIRES_CALENDAR_REVIEW`, with NO automatic price correction or gap-filled candles. Record split/dividend *evidence* as independent immutable revisions, not verified adjustments.
- API read-only under the **existing** `/v1/*` token middleware. No writable ingestion route or network call on GET. No order execution, no prediction, no implicit backtest conversion.

## Offline capture (safe default)

From root of repository with installed backend dependencies:

```sh
python scripts/history_ingest.py --mode demo --limit 3
```

The default archive is `data/history.sqlite`; `data/` and `*.sqlite` are git-ignored. Inspect a bounded archived response using existing authenticated local API:

```sh
curl 'http://127.0.0.1:8001/v1/history/batches?limit=10'
curl 'http://127.0.0.1:8001/v1/history/observations/US:NASDAQ:MSFT?source=SYNTHETIC_FIXTURE&price_basis=SYNTHETIC&limit=5'
```

If `SWING_API_TOKEN` is configured, use `Authorization: Bearer <token>` from a secure shell/secret store; avoid putting tokens in shared screenshots or shell history. A `404` response means no observations exist for that source+basis; not an empty `0` price.

### Provider capture (opt-in, NOT for a Mac still showing an XProtect alert)

After independently resolving the macOS alert and confirming installed dependencies and providers are trusted, the command supports:

```sh
python scripts/history_ingest.py --mode live --allow-live --instrument-id US:NASDAQ:MSFT
```

- Does **not** execute a shell or install packages; it invokes existing `load_bars` (Yahoo equity `period=2y` or Binance 350 daily bars). This phase **does not implement multi-year provider pagination** beyond those existing limits.
- Outbound provider/network calls can execute third-party Python/native code indirectly. No remote scan has been executed on the user's Mac by this change. The earlier macOS **Malicious Script Blocked** cause remains unknown. **Do not run this LIVE command while that warning remains unresolved.** Never disable Gatekeeper/XProtect to force completion.
- Any failed provider or validation is reported as an error; **no silent switch** to synthetic prices.

## API contract

- `GET /v1/history/batches?limit=50` — captures, hashes, row counts, correction counts. Max 100.
- `GET /v1/history/observations/{instrument_id}?source=...&price_basis=...&as_of=...&limit=500` — archived candles with revision, content hash, flags and observation timestamp; max 2500. `as_of` must be UTC ISO-8601.
- `GET /v1/history/actions/{instrument_id}?source=...&as_of=...` — stored corporate-action evidence; adjustment_applied always false.
- API and CLI do **not** accept arbitrary provider URLs, shell commands, or user-supplied executable expressions.

## Critical data science limitations (remain open)

1. Historical Yahoo backfill can already reflect modern split adjustments. `auto_adjust=False` does **not** prove original unadjusted tradable historical prices. Captured records are `VENDOR_UNVERIFIED` and **cannot certify fill/risk geometry**.
2. This archive's `first_observed_at` records the actual time *this software saw a bar*, not the real provider publication/availability time. It therefore **cannot establish point-in-time survivorship-free backtests** for periods before capture.
3. Venue holiday, suspension, early-close, and official calendar completeness checks are not integrated; gaps remain explicitly unverified.
4. Corporate actions can be archived as evidence, but are **not automatically fetched, reconciled or applied**. Split-adjusted analytic vs raw executable series remain unverified.
5. Existing historical provider adapters are finite-window (`yfinance` 2y, Binance 350 bars); no archival delisted-company universe, cross-source reconciliation, or long-term correction monitoring.
6. `validated`, `point_in_time_validated`, `calendar_validated`, `corporate_actions_verified`, and `execution_verified` remain **false**. Live quotes, fees, exchange lots and trade execution are not certified.

## Verification and acceptance

`PYTHONPATH=backend python -m pytest -q backend/tests/test_history.py`

Tests check atomicity, timestamp provenance, revisions/idempotency, conflict rejection, provider/basis spoofing, corporate-event evidence, checksum tampering, old API guard, offline demo capture and LIVE opt-in. CI also runs the full existing backend suite. No LIVE scanner or untrusted AppleScript is run during tests.
