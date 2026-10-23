# Historical candidate-universe observation — research-only

**Task:** TSK-013 (partial; historical eligibility evidence). **Status:** implemented observed-roster snapshots, not a point-in-time complete exchange universe. **No LIVE network calls.**

## Problem

`config/universe.json` holds the current manually configured watchlist; `data/discovered_universe.json` holds a rotating, bounded *candidate sample*. Neither one establishes the listing status, IPO date, delisting status or liquidity of a security in 2024 or 2025. Running a backtest for an asset picked from today's roster does not resolve survivorship bias.

## Implemented

- `backend/app/universe_history.py` uses the **same** `data/history.sqlite` database with one new `history_universe_observations` table (created only during an explicit CLI capture). A snapshot records its **actual observation timestamp**, mode, sorted canonical candidate IDs and a SHA-256 digest covering the observation time and membership. The table is append-only by application contract.
- `scripts/universe_capture.py` explicitly captures the local registry with `--mode demo` or `--mode live`. Even in `live` mode this reads local registry/discovery JSON **without contacting providers**. Capture never allows arbitrary past observation dates, and refuses conflicting rosters with the same timestamp. A second identical capture with the same injected clock is idempotent.
- For each historical bar, the validator uses only a roster observation recorded **on or before that bar's time**. Before the first observed roster it returns `UNKNOWN_BEFORE_OBSERVATION`; a present candidate returns `OBSERVED_CANDIDATE`; absence from a sampled roster returns `UNKNOWN_NOT_IN_SAMPLE`, **not** unlisted or ineligible.
- Archived Backtesting Engine V2 includes `archive_snapshot.universe_evidence` with per-bar counts, `evidence_sha256`, and explicit `historical_membership_verified=false`, `survivorship_bias_resolved=false`. It stays `RESEARCH_ONLY`, `validated=false`. The original candle fingerprint remains unchanged. An optional `expected_universe_evidence_sha256` pin detects changes to sampled-roster evidence. This does not modify trades or change strategy criteria.
- Read-only, private `GET /v1/history/universe/captures` returns bounded capture metadata; no user-provided file path or network endpoint. The web Archived Backtest modal displays unknown/observed counts separately from validated performance.
- Schema change: table is created automatically on first capture in existing `history.sqlite`; old candle/action data and replay APIs are preserved. Until a capture exists, the replay reports `NO_UNIVERSE_EVIDENCE`. No automatic capture at startup.

## Offline workflow

```bash
# From project root with .venv activated; no LIVE provider is called.
git pull --ff-only origin main
python scripts/universe_capture.py --mode demo
python scripts/archive_backtest.py --mode demo --instrument-id US:NASDAQ:MSFT --strategy PULLBACK
PYTHONPATH=backend python -m pytest -q backend/tests/test_universe_history.py
PYTHONPATH=backend python -m pytest -q backend/tests
```

With a local DEMO server:

```bash
curl -fsS 'http://127.0.0.1:8001/v1/history/universe/captures?limit=5' | python -m json.tool
```

For repeatable archived replay, save **all three** output fields: `snapshot_as_of`, `snapshot_sha256` (candle revisions) and `universe_evidence_sha256` (observed candidate-roster evidence). Then pass both `--expected-snapshot-sha256` and `--expected-universe-evidence-sha256` with the original `--as-of`. A later sample capture must not silently alter the pinned result.

## What remains *not* proven

- These are observation-time snapshots of **current candidates**, not historical exchange listings. This method cannot reconstruct assets that were delisted before the app started observing them. No IPO/delisting corporate-event feed has been integrated.
- `OBSERVED_CANDIDATE` does not establish historic listing, membership of a broad index, investability, market trading hours, spread/turnover liquidity, or actual access to data at that time. The dynamic discovery snapshot rotates/filters candidates; therefore **absence is UNKNOWN**, never `NOT_LISTED`.
- Historical market price basis, action-adjusted executions, original publication times, US/IDX official historical trading calendars, and a complete licensed historical universe are still missing. Even when all selected bars have observed-candidate evidence, all validation/forward-trading claims remain false.
- Checksums are accidental-corruption checks, not independently signed provenance. A machine that can rewrite both database records and their hashes can forge the evidence; keep trusted copies/backups outside the research DB.
- No real-money trading, return forecasts, strategy loosening, external npm installs or agent hooks. The unresolved local macOS alert is separate from this offline development work.

## References for engineering approach

The upstream `miqdadbadjuber/anti-slop` comment hygiene and `DietrichGebert/ponytail` YAGNI/edge-case guidance informed the small-scope implementation. No external project code was copied or executed and no persistent third-party agent hook was installed.
