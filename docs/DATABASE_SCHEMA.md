# DATABASE_SCHEMA — Durable App State & Immutable Research

**Status:** logical schema and SQLite-oriented DDL proposal; apply via migration tool, **not** as ad hoc CREATE during API startup. Historical OHLCV/feature matrices live in Parquet with immutable manifests.

## Storage policies

- SQLite WAL, one serialized writer, `PRAGMA foreign_keys=ON`, transactional migrations with schema version, consistent backup.
- Unique identifiers `TEXT` UUID/ULID. UTC ISO8601 timestamps with `Z` and lexicographically sortable canonical representation.
- Exact prices/monetary values **stored as decimal strings** (TEXT) and converted with Python `Decimal` at API boundary. **Do not SQL SUM/ORDER textual prices**; calculations happen with Decimal in domain or proper numeric analytical storage. Indicator feature arrays can use float64 Parquet with tolerance tests.
- Sensitive provider tokens never persisted here in plaintext. Secrets in OS keyring/environment/secret manager.
- Soft deletes/versioning rather than destructive removal of signals or fills; optionally compact derived cache only.

## Core tables

```sql
PRAGMA foreign_keys=ON;

CREATE TABLE instruments (
  id TEXT PRIMARY KEY,
  canonical_key TEXT NOT NULL UNIQUE,
  market TEXT NOT NULL CHECK(market IN ('US','IDX','CRYPTO')),
  asset_type TEXT NOT NULL,
  exchange TEXT NOT NULL,
  quote_currency TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE instrument_aliases (
  id TEXT PRIMARY KEY,
  instrument_id TEXT NOT NULL REFERENCES instruments(id),
  provider TEXT NOT NULL,
  external_symbol TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  UNIQUE(provider, external_symbol, valid_from)
);

CREATE TABLE instrument_status_history (
  id TEXT PRIMARY KEY,
  instrument_id TEXT NOT NULL REFERENCES instruments(id),
  status TEXT NOT NULL,
  board TEXT,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  source TEXT NOT NULL,
  available_at TEXT NOT NULL
);

CREATE TABLE market_rule_versions (
  id TEXT PRIMARY KEY,
  market TEXT NOT NULL,
  venue TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  source_url TEXT NOT NULL,
  rules_json TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE data_snapshots (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  data_through TEXT NOT NULL,
  manifest_uri TEXT NOT NULL,
  manifest_hash TEXT NOT NULL UNIQUE,
  quality_status TEXT NOT NULL,
  schema_version TEXT NOT NULL
);

CREATE TABLE universe_snapshots (
  id TEXT PRIMARY KEY,
  as_of TEXT NOT NULL,
  data_snapshot_id TEXT NOT NULL REFERENCES data_snapshots(id),
  universe_config_hash TEXT NOT NULL,
  included_count INTEGER NOT NULL,
  excluded_count INTEGER NOT NULL,
  results_manifest_uri TEXT NOT NULL,
  results_manifest_hash TEXT NOT NULL,
  UNIQUE(as_of, data_snapshot_id, universe_config_hash)
);

CREATE TABLE screener_configs (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version INTEGER NOT NULL,
  config_json TEXT NOT NULL,
  config_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  UNIQUE(name, version)
);

CREATE TABLE screener_runs (
  id TEXT PRIMARY KEY,
  screener_config_id TEXT NOT NULL REFERENCES screener_configs(id),
  universe_snapshot_id TEXT NOT NULL REFERENCES universe_snapshots(id),
  strategy_version TEXT NOT NULL,
  scoring_version TEXT NOT NULL,
  code_revision TEXT NOT NULL,
  evaluated_at TEXT NOT NULL,
  completed_at TEXT,
  status TEXT NOT NULL,
  result_manifest_uri TEXT,
  result_manifest_hash TEXT,
  error_code TEXT
);

CREATE TABLE setup_signals (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES screener_runs(id),
  instrument_id TEXT NOT NULL REFERENCES instruments(id),
  strategy_id TEXT NOT NULL,
  strategy_version TEXT NOT NULL,
  published_at TEXT NOT NULL,
  original_status TEXT NOT NULL,
  original_evidence_json TEXT NOT NULL,
  original_trade_plan_json TEXT,
  immutable_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE signal_events (
  id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL REFERENCES setup_signals(id),
  event_type TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  event_key TEXT NOT NULL UNIQUE
);

CREATE TABLE watchlist_items (
  id TEXT PRIMARY KEY,
  instrument_id TEXT NOT NULL REFERENCES instruments(id),
  strategy_id TEXT,
  note TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  added_at TEXT NOT NULL,
  UNIQUE(instrument_id, strategy_id)
);

CREATE TABLE journal_trades (
  id TEXT PRIMARY KEY,
  signal_id TEXT REFERENCES setup_signals(id),
  instrument_id TEXT NOT NULL REFERENCES instruments(id),
  trade_mode TEXT NOT NULL CHECK(trade_mode IN ('PAPER','MANUAL_ACTUAL')),
  trade_state TEXT NOT NULL,
  opened_at TEXT,
  closed_at TEXT,
  executed_qty TEXT,
  average_entry TEXT,
  average_exit TEXT,
  fee_total TEXT,
  currency TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE alerts (
  id TEXT PRIMARY KEY,
  signal_id TEXT REFERENCES setup_signals(id),
  event_key TEXT NOT NULL UNIQUE,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  sent_at TEXT,
  last_error TEXT
);

CREATE TABLE job_runs (
  id TEXT PRIMARY KEY,
  job_key TEXT NOT NULL UNIQUE,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL,
  lease_until TEXT,
  attempted INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  error_code TEXT
);

CREATE TABLE forecasts (
  id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL REFERENCES setup_signals(id),
  forecast_status TEXT NOT NULL,
  model_version TEXT,
  model_hash TEXT,
  published_at TEXT NOT NULL,
  forecast_json TEXT,
  validation_manifest_uri TEXT
);

CREATE TABLE observed_outcomes (
  id TEXT PRIMARY KEY,
  signal_id TEXT NOT NULL REFERENCES setup_signals(id),
  horizon INTEGER NOT NULL,
  horizon_unit TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  outcome_type TEXT NOT NULL,
  details_json TEXT NOT NULL,
  outcome_version TEXT NOT NULL,
  UNIQUE(signal_id, horizon, horizon_unit, outcome_version)
);

CREATE INDEX idx_signals_instrument_time ON setup_signals(instrument_id, published_at);
CREATE INDEX idx_signal_events_signal_time ON signal_events(signal_id, observed_at);
CREATE INDEX idx_runs_eval_time ON screener_runs(evaluated_at);
CREATE INDEX idx_status_instr_date ON instrument_status_history(instrument_id, effective_from);
```

SQLite `UNIQUE(instrument_id, strategy_id)` permits multiple rows with NULL strategy; application or a separate partial unique index must enforce desired watchlist dedup for null strategy. Use carefully tested migration for this; `CHECK(json_valid(...))` optional when SQLite JSON functionality confirmed.

## Parquet datasets

- Raw provider candles (immutable append/versions), curated canonical candles, computed features, universe inclusion/exclusion manifests, screener output, experiments, backtest trade ledgers.
- Manifest: `schema_version`, UTC created_at, `source`, `source_revision`, `row_count`, `partition_checksums`, `content_hash`, `data_through`, `calendar_version`, `price_basis`.
- Enforce storage size: compact partition after threshold, never delete referenced snapshot while a signal/backtest depends on it.

## Invariants and migrations

No UPDATE to `setup_signals.original_*` or existing `screener_configs.config_json`; append a new version. Enforce at repository layer plus optional SQLite triggers for immutable columns. Outcome is another table; no retroactively changing history. Use migration revisions, rollback instructions, backup before DDL, and DB integrity checks after restoration.

Query strategy: instrument/status/watchlist on SQLite; heavy longitudinal features on DuckDB Parquet; caches contain only derived records and can be rebuilt. Cache invalidation keyed by snapshot ID + code hash.

## Future optional tables

`economic_events`, `provider_request_logs` (no credentials), `feature_manifests`, `portfolio_position_events`, `model_registry`, `backtest_runs`, `backup_audit`. Define them when corresponding milestone begins; do not overbuild migrations before use.
