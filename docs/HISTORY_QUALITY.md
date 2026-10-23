# Historical Data Quality & Validation v1 — research-only quality gate

**Scope:** TSK-007/TSK-008/TSK-012 partial implementation. Deterministic offline checks and conservative quarantine, with explicit unverified inputs. **This phase implements a quality *audit*, NOT complete authoritative historical-data validation.** No LIVE Run Scan was executed, and the earlier macOS XProtect alert is still unresolved.

## Delivered

- `backend/app/history_quality.py`: independently recomputes market-local session dates from UTC OHLC close markers; checks duplicate/out-of-order sessions, US/IDX weekend observations, crypto UTC 23:59:59 day-end markers and missing 24-hour candles, unexplained long equity gaps, suspect split-size price jumps, and zero volume. Raw OHLC already undergoes `HistoryStore.read()` SHA-256 and `validate_candles` checks. It **does not** alter stored OHLCV, auto-fill gaps or repair/certify corporate actions.
- Explicit user-provided calendar evidence (JSON, ≤512 KiB, 5000 ordered unique sessions, single market, UTC observed_at, bounded coverage). Only declared sessions inside the fully covered period can count as missing. No simplistic weekday rule is used to declare US Thanksgiving, IDX closures, holidays or half-days *missing*. Calendar source is always `PROVIDED_UNVERIFIED`, even with a plausible source name or URL. Without a calendar, equity coverage is `NOT_PROVIDED`. Crypto uses continuous UTC dates.
- Evidence-only split matching (within ±2 calendar days of a suspicious price jump). Matching evidence never changes the severity of the underlying 35% discontinuity or claims an executable RAW price. Dividend events remain unadjusted.
- Independent archived/reference series comparison when the caller supplies a second source, same instrument and price basis, and explicitly matching currency; >2% close differences block the quality gate. A reference's identity or provenance is not externally certified merely by being supplied. The current default single-provider archive cannot complete source reconciliation without acquiring genuinely independent licensed data.
- `GET /v1/history/quality/{instrument_id}` exposes read-only report behind existing auth, no file-path parameters, imports, fetches or side effects. `python scripts/history_quality_audit.py` works offline against `data/history.sqlite` and supports `--calendar /local/path/file.json` with no network calls. Reports list at most 100 findings but preserve full counts. Always `calendar_validated=false`, `corporate_actions_verified=false`, `point_in_time_validated=false`, `execution_verified=false`.
- Archived backtest calls the same validator on the selected, pinned snapshot. `BLOCKED` findings return HTTP 422; research-only warnings remain disclosed in `archive_snapshot.quality_report`. Original non-archived `/v1/backtests/*` and `/v1/screeners/*` remain unchanged. Snapshot fingerprint still refers only to chosen candle revisions, not supplied external calendar; include calendar SHA-256 separately to identify audit context.

## Run locally (safe / no LIVE providers)

```bash
# Prerequisite: archived DEMO candles exist from earlier tests
python scripts/history_quality_audit.py --mode demo --instrument-id US:NASDAQ:MSFT
python scripts/history_quality_audit.py --mode demo --instrument-id US:NASDAQ:MSFT --json
PYTHONPATH=backend python -m pytest -q backend/tests/test_history_quality.py
PYTHONPATH=backend python -m pytest -q backend/tests
```

With the locally running DEMO server:

```bash
curl -fsS 'http://127.0.0.1:8001/v1/history/quality/US:NASDAQ:MSFT?source=SYNTHETIC_FIXTURE&price_basis=SYNTHETIC&limit=2500' | python -m json.tool
```

Example **manual calendar evidence only** (NOT an official calendar):

```json
{
  "market": "US",
  "source": "Manually reviewed session export; not certified",
  "observed_at": "2026-10-23T00:00:00Z",
  "coverage_start": "2026-10-20",
  "coverage_end": "2026-10-22",
  "sessions": ["2026-10-20", "2026-10-21", "2026-10-22"]
}
```

Save under a local non-Git directory and invoke `--calendar /absolute/path/sessions.json`. The calendar must cover **the whole selected archive period** to support a missing-session verdict. A partial calendar produces `CALENDAR_WINDOW_NOT_COVERED` and a research warning, rather than pretending gaps are verified. Archive retention cap is 2500 candles; a truncated window is disclosed separately by the archive replay response.

## Hard limitations before research evidence can support investment decisions

1. No official versioned US or IDX trading calendars, including holidays, half-days, exceptional trading, IPO dates and halts, have been imported or certified. A user-supplied JSON calendar is not self-authenticating.
2. Vendor-adjusted/RAW historical prices remain unverified; corporate-action evidence is not fetched from authoritative original filings and is not applied. A real backtest must use *tradable RAW price at the time* consistently for fills, ticks, fees and dividends.
3. The archive's `first_observed_at` is not data's original publication time. Modern vendor backfill does **not** establish no-look-ahead fundamentals or delisted-universe membership. Holdout remains descriptive.
4. A second independent price source is **not configured**. The comparator requires explicit, same-currency/basis source evidence; no fallback or fake synthetic comparison.
5. No user trading is executed, no strategy threshold was relaxed, and no win-rate/probability/portfolio claim is certified. All returned results remain `RESEARCH_ONLY`.
6. The macOS XProtect popup was not reproduced or attributed. Continue to avoid LIVE Run Scan until it is investigated using actual local system diagnostics; do not disable Gatekeeper/XProtect.

## Acceptance / reproducibility

Offline tests exercise normal archive, missing session, duplicate/out-of-scope calendars, weekend equity and missing crypto days, SHA-preserved session metadata tampering, split evidence, cross-source conflicts, currency/basis mismatch, API and CLI without provider access. All changes are additive, and the original history SQLite schema requires **no migration**.


## Website display

Archived Backtest modal now surfaces the research quality-gate status, calendar coverage, and finding counts. The label `STRUCTURAL_PASS` does not imply a certified exchange calendar or corporate-action adjustment. Blocking issues return an API 422 with a reviewable error instead of drawing a fabricated performance report.


## Historical evidence reconciliation (2026-10-23)

Offline quality audit can now compare a **user-provided second-provider close series** with the archived series using `--reference /absolute/path/closes.json`. The bounded JSON contract is `instrument_id`, `source`, `price_basis`, `currency`, `observed_at`, and `candles` (up to 2500 strictly increasing `session_date` and positive decimal-string `close`). A valid input still has `independent_source_verified=false`; its claimed vendor and observation time are **not independently authenticated**. No request is made to the named provider.

```sh
python scripts/history_quality_audit.py --mode demo \
  --instrument-id US:NASDAQ:MSFT --reference /private/research/msft-second-source.json --json
```

The report's `evidence_sha256` fingerprints the selected archived candle revisions, calendar document, reference file content and as-of corporate-action evidence. Save it and pass `--expected-evidence-sha256 DIGEST` to reject later accidental evidence changes. This digest is not a signature and must be retained outside the writable archive if tamper detection matters.

Calendar and reference `observed_at` dates later than the selected archive snapshot cutoff now **BLOCK** reconciliation, rather than being silently treated as known at that time. Corporate-action reads now return **the latest revision observed by the requested cutoff**, preserving a reproducible historical view.

The feature is additive and offline: no new dependencies, network permissions, price adjustments, exchange-calendar certification or automated execution. The macOS XProtect popup remains unresolved.
