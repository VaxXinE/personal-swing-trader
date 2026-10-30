## 2026-10-30 — Release readiness evidence and explicit go/no-go

- Document research-only beta feature gates, actual test evidence, device/manual recovery checks and blockers to trustworthy real-market strategy validation.
- Keep existing unknowns and zero-trade research baseline visible rather than declaring production readiness on CI compilation alone.

## 2026-10-30 — TSK-005 private SQLite backup/restore hardening

- Replace single-database ad hoc backup with SQLite online snapshot of journal and history archive, bounded SHA-256 manifest and owner-only local files.
- Add verify and fail-closed restore to a new directory; no silent overwrite, SQL executed from manifest names, network upload or secret export.
- Add seven offline regression checks for WAL, two-DB roundtrip, malicious manifests, checksum tampering, symlink and overwrite protections.
- Keep cross-DB atomicity and at-rest encryption explicitly out of scope, with recovery runbook.

## 2026-10-25 — Chronological rejection stability diagnostics (TSK-027 partial)

- Split archived PULLBACK and BREAKOUT research funnels into deterministic EARLY/LATE signal windows while retaining the original signal calculations, fills and 75/25 holdout.
- Reconcile per-period technical/gate/entry counters and disjoint reason combinations against the global diagnostic counters; cover no-history and engineered-trade fixtures.
- Extend the offline and seven-market CI reports with time-window summaries, without adding an external provider or changing strategy thresholds.
- Keep all backtest results RESEARCH_ONLY and descriptive; observed 2025–2026 history is not an untouched prospective validation dataset.

## 2026-10-25 — Exact technical rejection combinations (TSK-027 partial)

- Trace per-signal *disjoint* rejection combinations and exclusive one-reason failures, so multi-label reasons do not overstate how many bars were rejected.
- Surface top five combinations in both-strategy research diagnostics and CI, with stable lexical ties and no change to targets, stops, fees, entry rules, or validation status.
- Add tests for funnel arithmetic and single-failure interpretation. No data redistribution, new dependencies, strategy fitting, or trade execution.

## 2026-10-25 — Real-provider strategy diagnostics baseline

- Record seven-market, both-strategy provider CI results (3,045 archived candles, 1,505 eligible bars for each strategy, zero qualified setups) and observed rejection reasons with a traceable GitHub Actions run URL.
- Preserve unchanged strategy thresholds and research-only interpretation; no candidate cherry-picking, price redistribution or future-looking parameter tuning.

## 2026-10-25 — Zero-trade real-data research diagnostics (TSK-027 partial)

- Add offline dual-strategy archived snapshot funnel diagnosis with pinned observation cutoff, candle digest, and universe-evidence digest; report technical, research gate and next-bar entry rejection counts separately.
- Differentiate actual setup bottlenecks from insufficient completed-trade sample, without changing any trading criterion or fabricating expectancy.
- Switch seven-asset real-provider CI from only PULLBACK replay to both PULLBACK and BREAKOUT diagnostics when the quality gate passes; keep all vendor OHLCV ephemeral and not in Git.
- Add offline regression tests and research reporting guide; no new provider, dependency or secret.

## 2026-10-25 — IDX holiday evidence and extended real-price research pilot

- Reconcile the IDX 17–25 March 2026 long gap against published exchange holiday evidence; allow only those five documented weekday closures, retaining archived flags and applying a narrowly scoped review marker.
- Block missing additional weekdays, false candles on published closures, unexplained gaps on US/other periods, and suspected split/outlier price jumps.
- Expand cloud LIVE research matrix from 3 assets to 7 and lookback 2025-04-01–2026-10-20; no trading or strategy changes, no public redistribution of provider OHLCV.
- Add regression tests and calendar-source provenance. Apply anti-slop (no empty comments or inflated claims) and ponytail (smallest change using standard library and existing audit).

## 2026-10-25 — Real internet market research verification

- Add opt-in / provider-change-triggered GitHub-hosted market-data smoke checks for genuine MSFT, BBCA.JK and BTCUSDT daily bars over 2025-10-01 to 2026-10-20.
- Reuse existing bounded LIVE ingestion, offline quality audit, and archived replay; no extra provider wrapper, extra database schema, broker connection or trading.
- Do not publish or commit Yahoo Finance prices in a public repo; keep captured research archives ephemeral on CI runners.
- Document how to capture separate VENDOR_UNVERIFIED data in a user's own local history.sqlite with explicit consent.
- Apply anti-slop and ponytail guidance: narrow scope, reuse current code, no third-party agent hook or installer.

## 2026-10-24 — Historical candidate-universe observations (TSK-013 partial)

- Persist bounded, immutable *observed candidate* registry snapshots in the existing historical SQLite archive via a separate offline CLI; use actual observation times rather than invented historical listing dates.
- Audit each archived candle against only roster observations available by that candle's time; distinguish observed candidates from unknown/not sampled, never mark absence as delisted.
- Add reproducible universe-evidence fingerprint and optional fail-closed pin in archived replay CLI and API, a private capture-metadata endpoint and web disclosure.
- Retain `RESEARCH_ONLY`, `validated:false`, old scanner and strategy logic; no market-data API calls, external plugin hooks, or new dependencies.

## 2026-10-23 — Historical evidence reconciliation v1 (TSK-012 partial)

- Add bounded local second-source close evidence reader and optional CLI comparison without downloading or trusting a vendor claimed by the file.
- Reject calendar/reference evidence claiming to be observed after the archived cutoff; fingerprint candles, evidence, calendar and as-of action revisions.
- Correct archived corporate-action reads to return only the latest revision observed by the requested snapshot cutoff.
- Apply anti-slop/ponytail principles from reviewed upstream sources without installing executable hooks or new dependencies; keep all results research-only.

## 2026-10-23 — Research historical-quality gate (TSK-007/008/012 partial)

- Expose archived-replay quality gate summary and calendar certification limitations in the existing web asset-detail modal, with HTML-escaped values.

- Add deterministic offline research-snapshot quality checks: session-date mismatch and tampering, weekend equity bars, continuous crypto daily close/coverage, large unexplained equity price gaps and zero volume.
- Accept optional bounded, explicitly *unverified* external session lists, and reject missing/out-of-calendar sessions only for a fully covered supplied period. Handle evidence-only corporate actions and same-basis independent-source price discrepancies without inventing trusted data.
- Expose a read-only private `/v1/history/quality/{instrument_id}` endpoint and offline audit CLI; integrate fail-closed anomalies into archived replay without altering the legacy scanner or strategy rules.
- Add 11 adversarial/offline tests and quality contract docs. No LIVE provider calls or macOS XProtect workarounds.

## 2026-10-23 — Archived historical backtesting bridge

- Add provider-free, read-only archived backtests with reproducible SHA-256 observation snapshots and fail-closed source/mode mixing.
- Add conservative quality gate for suspected splits/long gaps, archive replay API, offline CLI, web asset-detail action, and 11 offline contract tests.
- Keep original backtest/scan API behavior and `validated:false`, do not initiate any LIVE provider request during archived replay.

## 2026-10-23 — Bounded historical source windows

- Add opt-in start/end calendar capture to the Historical Data Engine, with fail-closed Yahoo EOD finality and fixed-origin Binance spot pagination.
- Enforce window limits and no arbitrary external URLs or redirect-following. Add isolated/mock adapter tests; normal Run Scan remains unchanged.

## 2026-10-23 — Historical Data Engine v1 (research-only)

- Add SQLite append-only historical candle batches, corrections/revisions, provider price-basis separation, source manifest and integrity checks, as-of-first-observed snapshots.
- Add immutable corporate-action evidence, gap/split-suspect flags, a read-only authenticated API and offline-default explicit ingestion CLI with bounded LIVE opt-in.
- Add offline security and data-integrity contract tests, without changing scanner behavior, forecast/trading permissions, or allowing arbitrary provider URLs.
- Document why this archive is not yet a corporate-action-verified, survivorship-free, historically point-in-time feed; XProtect alert remains unresolved.

## 0.3.0-alpha — Swing Research Gate V2 (2026-10-23)
- Add an explainable research-only gate: technical confirmation, historical liquidity, stop distance in ATR, structural target, and modeled net R:R.
- 0.1% per-side friction is a labelled research assumption, never actual brokerage cost.
- Display PASS/WAIT/BLOCKED/EXCLUDED checks in asset detail without fabricating trade readiness or win probability.
- Preserve immutable old scans; add offline regression tests for gate semantics, look-ahead isolation and conservative cost rejection.
- Detailed specification in docs/STRATEGY_ENGINE_V2.md.

## 0.2.2-alpha — Discovery quality & coverage (2026-10-23)
- IDX candidate selection no longer always takes the alphabetic first 35 ticker codes. It now samples the entire imported listing using deterministic month-scoped rotation; no unverified claim of improved liquidity.
- Distinguish INSUFFICIENT_HISTORY scan rejections from provider/data failures. The raw error list is retained for backward compatibility.
- Per-market coverage exposes liquidity_passed and insufficient_history counts; dashboard now distinguishes attempted assets, analyzed assets, and strategy evaluations, and links to the XLSX importer.
- Existing saved scans and universe snapshots remain unchanged until the user explicitly syncs and runs a new scan.

# Changelog

## 0.2.1-alpha (2026-10-23)
- Import official IDX `.xlsx` listing directly, with shifted header and multi-worksheet handling; CSV compatibility retained.
- Exclude Papan Pemantauan Khusus when the board column exists; validate four-letter ticker and preserved previous snapshot on failure.
- No additional Python package needed for XLSX parsing, no formula evaluation or external file upload; defensive archive size limits.
- 6 new XLSX regression tests, including malformed/oversized workbook behavior. Import against a real BEI export still requires local validation.


## 0.2.0-alpha (2026-10-23)
- Opt-in Dynamic Liquid Universe candidate discovery, provider-specific sourcing, atomic local cache, bounded registry expansion.
- Data Health discovery/scan coverage, grouped Opportunity Explorer per asset, API discovery endpoint.
- Preserve baseline on provider failure, 15-minute EOD data cache; regression and browser smoke tests.
- Explicit IDX official CSV path, no undocumented auto-scraping and no live/profitability guarantees.

# Changelog

## [0.1.0] — 2026-10-23
- Initial documentation blueprint for private mobile personal swing intelligence system.
- Locked: long-only, manual trading, liquid universe, broad discovery, US/IDX/crypto spot, Flutter/FastAPI.
- Baselines: market liquidity thresholds, technical strategies, score weighting and risk budget; all explicitly unvalidated.
- Defined gated forecast, auditability, data quality and security requirements.
- **No app code implemented, no backtests executed, no trading performance claimed.**


## [0.1.0-alpha] — 2026-10-23 (implementation)

- Added private FastAPI local backend with health, registry, demo/live feeds, universe exclusion, two strategies, rule builder, score, research levels, risk sizing, watchlist, journal and immutable snapshot store.
- Added standalone responsive web client and Flutter Android/iOS Dart source (Flutter SDK bootstrap needed).
- Added launch scripts for Windows, macOS and Linux, optional Docker recipe, backup script, EOD scan script, editable instrument registry, and backend tests.
- Added implementation status matrix: execution verification, full point-in-time historical backtesting, realtime streaming, push alerts, fundamentals and ML forecasts not completed.
- Verified backend tests and browser rendering with API-mocked fixture; no release APK built in this environment.

## v0.1.1 — plug-and-play packaging improvements
- Liquid Universe now the default in both the responsive browser and Flutter Explorer, with opt-in excluded assets toggle.
- Added installable web shell (PWA manifest/icons/asset-only service worker; personal/API data never cached).
- Added `START_HERE_ID.md`, `scripts/doctor.py`, real-HTTP Chromium test and GitHub Actions private APK build workflow.
- Release APK build is an **untested workflow**, not a delivered or verified APK; no forecast probabilities have been activated.
