# PRD — Product Requirements Document

**Product:** Personal Swing Intelligence · **Version:** 0.1 · **Date:** 2026-10-23 · **Status:** Target specification. Alpha implementation exists; see [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for honest coverage and limitations.

## 1. Problem dan solusi

Pengguna tunggal perlu menemukan peluang swing long-only dari tiga pasar tanpa bergantung pada banyak aplikasi, tetapi tidak ingin hasil berupa angka indikator tanpa konteks. Produk menyatukan discovery, validasi, risk planning, monitoring, dan outcome audit. Bukan rekomendasi pasti atau automated execution.

**Target persona:** developer/trader pribadi; memahami dasar saham/crypto; membutuhkan alasan yang bisa ditelusuri, UI mobile ringkas, detail teknikal on demand. **Primary job:** “Setelah candle selesai, tunjukkan peluang yang relevan, jelaskan mengapa dan apa yang membatalkan setup, lalu bantu gue memantaunya.”

## 2. Scope

**P0 / MVP**
- Universe US/IDX/crypto spot + pencarian simbol; historical and quote ingest beratribusi; final candle, market calendar, kualitas dan exclusion reasons.
- Preset screener Pullback dan Breakout; custom screener typed `AND/OR/NOT`, saved versions.
- Liquidity gates, scoring explainable, ranking by market, status candidate/ready.
- Risk & position sizing manual long-only; alerts/watchlist; mobile dashboard/asset detail.
- Audit sinyal dan paper trading journal sederhana; backtest point-in-time minimal.
- Private access, backup, tests, observability.

**P1 setelah P0 stabil:** historical replay UI, comparator parameter, quote streaming watchlist di pasar yang mampu, news/filings evidence, advanced journal, model-probability laboratory terpisah.

**GATED:** probabilitas target-first/stop-first dan price distribution **hanya ditampilkan jika validasi out-of-sample + kalibrasi lulus**. Sebelum itu tampil `NOT_VALIDATED` tanpa persentase.

**Out of scope:** real order placement; margin/short/futures; multi-user; social/sharing; public deployment; monetisasi; reversal strategy; guaranteed price targets; AI trade execution.

## 3. User journeys

- **UJ-01 Morning/evening scan:** Home → choose market/strategy → scan snapshot latest complete → inspect ranked list → detail supporting/contradicting factors → add watchlist.
- **UJ-02 Custom scan:** Screener → compose typed rules → validate → preview match count/exclusions → save version → run → compare results.
- **UJ-03 Manual trade plan:** detail → review status and freshness → view entry/stop/target, fees and sizing → mark planned/taken/skipped → journal actual trade.
- **UJ-04 Monitoring:** receive event alert → reopen fresh analysis → check if setup still valid → manually act or dismiss.
- **UJ-05 Historical accountability:** inspect original signal snapshot → see observed outcomes and benchmark; never retroactively edit initial result.

## 4. Functional requirements

| ID | Priority | Requirement | Acceptance (testable) |
|---|---|---|---|
| FR-001 | P0 | Registry + aliases US/IDX/crypto, asset type, venue and market status | No collision for identical symbols across exchanges; status tracked as-of |
| FR-002 | P0 | Ingest OHLCV with provider, UTC timestamps, final flag and QC | Duplicate/invalid OHLC rejected or quarantined |
| FR-003 | P0 | Liquid universe with market-specific rules and rejected reason | Result reproducible by timestamp & config version |
| FR-004 | P0 | Search/browse included and excluded instruments | Excluded visible with reason; never falsely labelled Ready |
| FR-005 | P0 | Detect Trend Pullback / Breakout on finalized candles | Golden fixtures pass; no current bar leakage into prior lookbacks |
| FR-006 | P0 | Custom rule builder with nested boolean ops and whitelist | Invalid field/operator/type rejected; no `eval`/SQL concatenation |
| FR-007 | P0 | Save/version screeners, rerun on snapshots | Prior run remains unchanged after rule edits |
| FR-008 | P0 | Explainable scoring per strategy 0–100 | Component breakdown sums; incomplete has no numeric rank |
| FR-009 | P0 | Trade eligibility gates separate from score | Unknown data/quotes cannot yield EXECUTION_VERIFIED |
| FR-010 | P0 | Rank per market+strategy; stable ties and dedupe | Same dataset/config always same order; global mix no false comparability |
| FR-011 | P0 | Trade-plan entry/stop/target/R:R with fees assumptions | Levels valid, executable rounding, target rationale recorded |
| FR-012 | P0 | Position sizing for US/IDX/spot, lot/tick/step constraints | Never exceeds cash/risk/exposure; invalid inputs rejected |
| FR-013 | P0 | Watchlist, single event alert and status lifecycle | Idempotent notifications; invalidation appears even if initial score high |
| FR-014 | P0 | Original signal ledger and paper journal | Immutable signal snapshot; subsequent outcome separate record |
| FR-015 | P0 | Replay/backtest with explicit execution assumptions | OOS timeline integrity tests pass |
| FR-016 | P0 | Flutter navigation Home/Screener/Asset/Watchlist/Journal | Loading/empty/stale/error/accessibility tested |
| FR-017 | P0 | Private API; authorization, input validation, secrets management | Unauthorized network client blocked; no secrets in app build |
| FR-018 | P0 | Scheduler by exchange session + crypto UTC day | Jobs do not scan incomplete candle; idempotent retries |
| FR-019 | P1 | Fundamental/event evidence | As-of published time, source link, no invented factor |
| FR-020 | GATED | Calibrated forecast distribution and barrier probabilities | Validation card + sample & period; gate fails closed |
| FR-021 | P1 | Searchable historical signals, replay, comparisons | Point-in-time features and strategy versions preserved |
| FR-022 | P1 | Real-time quotes where provider available | Stream reconnect/backfill/STALE UX verified |

## 5. Non-functional requirements

| ID | Requirement | Acceptance |
|---|---|---|
| NFR-001 | Reproducibility | SHA/config/data snapshot links for every run |
| NFR-002 | Trust and freshness | Every displayed market field has `as_of`, `source`, `freshness`, `quality` |
| NFR-003 | Portability | Works local Linux/macOS for backend, Android for app; no mandatory managed cloud |
| NFR-004 | Security | VPN/private binding default, least privilege, no public anonymous API |
| NFR-005 | Recoverability | Successful backup + restore drill with checksums |
| NFR-006 | Performance | Cached result list opens without recomputing whole universe; load testing sets actual SLO |
| NFR-007 | Accessibility | Labels, text scaling, 44px+ touch targets target, contrast and non-color statuses |
| NFR-008 | Observability | Structured job logs, error categories, healthcheck, data lag metrics |
| NFR-009 | Cost control | No mandatory paid feed; clear degraded mode when provider unavailable |

## 6. Release gates

**Alpha:** FR-001–012, FR-015, FR-017–018 verified on fixtures; UI basic displays results. **Personal Beta:** FR-013–016 + recovery drill + multi-week paper logging, no false-live labels. **Forecast Lab:** FR-020 only upon research validation; no production activation by schedule alone.

## 7. Dependencies / known blockers

- Availability and permitted use of data vendor endpoints varies; check provider terms before production operation.
- Live US/IDX bid-ask, IDX official turnover and historical point-in-time board membership may not be available from free sources; these capabilities must gracefully degrade.
- Full survivorship-bias-free backtest requires delisted instrument history and lifecycle data. If absent, report **limited-universe backtest**, not full-market proof.
- Paper fills are estimates, not real broker execution.

## 8. Traceability

See [TRACEABILITY](docs/TRACEABILITY.md), [TEST_PLAN](docs/TEST_PLAN.md), [ROADMAP](docs/ROADMAP.md). Modification of an FR ID requires corresponding tests/doc update.
