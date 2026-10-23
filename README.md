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

The launcher installs backend dependencies into `.venv/`, runs the local API on **127.0.0.1:8000**, and serves the fully functional responsive web application at:

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
