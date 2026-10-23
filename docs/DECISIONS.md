# DECISIONS — Architecture Decision Record (ADR) Log

**Purpose:** menjaga semua agent/developer mengacu keputusan terbaru tanpa mengubah aturan diam-diam.

Format untuk keputusan baru: `ADR-ID, date, status, context, options, decision, consequences, migration/affected docs`.

## Locked decisions

### ADR-001 — Personal single-user private app (2026-10-23, ACCEPTED)
**Context:** hanya satu developer/user. **Decision:** no SaaS, auth multi-tenant, billing, shared accounts. Backend remains private/authenticated. **Consequences:** simple infrastructure; user data localized; still need security and backups. Affects PRD, SECURITY, ARCHITECTURE.

### ADR-002 — Long-only spot, manual execution (2026-10-23, ACCEPTED)
**Decision:** long equity and crypto spot only; no auto execution, derivatives, leverage, borrow, short. **Consequences:** no brokerage write permissions; journal includes manual fills. Affects STRATEGY, RISK, API, PRD.

### ADR-003 — Three markets and daily-first swing (2026-10-23, ACCEPTED)
**Decision:** US Stocks, IDX equities, crypto spot; daily finalized candles for signal; intraday support informational/late phase. Stocks H units = exchange sessions; crypto H = UTC calendar days. **Consequences:** per-market calendars; no cross-market time assumption.

### ADR-004 — Broad discovery + liquid default (2026-10-23, ACCEPTED)
**Decision:** visible excluded universe and reasons; no arbitrarily limiting discovery to top 10; strict Trade Ready eligibility. **Consequences:** distinct discovery, score, readiness and execution gates.

### ADR-005 — Start with Trend Pullback and Breakout (2026-10-23, ACCEPTED)
**Decision:** Reversal and advanced indicators not MVP. **Consequences:** explainable and testable strategy baseline; parameter values still proposed, not validated.

### ADR-006 — Modular Python monolith + Flutter (2026-10-23, ACCEPTED)
**Decision:** Flutter Android, Python/FastAPI, SQLite, Parquet + DuckDB, bounded workers and local/private VPN. No early Kafka/Kubernetes. **Consequences:** minimal ops, single-writer SQLite architecture.

### ADR-007 — Score is not probability (2026-10-23, ACCEPTED)
**Decision:** `Setup Quality Score` separate from calibrated forecast; liquidity as hard gate, not a score booster; rankings per market/strategy. **Consequences:** avoid fabricated predictive claims.

### ADR-008 — Forecast gated until validated (2026-10-23, ACCEPTED)
**Decision:** null probabilities until OOS evaluation/calibration and explicit promotion. **Consequences:** functioning application can launch without predictive model; UI shows NOT_VALIDATED.

### ADR-009 — Append-only signal audit (2026-10-23, ACCEPTED)
**Decision:** original thesis and market data snapshot immutable; corrections/outcomes appended as events. **Consequences:** extra storage but trustworthy retrospective analysis.

### ADR-010 — Provider and venue rules are versioned (2026-10-23, ACCEPTED)
**Decision:** no timeless hardcoded price fractions, fees, calendars; data from vendor with provenance and as-of version. **Consequences:** cost of metadata upkeep and honest unknown state.

## Proposed, not locked

### ADR-011 — Liquidity baseline parameters (PROPOSED)
Initial ADV20 US 10m USD, IDX 10b IDR, crypto 10m USDT; quote spread heuristics; verify using measured spreads and strategy execution. Changing these thresholds creates versioned config + backtest sensitivity, **not** arbitrary silent tweak.

### ADR-012 — Risk budget 0.5% per trade / 2% aggregate (PROPOSED)
Research default, personal setting adjustable. Not an absolute max loss due to gap/slippage. Require portfolio cash checks.

### ADR-013 — Exchange/custody choice (OPEN)
Crypto initial reference Binance public pairs, not broker commitment; operational availability, venue and asset purchasing method TBD. Personal broker/exchange specific order rules loaded only after choice.

## Change protocol

1. New decision requests specify affected FRs, strategy versions, data lineage and tests.
2. State becomes ACCEPTED only after explicit user agreement for fundamental product-scope changes; parameter experiments stay PROPOSED until measured.
3. Update `DECISIONS`, corresponding domain spec, `PRD`, traceability, tests and `CHANGELOG` **in one change**.
4. Superseded entries preserved with link to replacement, not deleted.
