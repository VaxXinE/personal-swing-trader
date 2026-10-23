# TEST_PLAN — Quality Gates and Acceptance Matrix

**Status:** planned tests, **not run**. Test fixtures must be synthetic or licensed/permitted; no live provider required in default CI.

## 1. Test pyramid

- **Unit (fast):** typed AST, EMA/ATR/RVOL edge cases, next-open fill, price/lot rounding, scoring rubric, deterministic ranking, state machine.
- **Property-based:** OHLC invariants, monotonic risk sizing when costs increase, correct rounding to steps, `sum_score <=100`, duplicate-free IDs.
- **Contract:** provider transforms, canonical timestamps/currency/adjustments, API Pydantic schemas, Flutter DTO parsing.
- **Integration:** SQLite migration and foreign keys, Parquet atomic commit+manifest, FastAPI auth, worker lease/idempotency, watchlist event dedupe.
- **End-to-end mobile:** Home→Explore→Asset→Watchlist→Journal; keyboard, dark/light, screen reader, offline/stale states.
- **Research:** walk-forward backtest, no-lookahead and survivorship warning, calibration/forecast feature gate.
- **Security:** auth negative, input fuzz, secret scan, SSRF deny-list/allowlist tests, rule AST resource limits.

## 2. Traceable acceptance cases

| Test ID | Covers | Fixture / expected behavior |
|---|---|---|
| T-001 | FR-001 | Same ticker different venues creates distinct canonical IDs |
| T-002 | FR-002 | Invalid OHLC/high-low/negative volume quarantined, never ranked |
| T-003 | FR-002/018 | Binance `x=false` kline cannot be used for EOD signals |
| T-004 | FR-003/004 | As-of universe/exclusions reproducible, historical IPO absent before listing |
| T-005 | FR-003/009 | No quote -> spread UNKNOWN -> not execution verified |
| T-006 | FR-005 | 20-day breakout resistance excludes signal candle |
| T-007 | FR-005/011 | After-close signal cannot fill at same completed close |
| T-008 | FR-006 | `eval`, unknown rule fields, mixed types, nested overflow rejected |
| T-009 | FR-007 | Updating saved screener creates new version; original run unchanged |
| T-010 | FR-008 | Score component points add to total; unknown input => incomplete |
| T-011 | FR-009 | High score + halted venue or stale spread => WAIT/UNKNOWN |
| T-012 | FR-010 | Stable sorting per market, duplicate underlying grouped appropriately |
| T-013 | FR-011/012 | IDR lot=100 and versioned tick rule applied; cap cash/risk |
| T-014 | FR-012 | Crypto quantity respects step/minNotional; USD/IDR conversion explicit |
| T-015 | FR-013 | Repeated worker event => exactly one recorded alert event |
| T-016 | FR-014 | Original signal hash does not change after observed outcome recorded |
| T-017 | FR-015 | Split/earnings publication timestamps prevent artificial signal leakage |
| T-018 | FR-015 | Same daily bar hits target & stop -> not counted target-first by default |
| T-019 | FR-016 | Flutter list/detail/empty/stale/errors pass widget/golden tests |
| T-020 | FR-017 | Unauthenticated remote API denied; secrets absent from app/assets/logs |
| T-021 | FR-018 | DST/IDX holiday/half session/crypto UTC day scheduler boundary correct |
| T-022 | FR-020 | NOT_VALIDATED forecast has **null** probability/price quantiles |
| T-023 | FR-020 | Purged temporal splitting prevents overlapped labels in train/test |
| T-024 | FR-022 | WS reconnect gaps trigger reconciliation, stale data badge shown |
| T-025 | NFR-005 | Restore backup recovers SQLite+Parquet manifest consistency |
| T-026 | NFR-001 | Identical snapshot+version+config => equal score/run hash |
| T-027 | NFR-007 | Screen reader identifies ticker/currency/status/timestamp without color |
| T-028 | NFR-008 | Job timeout emits traceable error and safely retriable lease |
| T-029 | FR-009/012 | IDX special-watch board cannot use continuous execution model |
| T-030 | FR-011 | No actual resistance: synthetic 2R target cannot earn structural validation |

## 3. CI gates

- Python `ruff check`, `ruff format --check`, typing (`mypy` or `pyright` once selected), `pytest`, package dependency lock integrity.
- Dart `dart format --output=none --set-exit-if-changed .`, `flutter analyze`, `flutter test`.
- Static secret scan and dependencies audit. Tests use mock HTTP and deterministic fixture clock; no expensive live web calls on every CI run.
- Migration up/down or forward+restore fixture; can boot sample app against empty DB.

## 4. Data quality sample suite

Include fixtures: suspended IDX share, special-watch board, split, rights, US DST transition, early-close session, illiquid coin spread spike, unsupported minimum notional, duplicate provider candles, delayed quote, missing holidays, a short-listed IPO, ambiguous barrier day, expired custom screener rule.

## 5. Quantitative evaluation checklist

- Separate `IN_SAMPLE`, `VALIDATION`, `OUT_OF_SAMPLE`, `FORWARD_PAPER` labels.
- Report costs, no-fill, gaps, benchmark, universe population, delisted coverage and confidence intervals.
- ML not promoted based solely on win rate; inspect Brier/log loss, calibration, quantile empirical coverage and baseline differences.
- Numeric score never labelled predicted probability.

## 6. Release checklist

- [ ] All P0 FR have passing acceptance test IDs.
- [ ] All major errors have visible UI behavior.
- [ ] Backup restore successfully performed on second temp directory.
- [ ] Negative auth and data-staleness tests pass.
- [ ] User can generate scan from finalized data and view source/score/risk breakdown.
- [ ] Signal stored with snapshot & code hash and observed outcome appended separately.
- [ ] All experimental claims marked explicitly; no forecast numbers pre-validation.
