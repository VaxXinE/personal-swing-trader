# Personal Swing Intelligence — Personal Research Beta release gate

**Assessment date:** 2026-10-30  
**Disposition:** **RESEARCH-ONLY BETA CANDIDATE**; **NO-GO** for statistically validated trade signals, execution-ready recommendations, public hosting, or unattended production trading.

This document is an evidence-based release assessment, not an assertion that the complete PRD, M0–M7 roadmap, or market validation is finished. The product is designed as private single-user decision support; there are no broker order endpoints.

## Verified engineering evidence

- Main branch before this gate record: `d2db583`. Backend CI: **155 passed, 1 compatibility warning** in [GitHub Actions](https://github.com/VaxXinE/personal-swing-trader/actions/runs/40999088145). Android build outcome must be checked from that run separately; CI compilation is not a physical-device usability test.
- The seven real provider series in [real-market baseline](REAL_MARKET_FUNNEL_BASELINE.md) and [period-stability report](REAL_MARKET_PERIOD_STABILITY.md) show **zero qualified strategy setups** across 1,505 eligible signal bars *per strategy*. Those are historical exploratory observations, not independently validated trade signals. Never replace missing trades with synthetic wins.
- The historical archive has source/basis labels, checksums, revisions, structural QC, partial IDX holiday review and an observed candidate roster. It does **not** certify official full exchange calendars, historical delisted universe, RAW tradable price, provider publication times, independent adjustment series, or survivorship-free replay.
- TSK-005/NFR-005 now has a local offline recovery drill for SQLite journal and history database via `scripts/backup.py`. Tests cover active WAL commits, two-database restore, checksum mismatch, symlink refusal, manifest path injection and overwrite protection. Real-user encrypted off-device restore is **not** attested.

## Feature gates

| User goal | Current disposition | Release condition |
|---|---|---|
| Private DEMO screener and asset explanation | **Usable with fixture limitations** | Smoke test on user's machine; display DEMO conspicuously |
| Real-data discovery and EOD research | **Research-only** | Approved provider use, finality/freshness confirmation, independent spot checks, bad-source fallback |
| Watchlist, risk sizing and paper journal | **Local baseline** | Manual Android navigation, local storage/recovery and accessibility acceptance |
| Archived PULLBACK/BREAKOUT | **Diagnostic-only** | Full source/adjustment/calendar/PIT checks and unbiased multiyear prospective protocol |
| Forecast probabilities | **Blocked by design** | Measured OOS and forward paper calibration above pre-registered baselines |
| Automated live execution or public access | **Not part of scope** | Separate architecture/consent/security/legal review (not enabled here) |
| 24/7 EOD scheduler and automatic alerts | **Not signed off** | TSK-028 idempotency, market-session/DST, outage and delivery tests |

## Run the reproducible local acceptance checks

From the repository root, with explicitly installed dependencies and activated `.venv`:

```bash
git pull --ff-only origin main
python scripts/doctor.py
PYTHONPATH=backend python -m pytest -q backend/tests
python scripts/server_smoke.py
node --check web/app.js
python scripts/backup.py
```

The last command creates an owner-private **unencrypted** directory in `backups/`; it requires an existing `data/swing.db`. Copy the exact backup directory name from output, then:

```bash
python scripts/backup.py --verify backups/ACTUAL_BACKUP_DIRECTORY
python scripts/backup.py --restore backups/ACTUAL_BACKUP_DIRECTORY \
  --target data/restore-drill-20261030
```

The restore target must **not** already exist. Do not point it to the active `data/` files or overwrite active SQLite databases. Keep `backups/` on encrypted storage, never in Git or a public artifact. Stop application writes and do a separate operator-supervised recovery drill before any actual migration. This archive covers SQLite databases, **not** unrelated Parquet/config/external files or secrets.

For the browser workflow, launch DEMO on loopback:

```bash
SWING_DATA_MODE=demo bash scripts/start.sh --port 8001
```

Manually verify: Run Scan → Opportunity Explorer → asset detail → Archived backtest → Watchlist → Paper/Manual Journal → Data Health. Test empty/loading/error/stale states on narrow Android screen and physical-device navigation. Do not call this gate passed just because `flutter build apk` succeeds.

## Go/no-go acceptance remaining

1. **Mandatory before personal beta sign-off:** full data backup/restore drill using a *copy* of actual private data; Android physical-device workflow and accessibility checks; auth and token rotation tests against intended VPN/private topology; dependency/security scan and documented restore operator.
2. **Mandatory before using trade signals for decisions with claimed reliability:** complete versioned exchange calendars; corporate actions and independently checked price adjustment; historical lifecycle/delisting and universe sampling policy; executable lot/tick/cost assumptions; a pre-registered out-of-sample + multi-week forward-paper protocol that produces sufficient **actual qualified trade** observations.
3. **Optional or gated:** calibrated ML forecasts, real-time quote streaming, advanced news/fundamental features, automatic order execution. Forecast UI must remain `NOT_VALIDATED` until its independent release gate is fulfilled. No ROI/win-rate estimates from the current zero-trade sample.

The unresolved macOS security alert does not prevent improving tests and the isolated cloud research workflow, but this project cannot declare the affected Mac secure or advise disabling its protections. A dedicated local diagnostic and supply-chain review is still needed for local LIVE use.

## Development constraints

Follow the repo's `AGENTS.md` and ADRs. Applied **Anti-Slop** (comments only where they explain non-obvious constraints; no decorative code) and **Ponytail** (reuse SQLite backup API and existing CI; no extra infrastructure, ORM, background daemon or code copied from those third-party skills). Keep tests and behavior intact.
