# Archived Backtesting Integration — Research Only

**Task ID:** BT-HIST-01 · **Acceptance:** a stored, source-qualified OHLCV observation snapshot is replayed without any provider or network calls. Existing `/v1/backtests/{instrument_id}` remains unchanged.

## What ships

- `backend/app/archive_backtest.py` adapts the immutable archive observation records into `Candle` objects, then calls the **same** existing `replay()` strategy and execution simulator. No threshold, target calculation, friction assumption, or journal/order logic is changed.
- `GET /v1/history/backtests/{instrument_id}` is read-only, covered by the existing `/v1/` Bearer authentication middleware. There is no POST, arbitrary URL, subprocess, or automatic historical download.
- `scripts/archive_backtest.py` replays a previously ingested archive offline; by default, DEMO MSFT.
- Data mode and provider are **strictly paired**. DEMO: `source=SYNTHETIC_FIXTURE`, `price_basis=SYNTHETIC`. LIVE configuration: US/IDX use `YFINANCE_RESEARCH_RAW` and crypto uses `BINANCE_SPOT_EOD`, always with `VENDOR_UNVERIFIED` basis. A LIVE archive replay never fetches fresh LIVE data, and mode mismatch fails closed with HTTP 422.
- The bridge reads up to 2,500 recent archived candles and refuses to simulate fills if the archive contains suspected splits/outliers, long unexplained gaps, unknown flags or insufficient warmup/history. Quality flags are also recomputed from adjacent bars because flags metadata is not itself covered by the underlying per-row payload checksum. Existing underlying OHLC checks still run.
- A `sha256` fingerprint binds the selected instrument/provider/basis to each candle's timestamp, revision, content checksum and first observation time. Responses include the resolved observation cutoff `as_of_observation` and the fingerprint. Reusing both fields makes a specific archived version reproducible; if the fingerprint mismatches, HTTP 409 is returned instead of silently using revised data.

## Offline CLI walkthrough

**Prerequisites:** previously ingested `data/history.sqlite`, e.g. `python scripts/history_ingest.py --mode demo --limit 3`.

```bash
python scripts/archive_backtest.py --mode demo --instrument-id US:NASDAQ:MSFT --strategy PULLBACK
python scripts/archive_backtest.py --mode demo --instrument-id US:NASDAQ:MSFT --strategy BREAKOUT
```

Store the printed `snapshot_as_of` and `snapshot_sha256` to reproduce exactly the same version later:

```bash
python scripts/archive_backtest.py --mode demo --instrument-id US:NASDAQ:MSFT \
  --as-of '2026-10-23T09:06:17.907937Z' \
  --expected-snapshot-sha256 'PUT_64_HEX_DIGITS_FROM_PREVIOUS_OUTPUT_HERE'
```

The sample date is illustrative; use your own actual CLI output. None of these commands makes network calls.

## API walkthrough

Run server in DEMO mode and call:

```bash
curl -fsS 'http://127.0.0.1:8001/v1/history/backtests/US:NASDAQ:MSFT?source=SYNTHETIC_FIXTURE&price_basis=SYNTHETIC&strategy=PULLBACK&horizon=10' | python -m json.tool
```

Query parameters: `source`, `price_basis` (required), `strategy` (`PULLBACK` or `BREAKOUT`), `horizon` (2–20), `as_of` (UTC first-observed cutoff, optional), `limit` (1–2500), and `expected_snapshot_sha256` (optional optimistic hash assertion). With API bearer auth enabled, provide the token privately; do not publish secrets or put tokens into shared commands/logs. HTTP status: `200` research result, `404` no matching instrument/observed candle, `409` expected fingerprint mismatch, `422` invalid/mixed/unsafe data.

The web asset detail provides an **Archived backtest** button in addition to the existing backtest. Its result displays source, snapshot cutoff, fingerprint and rejection statistics. This button **does not** start LIVE Run Scan or write archives. If no archive exists it displays an error, not a DEMO fallback.

## Scientific and security limits

**`validated: false` and `status: RESEARCH_ONLY` are unconditional.** An archival snapshot is not a genuine historical point-in-time feed: first-observed time is when *this application* ingested a provider backfill, not when the venue published it. Yahoo's returned historic candles may include post-event adjustments even with `auto_adjust=False`. This does not supply a delisted-universe, verified split/dividend data, official calendar, direct execution prices, or leakage-free model-selection holdout. Do not treat outcome metrics as forecasts or financial advice.

The SHA-256 hashes detect accidental/unauthorized modifications **only if the stored expected digest is trustworthy**; they are not cryptographically signed, and an attacker with write access could alter both data and hashes. The archive database is not a regulated immutable audit ledger. Restoring an older SQLite backup can also change the version seen at a given observation cutoff; the supplied fingerprint fails closed when checked.

**Mac warning remains unresolved:** do not enable LIVE capture or Run Scan just to verify this bridge. This phase only consumes already archived data. No XProtect/Gatekeeper overrides are part of the project.

## Verification

```bash
PYTHONPATH=backend python -m pytest -q backend/tests/test_archive_backtest.py
PYTHONPATH=backend python -m pytest -q backend/tests
node --check web/app.js
```

Historical archive check covers the local provider-free replay, mode/basis mismatches, revisions and stable as-of hashes, explicit 409 failure, quarantining suspicious data, payload corruption, private API access, missing/insufficient history, and offline CLI.


## Candidate-roster observation status

An archived replay additionally returns `archive_snapshot.universe_evidence` (observed candidate-roster counts by bar, source/mode, and a SHA-256 evidence fingerprint). Use `--expected-universe-evidence-sha256` to detect changes independently of the candle revision fingerprint. The current registry cannot establish historic IPO/delisting or listing membership, so the evidence never changes `validated:false`. See [HISTORICAL_UNIVERSE](HISTORICAL_UNIVERSE.md).
