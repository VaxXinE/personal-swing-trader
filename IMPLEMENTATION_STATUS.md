# Implementation Status — Alpha 0.2.2

**As of:** 2026-10-23. This tracks features honestly relative to `PRD.md`. Data in demo mode is fictional; trading probabilities are gated off.

| Area / FR | Status | Evidence / Remaining work |
|---|---|---|
| FR-001 Instrument registry | PARTIAL | `config/universe.json`, validated up to 250 instruments; lacks historical aliases, listing-state timelining and dynamic full exchange discovery |
| FR-002 Data ingest/QC | PARTIAL | strict OHLC validation, UTC final candles in live adapters; source-specific corporate-action adjustment and QC pipelines pending |
| FR-003/004 Liquid universe & exclusions | PARTIAL | ADV20 / median / price gates, exclusion reasons; no complete live IDX status or true point-in-time membership |
| FR-005 Two strategies | IMPLEMENTED (baseline) | deterministic pullback and breakout code with shifted resistance and tests; no claim of strategy profitability |
| FR-006 Rule AST | IMPLEMENTED | recursive AND/OR/NOT, field whitelist, three-valued UNKNOWN, numeric bounds and depth limits |
| FR-007 Saved screener versions | IMPLEMENTED (local) | SQLite append-only version records; API/UI simple rule builder, full nesting via API |
| FR-008 Score explanation | PARTIAL | 5-part rubric and evidence; relative strength and independent regime data unavailable -> partial context score |
| FR-009/010 Eligibility/ranking | PARTIAL | explicit no execution verification, stable per-market sorted research list; no cross-market calibrated ranking |
| FR-011 Trade plan | PARTIAL | structural levels / hypothetical 2R labelled; actual exchange tick histories and fill convention verification pending |
| FR-012 Position sizing | PARTIAL | Decimal/risk/exposure/IDX whole lot, US whole shares, approximate crypto precision; no real broker order-step/FX validation |
| FR-013 Watchlist/alerts | PARTIAL | persistent watchlist; push alerts and status-event notification absent |
| FR-014 Signals/journal | IMPLEMENTED (basic) | immutable SQLite snapshot, paper/manual journal with realized P&L if exit provided; trade analytics pending |
| FR-015 Backtesting | RESEARCH LAB | next-bar simulation, stop-first intrabar ambiguity, fees; OOS, survivors, corporate actions, traded value history pending |
| FR-016 Flutter UI | SOURCE READY / UNVERIFIED BUILD | Material 3 four-tabs, detail, watchlist, journal, basic custom builder; Liquid Universe toggle. Flutter SDK unavailable here. GitHub Actions template created but not executed. Responsive web UI tested separately. |
| FR-017 Private API | PARTIAL | loopback default, bearer token required for non-loopback startup, input validators. HTTPS/VPN configuration user's responsibility. |
| FR-018 Scheduler | PARTIAL | manual `scan_once.py` works, OS scheduling can be configured; no fully correct session calendar orchestration |
| FR-019 Fundamentals/news | NOT IMPLEMENTED | only technical features. Do not represent scoring as including actual fundamental/news evidence |
| FR-020 Probabilistic forecasts | BLOCKED / NOT VALIDATED | null probabilities and visible validation warning; research, calibration, rollback pending |
| FR-021 History/replay UI | PARTIAL | run list, signal snapshot endpoint, basic replay endpoint; historical as-of app explorer pending |
| FR-022 Live quotes/WebSocket | NOT IMPLEMENTED | Binance bookTicker at live fetch only; EOD signals. Do not label equity quotes realtime |

## Executed verification

- Backend: `pytest` tests include data QC, no-lookahead resistance, rule AST and `UNKNOWN`, auth guard, journal, SQLite saved configs, forecast gate and risk sizing.
- Browser UI: Chromium rendering with mocked API payloads, checked DOM, asset detail and no uncaught page errors. Server-backed Chromium page navigation was blocked by test environment policy; loopback API verified separately through real HTTP smoke checks.
- Node: `node --check web/app.js` syntax verified.
- Flutter/Android: **not executable/tested in build environment** (SDK + Android SDK absent). Source included with a platform bootstrap script.
- Docker: not tested; container engine unavailable.

## Recommended implementation order from here

1. Run the app locally and test live provider connectivity + completeness on 10–20 chosen assets.
2. Test Flutter on Android emulator and physical phone; fix platform integration issues and freeze lockfile.
3. Implement market status / timestamp-aware corporate actions and replace illustrative IDX and crypto order rules with official effective-dated rules.
4. Add independently sourced bid/ask/session checks and mark trade-ready only when all gates pass.
5. Create unbiased historical universe/strategy backtesting with forward OOS tests.
6. Only then consider ML probabilities, calibration and alert automation.

## v0.1.1 verification supplement

- `python -m pytest -q backend/tests`: 22 passed (including settings-regression tests).
- `python scripts/server_smoke.py`: passed, 38 synthetic strategy evaluations over 19 instruments, 0 provider errors.
- `python scripts/ui_smoke.py`: passed on 1440x900 and 390x844 Chromium with mocked API and no JavaScript page errors.
- `python scripts/doctor.py`: passed essential runtime/config checks.
- `node --check web/app.js`: passed.
- `python scripts/browser_e2e.py`: **blocked** by environment browser `ERR_BLOCKED_BY_ADMINISTRATOR`; not counted as passed.
- PWA install metadata and GitHub Android build workflow: files included, **not validated on a physical phone nor in GitHub CI**.

## 2026-10-23 — Market timestamp provenance hotfix

- Yahoo daily equity rows carry a trading-session date, not a trustworthy precise last-trade timestamp. Previously the conservative readiness guard (17:00 America/New_York / 16:30 Asia/Jakarta) was reused as the candle close timestamp. Now it is a separate guard from the **derived normal-session close marker** (US 16:00 ET; IDX 16:02 WIB after regular closing matching).
- Every new setup includes `candle_metadata`: `timestamp_basis`, `finality_basis`, `last_session_date`, `age_hours_at_scan`, `validation_scope`, and `calendar_validated=false`. These are explicit limitations, not a claim of verified live quotes. Data Health shows market coverage and timestamp provenance.
- This is a partial safety fix, not a complete official session calendar. Early close/holidays and provider latency need dedicated calendars and point-in-time sources. Existing SQLite signal/run snapshots remain intentionally unchanged; re-run scanner to produce new metadata.

## v0.2.0 Dynamic Universe supplement (2026-10-23)

- US: Nasdaq Trader directory parsing and bounded month-rotating sample; **not full market / not liquidity-ranked**.
- Crypto: Binance active USDT spot candidates sorted by rolling 24h quote volume, then historical ADV20 scanned.
- IDX: direct official XLSX import (CSV remains supported), no undocumented API or misleading full auto-coverage. File-format unit tests pass; real export compatibility should be verified locally.
- `data/discovered_universe.json`: local atomic snapshot, partial failure retains existing market; manual config wins on duplicate IDs; demo isolated; cap 250 total.
- API GET `/v1/universe/discovery`, per-market `coverage` in scan results and Data Health panel.
- Explorer grouped into one card per asset (best matched setup) with strategy breakdown; cross-market results still separate rather than ranking uncalibrated scores together.
- LIVE provider EOD successful reads are cached in memory for 15 minutes. Not realtime. Scanning is still sequential.
- Offline parser/sync regression tests: **35/35 backend tests**, HTTP smoke and mock browser UI smoke passed locally. Provider connectivity after deployment not yet verified.
- **Outstanding:** IDX official historical trading status, Nasdaq directory candidate liquidity prescreen, provider batch calls, full historical point-in-time universe, production Android build, probability validation, session-calendar aware scheduler.

## v0.2.1 — IDX Excel import

- Import .xlsx or .csv for IDX using `--idx-file`, with bounded OOXML parsing and no extra pip dependency.
- Workbook data never executes Excel formulas/macros; failures preserve the last valid discovery snapshot.
- Verification: 41 backend tests passed in this environment (35 previous + 6 XLSX tests). No live IDX workbook was provided for integration testing.

## v0.2.2 post-import audit (2026-10-23)

- IDX selection no longer arbitrarily prioritizes A-prefix codes from alphabetical official exports. New sync performs repeatable calendar-month candidate rotation across the validated source listing. This is an exploration sample, **not** liquidity ranking or proof of active tradability.
- `coverage.liquidity_passed` and `coverage.insufficient_history` count instruments, distinct from 2-per-asset strategy evaluations. Scan rejections from under 60 complete daily candles have `INSUFFICIENT_HISTORY` category; existing `errors` field retained for compatibility.
- Data Health changes 'Provider Errors' to 'Scan Failures' and shows historical liquidity-pass counts. `README.md` explains that sync must be rerun to refresh saved local universe.
- Tests: 43 backend passed, HTTP demo smoke passed, Node syntax passed. Actual live Yahoo/Binance feed and production exchange suitability not yet verified by this patch.
