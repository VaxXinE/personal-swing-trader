# TASKS — Implementation Backlog and Dependencies

**Status:** Alpha vertical slices exist; this remains the full target backlog. See [IMPLEMENTATION_STATUS](../IMPLEMENTATION_STATUS.md); do not mark tasks complete without all acceptance gates. Task IDs stable; use these IDs in code reviews, commits and agent prompts. A task is done only when its tests and docs are committed. `Priority P0` means MVP need; not permission to bypass dependency.

| Task | Milestone | Depends on | Deliverable / acceptance test |
|---|---|---|---|
| TSK-001 | M0 | — | Scaffold backend `pyproject`, Flutter app, folder boundaries, dev scripts, README; clean boot tests |
| TSK-002 | M0 | 001 | CI ruff/type/pytest/flutter format/analyze/test + fixture runners |
| TSK-003 | M0 | 001 | Auth/private API binding, config + secret handling + health endpoints; T-020 |
| TSK-004 | M0 | 001 | SQLite migrations/schema, repository interfaces, WAL writer; migration tests |
| TSK-005 | M0 | 004 | Local backup, encrypted backup plan + restore fixture; T-025 |
| TSK-006 | M1 | 004 | Instrument ID/alias/status registry; T-001 |
| TSK-007 | M1 | 006 | US/IDX/crypto calendars and market-rule versions; T-021/029 |
| TSK-008 | M1 | 006,007 | Canonical OHLCV/quote Pydantic contracts, QC, raw/adjustment flags; T-002 |
| TSK-009 | M1 | 008 | Yahoo research adapter + provider limiter/metrics; fixtures, pilot US/IDX |
| TSK-010 | M1 | 008 | Binance REST/WebSocket adapter with final kline and reconnect; T-003 |
| TSK-011 | M1 | 008-010 | Parquet atomic partitions, DuckDB query service, immutable manifests; integrity tests |
| TSK-012 | M1 | 009-011 | Provider pilot/data quality report and fallback UX; T-005 |
| TSK-013 | M2 | 007,011 | Liquid Universe with exclusions, as-of membership; T-004/005 |
| TSK-014 | M2 | 011 | Versioned technical feature library EMA/ATR/RVOL/ROC/structure; indicator fixtures |
| TSK-015 | M2 | 013,014 | Typed screener AST parser/validator/evaluator and resource limits; T-008 |
| TSK-016 | M2 | 015,004 | Screen configs/runs/snapshots immutable history and API; T-009/026 |
| TSK-017 | M3 | 014-016 | Pullback pure detector + fixtures; T-006/007 |
| TSK-018 | M3 | 014-016 | Breakout pure detector shifted resistance + fixtures; T-006/007 |
| TSK-019 | M3 | 017,018 | SQS component explanations, incomplete status; T-010/030 |
| TSK-020 | M3 | 019,013 | Eligibility gates, stable per-market rankings and dedupe; T-011/012 |
| TSK-021 | M3 | 007,020 | Trade plan and Decimal lot/fee/FX/cash position sizing; T-013/014/029 |
| TSK-022 | M4 | 016,019-021 | Flutter Home/Explore/Asset/detail + source/freshness states; T-019/027 |
| TSK-023 | M4 | 015,022 | Custom screener UI builder with validation and version-save |
| TSK-024 | M4 | 020,022 | Watchlist, idempotent alerts + original signal link; T-015 |
| TSK-025 | M4 | 021,024 | Manual/paper journal and position notes; T-016 |
| TSK-026 | M5 | 017-021 | Event-driven backtest fills, ambiguous barrier handling, fees; T-017/018 |
| TSK-027 | M5 | 026,016 | Walk-forward evaluation reports, baseline/cost sensitivities, audit exports |
| TSK-028 | M6 | 024-027 | Private session-aware EOD scheduler & forward paper run, incident runbooks; T-028 |
| TSK-029 | M7 | 027,028 | ML experiment, purged labels, calibration/evaluation; T-022/023 |
| TSK-030 | M7 | 029 | Forecast UI behind explicit validation gate + model registry and rollback |

## Working agreement

For each task: add `Implemented by`, `Commit`, `Tests run`, `Known limitation` in issue/PR record. Do not replace the table with “complete” unless a reproducible artifact exists. User may mark task blocked by data source and continue with isolated mock fixtures without pretending live coverage.

## Starter prompt for a coding agent

> Implement TSK-001 only from this documentation bundle. Read README.md, AGENTS.md, PRD.md, docs/ARCHITECTURE.md, docs/SECURITY.md and docs/TEST_PLAN.md first. Create maintainable Flutter + FastAPI scaffold with explicit domain/application/adapters separation; do not implement trading strategies or add external paid providers. Configure project tooling and a fixture-only smoke test, run the checks actually available, report results, and update CHANGELOG.md. Do not expose unauthenticated API publicly or hardcode secrets.
