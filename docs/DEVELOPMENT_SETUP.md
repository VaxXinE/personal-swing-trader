# DEVELOPMENT_SETUP — First Sprint Implementation Guide

**Implementation note (2026-10-23):** Runnable alpha source now exists in this repository. For actual startup read [README](../README.md), and check [IMPLEMENTATION_STATUS](../IMPLEMENTATION_STATUS.md). The guidance below is retained as original scaffold acceptance baseline, not as current implementation state.

## 1. Preflight (choose installed stable releases at implementation time)

- Flutter stable channel, Android SDK + emulator, Dart analyzer; Python supported stable release (prefer ecosystem-compatible version, not bleeding-edge), Git, Docker optional.
- Package management: Python `uv` or `pip`+lockfile, Dart `pubspec.lock`; pin versions after initial compatibility check.
- Test & lint: `pytest`, `ruff`, `mypy` or `pyright`, `flutter test`, `flutter analyze`, secret scan.
- Do not introduce paid services or Kubernetes for M0.

## 2. Monorepo target

```text
swing-intelligence/
├── README.md                # link to this blueprint
├── AGENTS.md
├── PRD.md
├── goal.md
├── design.md
├── docs/                    # all other specifications
├── apps/mobile/             # Flutter package
├── backend/
│   ├── pyproject.toml
│   ├── src/swing_intelligence/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── ports/
│   │   ├── infrastructure/
│   │   ├── api/
│   │   └── workers/
│   └── tests/
├── research/                # experiments with immutable manifests
├── data/                    # gitignored; historical/private data
├── scripts/
└── .github/workflows/
```

## 3. Initial `TSK-001` acceptance steps

1. Create Python package and FastAPI `/health/live` (loopback-only) with minimal dependency injection and config loaded safely, not debug-on by default.
2. Create Flutter shell with four placeholder tabs and explicit non-live fixture label.
3. Add pure domain hello/instrument type and one test to prove it imports without FastAPI/SQLite.
4. Add mock provider and deterministic fixture clock; no network calls needed to pass tests.
5. Add `.gitignore` entries for `.env`, database files, API credentials, Parquet, model artifacts, build caches, platform key stores.
6. Add minimal CI lint/format/test jobs and README local commands.
7. Run checks and report **actual output**; document anything untested.

## 4. Suggested first vertical slice after scaffold

`instrument registry → mock candles → QC → one completed data snapshot → deterministic feature → private GET endpoint → simple Flutter card showing EOD label`. Only then add actual market providers.

## 5. Boundary contract

Domain layer may import Python stdlib/NumPy utilities but not FastAPI, HTTP clients, or SQLite. API endpoints must call application services. No trade placement module included. Keep all sample prices clearly dummy data.

## 6. Developer safety

Environment variables and examples use fake strings and bind to localhost. Use Tailscale/identity-aware private tunnel for remote phone access, with separate session validation. Do not expose `uvicorn --host 0.0.0.0` unless protected by correctly configured network and authorization. Test device connection using a known mock endpoint, not real brokerage credentials.
