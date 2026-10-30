# OPERATIONS — Local/Private Runbook

**Status:** proposed operating procedures; commands are examples to adapt after scaffold exists. **Do not execute blindly on a machine holding secrets/data.**

## 1. Environment modes

`development`: mock feeds; SQLite tmp DB; test Parquet fixture; API binds localhost. `personal`: real approved personal-use feeds, encrypted/private local data volume, API private VPN, job schedule, notifications. `research`: separate datasets, model training isolated and no trade-alert promotion without manual review.

## 2. Boot sequence

1. Confirm Python/Dart toolchain versions from lockfiles, `.env` permissions, virtual environment, SQLite migrations.
2. Verify storage free space, data manifest readability and snapshot schema version.
3. Start backend API on loopback; start **one** scheduler instance and one bounded worker pool.
4. Check `/health/ready` with auth, provider budgets, latest committed snapshot, quote state.
5. Connect Flutter from authenticated VPN; UI must indicate source freshness.

Skeleton commands once packages exist (not runnable yet):

```bash
# example development workflow after scaffold
python -m venv .venv
source .venv/bin/activate
python -m pytest -q
# uvicorn app.main:app --host 127.0.0.1 --port 8000
# flutter run --flavor dev
```

## 3. Scheduler policies

- US: exchange-calendar close (NY local including DST/half days) + provider delivery buffer; don't hardcode 16:00 EST all year.
- IDX: official session close and settlement buffer; board-specific sessions and holidays.
- Crypto: UTC daily candle closing; kline `x=true` + REST reconciliation if needed.
- For all markets: job key `market+session_date+provider+job_version`, unique retry, lease, last success and freshness metric.
- Retry after transient outage with backoff but never publish scans against partial data.

## 4. Data incident runbooks

| Incident | Detect | Action |
|---|---|---|
| Provider 429/rate limit | HTTP status/job metric | backoff, reduce parallelism, last-good snapshot with STALE label |
| Quote older than SLA | `event_at` threshold | block execution-ready, refresh quote, show timestamp |
| Conflicting provider OHLC | checksum/delta QC | quarantine, investigate adjustment/timezone, don't choose silently |
| Bad corporate action | extreme jump audit | freeze affected signals; investigate raw vs adjusted basis |
| Incomplete crypto kline | `is_final=false` | wait; do not recalc EOD setup |
| SQLite locked | busy timeout retries | inspect multiple writers, serialize writes, never delete DB |
| Parquet partial write | manifest missing/hash mismatch | discard temp, restore previous committed snapshot |
| Push duplicated | duplicate event key | enforce uniqueness and idempotency |
| Unexpected public API | firewall scan/port access | stop API immediately, rotate tokens, examine logs |

## 5. Backups and restoration

- SQLite consistent backup via backup API or SQLite safe snapshot, **not** raw file copy while active without guarantees.
- Copy committed Parquet partitions + manifests referenced by DB in one versioned backup unit, encrypt at rest, keep separate device/offsite if available.
- Suggested baseline: daily metadata backup, weekly full snapshot, monthly restore test; adjust to storage cost/privacy.
- Restore procedure: stop writes → verify checksum and manifest → restore to **new** directory → run migrations as applicable → DB foreign key/integrity check → compare sample stored signals/manifest IDs → point private backend to restored path after confirmation.
- Secrets backed up separately in encrypted secret store; no plaintext `.env` inside archive.

## 6. Monitoring / alerts

Measure: `provider_last_success`, `final_candle_lag`, `missing_candle_count`, `scan_duration`, `scan_failure_rate`, `quotedata_stale_count`, `universe_size_by_market`, `alert_dedupe_count`, `disk_usage`, `backup_last_verified`. Internal data failures surface to user via Data Health, not push storms.

## 7. Upgrade and incident response

Pin dependency versions; staging/prototype with fixtures; before major provider/schema update take backup and run contract tests. If bad outputs published: freeze affected strategy version, mark relevant runs `RETRACTED` **as event**, preserve original records, send one correction alert to personal watchlist.

## 8. Data rights and retention

Private research usage still obeys provider terms/rate limits. Retain required datasets per provider contract; lifecycle cleanup must never delete audit snapshots referenced by published signals without explicit data retention decision.


## Verified recovery CLI — 2026-10-30 (TSK-005)

Run online SQLite backup **while the app is running**. This uses SQLite's backup API rather than copying a live `-wal` file. Captures `swing.db` and `history.sqlite` when present; the manifest contains SHA-256 and byte counts of both. Every snapshot is SQLite quick-check / foreign-key checked. An old `scripts/backup.py` invocation still creates a backup (now in a timestamped private directory rather than one `.db` file).

```sh
python scripts/backup.py
python scripts/backup.py --verify backups/swing-REPLACE_WITH_ACTUAL_FOLDER
python scripts/backup.py --restore backups/swing-REPLACE_WITH_ACTUAL_FOLDER --target /private/new-recovery-folder
```

For custom DB locations: `--db /absolute/path/swing.db --history-db /absolute/path/history.sqlite --backup-root /secure/local/path`. **Restoring requires a non-existent directory**; no active database is overwritten. Review restored DBs before configuring the app to use them. Files have owner-only permissions where the OS supports them. Integrity is checked again before and after copy. Run `PYTHONPATH=backend python -m pytest -q backend/tests/test_backup.py` for a restore drill including WAL, checksum corruption, path injection and overwrite refusal.

**Limitations:** These two SQLite snapshots are each consistent but not an atomic cross-database transaction. Backup includes no `data/discovered_universe.json`, external Parquet, secrets, mobile data or user-supplied CSV; archive those separately if applicable. Backups are **not encrypted by this script**; use an encrypted disk/volume and protect offsite transfers. It is not yet a full production disaster-recovery certification. Manual restore drills must be repeated against actual user data.
