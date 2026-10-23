# Application Package Manifest

**Version:** 0.2.1-alpha  
**Date:** 2026-10-23  
**Type:** runnable browser + FastAPI research alpha and Flutter mobile source; not a production release.

## Package contents

- `START_HERE_ID.md`: Indonesian plug-and-play instructions.
- `web/`: responsive installable browser interface, PWA manifest and static asset-only service worker.
- `backend/`: demo/live provider adapters, scan engine, SQLite watchlist/journal, rule validator and private API.
- `apps/mobile/`: Flutter client **source**, Android platform scaffold generated on Flutter machine or GitHub Actions.
- `.github/workflows/`: optional CI job that builds an APK **if successful** (not tested here).
- `config/`: manual market-universe baseline; no credentials stored.
- `scripts/sync_universe.py` and `backend/app/universe.py`: opt-in US/crypto discovery and IDX XLSX/CSV import.
- `data/discovered_universe.json`: created locally after sync; gitignored.
- `docs/`: original strategy, risk, architecture, API and roadmap specifications.
- `BUNDLE_MANIFEST.json`: SHA-256 inventory of packaged files (excludes itself).

## Verification & limitations

Test results are recorded in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
`demo` is synthetic, forecast probabilities are withheld, equity/crypto data adapters are best-effort EOD research, and there are no brokerage transactions. Neither APK build nor live provider connectivity was verified in this environment.
