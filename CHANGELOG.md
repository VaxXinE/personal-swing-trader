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
