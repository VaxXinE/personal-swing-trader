# SWING INTELLIGENCE — Private Swing Trading Research Lab

**Bahasa Indonesia / Quick Start:** [START_HERE_ID.md](START_HERE_ID.md). Untuk developer, mulai dari [AGENTS.md](AGENTS.md) dan [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).

**Version:** `0.3.0-alpha` · **Date:** 2026-10-23 · **Owner:** single developer/user · **Scope:** long-only; US + IDX equities and crypto spot.

**New in 0.3.0:** Swing Research Gate V2 adds explicit PASS/WAIT/BLOCKED/EXCLUDED criteria, ATR-based stop geometry, structural-target requirement, and *illustrative* modeled transaction costs. This is **not a trading signal** and does **not validate profitability**. See [docs/STRATEGY_ENGINE_V2.md](docs/STRATEGY_ENGINE_V2.md).

> **THIS IS A WORKING ALPHA, NOT A FINISHED FORECAST PLATFORM.** The browser app and private API work in synthetic demo mode, and optional market data adapters exist. No trade execution. Quote verification, fundamentals, historical-bias-free validation, and ML probabilities are **not** production ready. All synthetic data is labelled, and all forecasts are withheld.

## 1. Quick start — browser/mobile-responsive, no Flutter necessary

Requirements: **Python 3.11+** and internet access for installing Python dependencies. After that, demo data requires no market API keys and can run offline.

**Windows**: double-click `scripts/start.bat` (or run it in CMD). **macOS / Linux**:

```bash
bash scripts/start.sh
```

The launcher does **not** install or download dependencies at startup. Prepare the virtual environment explicitly:\n\n```bash\npython3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install -r backend/requirements.txt\n# For LIVE data instead, install: python -m pip install -r backend/requirements-live.txt\n```\n\nThe launcher runs the local API on **127.0.0.1:8000**, and serves the fully functional responsive web application at:

**http://127.0.0.1:8000/**

Explore now starts with **Liquid Universe only**; toggle "Include excluded / illiquid assets" to inspect rejected instruments. Try **Overview → Explore → Asset detail → Add to Watchlist → Journal**, or open **Screener Builder** and create an AND/OR rule. There are **19 manual baseline research instruments** in `config/universe.json`. You can add more instruments (up to 250) by editing that file, then restart/re-run the scanner. DEMO mode generates deterministic synthetic candles, **not market prices**, and the quote/execution gate remains UNKNOWN.

Swagger/OpenAPI: `http://127.0.0.1:8000/api-docs`.

## 1b. Dynamic candidate universe (V2 opt-in)

The first 19 symbols remain as the safe baseline. To discover additional US directory listings and Binance active USDT spot pairs **without hand-editing tickers**:

```bash
source .venv/bin/activate
python scripts/sync_universe.py --markets US CRYPTO
# On successful sync, click Run Scan in the LIVE dashboard; or run:
SWING_DATA_MODE=live python scripts/scan_once.py
```

For IDX, download the official IDX stock-listing **`.xlsx`** file and import directly (no conversion):

```bash
python scripts/sync_universe.py --markets IDX --idx-file "$HOME/Downloads/Daftar Saham.xlsx" --idx-limit 35
```

`.csv` is still supported with the same `--idx-file` flag. The legacy `--idx-csv` flag remains accepted. Header rows may occur after an introductory title, and the importer inspects multiple worksheets for `Kode` / `Nama Perusahaan` / optional `Papan Pencatatan`. Special Monitoring Board rows are excluded only when identified. **The original Excel file is never modified.** This is **NOT a fully automatic IDX integration**. The UI Data Health page shows source, count, sync date and analysis coverage. Candidate pre-selection is not a claim of actual liquidity. US discovery deliberately samples the directory; crypto uses rolling 24h volume only before the true ADV20 filter. Discovery is local/explicit, never called on every dashboard request. See [docs/DYNAMIC_UNIVERSE_V2.md](docs/DYNAMIC_UNIVERSE_V2.md) for details and limitations.

## 2. Optional REAL market research data

Install optional provider and start with live mode:

```bash
# macOS / Linux after first setup
source .venv/bin/activate
pip install -r backend/requirements-live.txt
python scripts/launch.py --live
```

On Windows: `.venv\Scripts\activate.bat`, `pip install -r backend\requirements-live.txt`, `python scripts\launch.py --live`.

- US & IDX: unofficial Yahoo-based historical daily data through `yfinance`; `.JK` for IDX. For personal research; inspect provider terms, rate limiting, corporate action and data completeness.
- Crypto: Binance public **spot** market-data endpoint `data-api.binance.vision`, 1D finalized candles and bookTicker. No key or order trading permissions required. Regional connectivity may vary.
- Provider errors are shown under Data Health and **never** replaced with synthetic prices when LIVE is active.
- Backtest remains **research-only** and may have survivorship and corporate-action biases. Scores are heuristics, not win probabilities. No REALTIME label on historical EOD data.

**Important:** the app scans the union of manual `config/universe.json` and successfully synced `data/discovered_universe.json` while in LIVE mode (bounded to 250 instruments). It does **not** automatically discover every listed equity or crypto pair; exchange listings/market-rules as-of history need later engineering.

## 3. Installable Web App and private Android build

The responsive browser client includes a PWA manifest and offline-cacheable **static shell only** (never cached private API responses, passwords, journal or prices). It can be installed as an app from Chrome on `localhost` or a private trusted HTTPS origin. On a physical phone, configure your own trusted HTTPS private endpoint; the app still requires the running backend for market data.

A GitHub Actions template is included at `.github/workflows/verify-and-build-android.yml`: after pushing this repository to a **private** GitHub repo, use Actions → **Verify API and build private Android APK** → Run workflow. If the run succeeds, download the APK artifact. This workflow has not been executed here, so the APK is not yet verified. For instructions in Indonesian see [START_HERE_ID.md](START_HERE_ID.md).

## 4. Flutter Android app

Flutter SDK **is not bundled** in this repository. Install stable Flutter, Android SDK / Android Studio, and an emulator. Then:

```bash
bash scripts/flutter_setup.sh
cd apps/mobile
flutter run
```

Windows: run `scripts\flutter_setup.bat`, then `cd apps\mobile && flutter run`.

`flutter_setup` uses `flutter create` to add Android/iOS host project files while keeping the included Dart app source and `pubspec.yaml`. It enables Android internet permission and **debug-only** localhost HTTP (never release cleartext). Default server URL in the Flutter app is `http://10.0.2.2:8000`, the Android emulator's host-machine loopback alias. **Start the backend first.**

For an actual Android phone, connect it to the same **private VPN** (e.g. Tailscale), then configure the server URL in the Flutter app's Settings. Use HTTPS/Tailscale Serve or an identity-aware proxy for remote access. Do not expose a bare backend or token over public HTTP.

> A prebuilt APK is **not included**. Flutter SDK and Android toolchain were unavailable in the package-building environment, so the mobile code has not undergone `flutter analyze`/Android emulator testing here. The responsive browser UI has been rendered and verified in Chromium with mocked API responses.

## 5. Local private security

Default bind: **127.0.0.1 only**. To allow remote traffic deliberately, use a VPN/tunnel, assign a random 32+ character token, and set `.env`:

```bash
cp .env.example .env
python -c "import secrets;print(secrets.token_urlsafe(32))"
```

Put that value in `SWING_API_TOKEN`, set `SWING_HOST=0.0.0.0` **only when network access is restricted by VPN/firewall**, and start again. The launcher refuses remote binding without a strong token. Use browser gear icon or Flutter Settings to enter the token. Browser stores token **in page memory only**; Flutter stores token **in app memory only**. It must be re-entered on restart.

The app has no brokerage connections, withdrawal capability, or automated execution. Never commit `.env`, databases, journals, or actual secrets.

## 6. Important paths

| Path | Purpose |
|---|---|
| `web/` | Standalone responsive research client (served by backend) |
| `apps/mobile/lib/` | Flutter Android/iOS Dart source |
| `backend/app/domain.py` | Pure strategy, EMA/ATR/RVOL, scoring, liquidity, risk |
| `backend/app/rules.py` | Validated AND/OR/NOT rule AST (no `eval`) |
| `backend/app/providers.py` | Synthetic demo, yfinance, Binance REST |
| `backend/app/service.py` | Scans, rankings and immutable run snapshots |
| `backend/app/storage.py` | SQLite watchlist, journal, screener versions and signals |
| `backend/app/main.py` | FastAPI + endpoints + private token guard |
| `config/universe.json` | Editable manual baseline symbol/market registry |
| `scripts/sync_universe.py` | Opt-in candidate discovery from US/Binance and official IDX XLSX or CSV |
| `data/discovered_universe.json` | Gitignored local discovery snapshot (created on sync) |
| `scripts/scan_once.py` | EOD scan to schedule via OS cron/task scheduler |
| `scripts/backup.py` | SQLite consistent backup (unencrypted: store encrypted separately) |
| `docs/` | 25+ original engineering blueprint documents |
| `IMPLEMENTATION_STATUS.md` | Exactly what is implemented and what is missing |

## 7. Test it

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest -q backend/tests
python scripts/doctor.py
python scripts/server_smoke.py
# Optional: pip install playwright && playwright install chromium, then python scripts/ui_smoke.py
node --check web/app.js # if Node installed
```

Run `python scripts/scan_once.py` manually; schedule at ~07:30 Asia/Jakarta *if needed*, recognizing that provider scheduling and full exchange-calendar semantics are still outstanding. Use `python scripts/backup.py` for local database backups.

Docker option (advanced): `SWING_API_TOKEN=<random-32+-chars> docker compose -f infra/compose.yaml up --build`. Runs Docker-internal `0.0.0.0` with API-token guard but binds **host-side 127.0.0.1** only. Host `data/` must be writable by container UID 10001. Compose was not executed in this environment.

## 8. Alpha feature coverage

**Usable now:** responsive web dashboard, filtered discovery, editable symbol registry, deterministic Pullback/Breakout baseline, estimated turnover liquidity, explainable heuristic scoring, evidence and blocking reasons, custom AND/OR rules (nested rules at API), saved versioned screeners, watchlist, paper/manual journal, risk calculator, research historical replay, source/freshness labels, immutable signal log, 22 automated backend tests, optional Yahoo/Binance source adapters.

**Not yet delivered:** automatic full-market US/IDX discovery & comprehensive coverage, licensed exchange-level realtime streaming, independently verified trade-readiness, complete exchange listings/IDX rule timeline, corporate-action safe backtests across delisted universe, institutional-grade data QC, validated prediction ML and probability intervals, full mobile custom rule nesting, push notifications, scheduled jobs by market calendar, native APK, successful Flutter/Android CI run.

The original PRD is the **target specification**, not a claim that all 30 tasks or requirements are completed. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [docs/TASKS.md](docs/TASKS.md) for remaining work.

### Post-import quality check (v0.2.2-alpha)

IDX `.xlsx` imports no longer always take the alphabetically earliest symbols; with a cap smaller than the listing, a month-stable deterministic rotated candidate sample is selected. To refresh the IDX sample, rerun `python scripts/sync_universe.py --markets IDX --idx-file "$HOME/Downloads/<actual-filename>.xlsx" --idx-limit 35` and click Run Scan. The Data Health screen distinguishes missing history, data/provider errors, and liquidity exclusions; historical liquidity passing is **not** trade readiness.

## Local browser security / PWA cache (0.3.1 maintenance)

On `localhost`, `127.0.0.1`, and `::1`, the app does **not** register its PWA service worker. It unregisters an older `'/static/sw.js'` worker belonging to this origin (if present) and clears only `swing-static-*` app caches. Other site workers/caches are left alone. For a trusted HTTPS non-local origin, the PWA registration remains available. HTTP LAN/public origins do not register the worker.

This browser-cache change is **not** proof that a malware warning was a false positive and does not replace OS/browser security checks. If a warning recurs, do not bypass it; inspect the browser alert's source, extensions, requested URL and browser/OS security logs. An API response only confirms backend availability, not device integrity.

Run `node scripts/pwa_smoke.cjs` for isolated PWA policy checks, and `node --check web/app.js` / `node --check web/pwa.js` for syntax.


## Security hardening & Backtest V2 research update (2026-10-23)

Startup scripts `scripts/start.sh` and `scripts/start.bat` **never run pip install**. Install/update dependencies explicitly during a reviewed setup operation, not when clicking Run Scan. Existing `.venv` environments continue to work without reinstalling anything.

`GET /v1/backtests/{instrument_id}?strategy=PULLBACK&horizon=10` now has a bounded, non-overlapping, stop-first OHLC replay, 0.1% modeled friction per side, and chronological DEVELOPMENT vs HOLDOUT descriptive slices. Results stay `RESEARCH_ONLY`, `validated:false`, with metrics withheld for fewer than 20 completed trades. See [Backtest V2](docs/BACKTEST_V2.md).

Review [the macOS security audit](docs/SECURITY_AUDIT_2026-10-23.md): no source-level causal link to the OS popup was established. **Do not re-run LIVE scan solely to reproduce the warning**, or disable XProtect/Gatekeeper. Continue validation with offline fixtures and DEMO mode while the Mac alert remains unresolved.


## Historical Data Engine v1 (2026-10-23)

Research-only historical archive is available with immutable candle observations, per-source/basis revisions, SHA-256 integrity checks, first-observed timestamps, corporate-action evidence, read-only `/v1/history/*` API, and offline-default CLI.

```bash
python scripts/history_ingest.py --mode demo --limit 3
PYTHONPATH=backend python -m pytest -q backend/tests/test_history.py
```

Live provider capture requires a separate explicit `--mode live --allow-live` opt-in and must **not** be run on a machine still showing a macOS *Malicious Script Blocked* warning. Read [Historical Data Engine](docs/HISTORICAL_DATA_ENGINE.md) and [security review](docs/SECURITY_AUDIT_HISTORY.md). This first-observed archive does **not** certify historical point-in-time availability or realistic split-adjusted/raw fills.

For explicitly requested historical date ranges (ONLY after Mac security warning is resolved), see `scripts/history_ingest.py --help` and `docs/HISTORICAL_DATA_ENGINE.md`. The provider request remains capped at 2,500 candles per ingest with unverified adjustment basis.


## Replay from stored Historical Data Engine snapshots

Backtest Engine V2 can now replay **previously ingested observations** without calling Yahoo/Binance. The original `/v1/backtests/*` endpoint is unchanged. DEMO example:

```bash
python scripts/history_ingest.py --mode demo --limit 3
python scripts/archive_backtest.py --mode demo --instrument-id US:NASDAQ:MSFT --strategy PULLBACK
```

The asset details modal also has an **Archived backtest** button. Results identify `archive_snapshot.as_of_observation` and `archive_snapshot.sha256`; send both back to check against later revisions. Mode/basis mismatches and unsafe price gaps fail closed. This is **research-only**, NOT historical point-in-time certification or executable trading. See [Archived Backtest Integration](docs/ARCHIVED_BACKTEST_INTEGRATION.md).


## Historical Quality Audit v1 (2026-10-23)

Offline, read-only data-quality review (session-date recomputation, crypto continuity, weekday equity sanity, split-size jumps, optional bounded manual session lists and independent-source close comparison) is available via `python scripts/history_quality_audit.py --mode demo --instrument-id US:NASDAQ:MSFT --json` and private `GET /v1/history/quality/{instrument_id}`. Archived backtests reject blocking anomalies; no API accepts provider URLs or local calendar file paths. **Calendar, original vendor price basis, corporate actions, source independence and historical point-in-time availability remain unverified.** See [History Quality Audit](docs/HISTORY_QUALITY.md).


Research-only cross-source reconciliation: `python scripts/history_quality_audit.py --mode demo --instrument-id US:NASDAQ:MSFT --reference /path/to/local-evidence.json --json`. It requires explicitly supplied offline evidence, enforces observation cutoffs, and prints `evidence_sha256` for repeatable audits. See [History Quality](docs/HISTORY_QUALITY.md). No third-party agent installers or hooks are used; the `anti-slop` and `ponytail` source guidance informed minimal scope and plain comments only.


## Observed candidate universe (TSK-013 partial)

Current registry/discovery samples cannot prove who was listed historically. You can explicitly archive **current sampled membership** without a network request via `python scripts/universe_capture.py --mode demo`; Archived Backtest now reports per-bar `UNKNOWN_BEFORE_OBSERVATION`, `OBSERVED_CANDIDATE` and `UNKNOWN_NOT_IN_SAMPLE` counts and a separately pinnable universe evidence fingerprint. Nothing here certifies IPO/delisting timelines or removes survivorship bias. See [Historical Universe](docs/HISTORICAL_UNIVERSE.md).


## Test genuine internet market data (research only)

Use the opt-in [real market research GitHub Actions workflow](https://github.com/VaxXinE/personal-swing-trader/actions/workflows/real-market-research.yml) to check a real, bounded historical slice of MSFT (US), BBCA (IDX), and BTCUSDT (Binance Spot) on an isolated runner. It uses the existing LIVE providers rather than generating synthetic candles, and stores no third-party prices in Git or public Actions artifacts. To persist data locally, run the explicit `history_ingest.py --mode live --allow-live --instrument-id ... --start-date ... --end-date ...` commands documented in [Historical Data Engine](docs/HISTORICAL_DATA_ENGINE.md). Genuine provider data remains `VENDOR_UNVERIFIED` and backtests remain `RESEARCH_ONLY`.


IDX March 2026 historical holiday exception: the 17→25 March BBCA gap matches BEI-announced Nyepi/Eid closures (18–20, 23–24 March) and is now disclosed as a **partial reviewed closure** without claiming an exchange-certified full calendar. Long unexplained gaps continue to block the archived backtest. Real-data CI now researches seven assets across US, IDX and Binance; see [research quality documentation](docs/HISTORY_QUALITY.md).


### Real-data strategy funnel

After an explicit LIVE historical capture, use `python scripts/research_diagnostics.py --mode live --instrument-id US:NASDAQ:MSFT --json` to compare PULLBACK and BREAKOUT over the same archived snapshot. The research CI runs this on seven US/IDX/crypto datasets and reports multi-label setup, risk-gate and hypothetical next-bar-entry rejections. `trades=0` is data scarcity, not evidence of a successful or failed trading strategy. [Research Diagnostics](docs/RESEARCH_DIAGNOSTICS.md).


Baseline from the seven real-provider research jobs: [2026-10-25 real-market rejection funnel](docs/REAL_MARKET_FUNNEL_BASELINE.md). All 14 fixed strategy/asset combinations had zero qualified setups, with documented overlapping reason counts. This is an audit outcome, not a reason to weaken rules or claim strategy performance.
