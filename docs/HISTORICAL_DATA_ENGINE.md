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

- Does **not** execute a shell or install packages. With no explicit date range it uses existing `load_bars` (Yahoo equity `period=2y` or Binance 350 daily bars). With both `--start-date` and `--end-date`, the bounded `history_sources` adapter fetches daily equities using an inclusive date window and Binance spot klines with bounded pagination, **at most 2,500 candles per ingest**. Larger windows must be split manually; a full year-over-year verified snapshot is not yet available.
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


### Optional bounded date-range backfill (LIVE opt-in only, after macOS security issue is resolved)

```sh
python scripts/history_ingest.py --mode live --allow-live --instrument-id US:NASDAQ:MSFT --start-date 2023-01-01 --end-date 2025-12-31
```

Dates are inclusive, must be valid `YYYY-MM-DD`, no future dates, and windows must be at most ten years; the 2,500-bar archive limit still applies. The equity adapter requests a fixed Yahoo symbol from the registry; the crypto adapter uses a fixed Binance origin, `follow_redirects=False`, spot-market checks, max four 1,000-row pages, and a fail-closed final-candle guard. A chosen historical window **does not prove price-basis/adjustment correctness, historical release time, or official session calendar completeness**. Mock-only contract tests confirm date-window rejection, provider origin allowlist, and final-candle filtering.


## Real internet market data: reproducible opt-in research check (2026-10-25)

Existing `history_ingest.py --mode live --allow-live` already connects to Yahoo Finance (US, IDX) and Binance public Spot APIs (crypto). The new [real-market-research workflow](../.github/workflows/real-market-research.yml) runs a bounded, provider-network verification on GitHub-hosted runners for `US:NASDAQ:MSFT`, `IDX:IDX:BBCA`, and `CRYPTO:BINANCE:BTCUSDT`. It is triggered by `workflow_dispatch` or by changes to the workflow/provider code on `main`. The database is ephemeral and **no vendor OHLCV is committed, cached, or uploaded as a public artifact**, as Yahoo Finance data rights are restricted. Only row counts, date range, source/basis and research test diagnostics appear in public CI logs.

```sh
# After explicitly installing research-only dependencies locally:
python -m pip install -r backend/requirements-live.txt
# Market data for a fixed, historic interval; note the explicit provider opt-in:
python scripts/history_ingest.py --mode live --allow-live --instrument-id US:NASDAQ:MSFT \
  --start-date 2025-10-01 --end-date 2026-10-20
python scripts/history_ingest.py --mode live --allow-live --instrument-id IDX:IDX:BBCA \
  --start-date 2025-10-01 --end-date 2026-10-20
python scripts/history_ingest.py --mode live --allow-live --instrument-id CRYPTO:BINANCE:BTCUSDT \
  --start-date 2025-10-01 --end-date 2026-10-20

python scripts/history_quality_audit.py --mode live --instrument-id US:NASDAQ:MSFT --json
python scripts/archive_backtest.py --mode live --instrument-id CRYPTO:BINANCE:BTCUSDT --strategy PULLBACK
```

The archive keeps research LIVE records under `VENDOR_UNVERIFIED`, **separate from all DEMO `SYNTHETIC` records**, including when sharing the same SQLite file. Quality failures must be reviewed, not auto-repaired. Yahoo uses a third-party unofficial client and may be rate-limited or blocked; a failed network capture means **no provider evidence was obtained**, not 0-volume market data. Official Binance public endpoint: https://data-api.binance.vision (no key). `yfinance` is for personal/research use; confirm your usage rights before any redistribution, vendor data export or commercial service. Spot-only does not apply to broker trade fills.

This internet data is *genuine provider-reported research data*, but **historical adjusted-price basis, first market publication time, delisted-universe coverage, exchange sessions and execution remain unverified**. Preserve `RESEARCH_ONLY` and `validated:false`; no actual position is opened. The macOS alert remains a separate issue; tests are executed on cloud runners instead of the affected machine, without bypassing its protections.


### First real-provider CI evidence and quarantine policy

The first 2026-10-25 run ([GitHub Actions 40117743259](https://github.com/VaxXinE/personal-swing-trader/actions/runs/40117743259)) obtained **actual provider data**: MSFT: 265 Yahoo bars and `STRUCTURAL_PASS`; BTCUSDT: 385 Binance Spot bars and `STRUCTURAL_PASS`; BBCA.JK: 253 Yahoo bars and `BLOCKED` on `LONG_GAP_REQUIRES_CALENDAR_REVIEW`. The research-runner now distinguishes **successful internet capture** from **quality quarantine**: a `BLOCKED` status intentionally skips archived replay and prints exact adjacent session dates for calendar evidence review, without treating any quarantine as a completed backtest. A malformed audit or provider failure still fails the job. Historical quote redistribution is avoided.

The IDX documented 2026 Nyepi/Idulfitri market break is March 18–24; authoritative calendar comparison needs to match the exact observed gap and full audited date period before changing its status. Do not suppress the 7-day safety threshold or retroactively invent a 2025–2026 official market calendar. Price-adjustment and historical-universe claims remain unverified.
