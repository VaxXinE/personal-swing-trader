# SCORING_RANKING — Explainable Ranking V0.2

**Status:** scoring allocation **BASELINE**; score is **not** calibrated probability, win rate, expected return, or advice.

## 1. Separation of concerns

**Eligibility** decides whether data & execution conditions permit decision; **Setup Quality Score (SQS)** summarizes pattern strength; **Entry Readiness** orders attention among valid candidates; **Prediction** (when separately validated) estimates probabilistic outcomes. A score of 95 with stale quote still yields `WAIT/UNKNOWN`.

## 2. Score composition

| Dimension | Max pts | Examples of observables |
|---|---:|---|
| Trend Quality | 25 | EMA ordering/slope, relative strength |
| Setup Structure | 30 | Pullback zone, base/resistance, valid bar structure |
| Momentum & Volume | 15 | RVOL, candle close strength, ROC |
| Risk/Reward Geometry | 20 | Stop grounded in structure, distance, achievable *structural* upside vs downside |
| Market Regime Alignment | 10 | market benchmark trend & volatility |
| **Total** | **100** | no liquidity points: liquidity is separate hard gate |

Every component is sum of **documented deterministic subrules** returning `points_earned`, `points_possible`, `observed_value`, `threshold`, and `reason_code`. No LLM-generated score.

### Proposed baseline subrule rubric

- Trend (25): close>EMA50 **7**, EMA20>EMA50 **7**, EMA50 5-bar slope positive **6**, relative strength vs **market-specific** benchmark positive **5**.
- Pullback structure (30): proximity to EMA/support **10**, reasonable pullback depth vs ATR **8**, higher-low structure **7**, confirmed reclaim **5**.
- Breakout structure (30): historic resistance quality **10**, 20-bar consolidation **8**, breakout close after buffer **7**, not extended **5**.
- Momentum/volume (15): RVOL relative to past 20 **7**, strong candle close location (`(Close-Low)/(High-Low)`) **5**, aligned ROC **3**.
- Risk geometry (20): meaningful nontrivial structural stop **7**, structural target quality **7**, **net** R:R at least threshold **6**. An arbitrary 2R target may **not** earn structural target points.
- Market regime (10): market benchmark trend **6**, market volatility acceptable **4**; benchmark: US SPY or broad-market proxy, IDX IHSG proxy, crypto BTC/total-market proxy (BTC scored against independent aggregate if available).

For continuous features, define score bins in a versioned table, e.g. RVOL: `<1=0`, `[1,1.5)=3`, `[1.5,2)=5`, `>=2=7`; cap extreme values. All bins are initial hypotheses. Keep strategy/version-specific reasons to prevent indicator double-counting; evaluate correlation before changing rubric.

## 3. Incomplete evidence

A dimension can be `VALID`, `UNKNOWN` or `INAPPLICABLE`. Never silently treat unknown as zero or reallocate its weight. If required input missing, score state is `INCOMPLETE`, numeric score `null`, excluded from standard rank. Optional contextual fundamental/economic events are evidence overlay; lack of news feed cannot create a fake negative technical score.

```json
{
  "score": 85,
  "score_type": "SETUP_QUALITY",
  "score_version": "SQS_V0_2",
  "score_status": "COMPLETE",
  "components": [
    {"name":"trend","earned":23,"max":25,"reason_codes":["EMA_ORDER_OK"]},
    {"name":"structure","earned":25,"max":30},
    {"name":"momentum_volume","earned":12,"max":15},
    {"name":"risk_geometry","earned":16,"max":20},
    {"name":"market_regime","earned":9,"max":10}
  ],
  "probability_win": null
}
```

Illustrative only. A test must assert `score == sum(earned)` and `max == 100` for COMPLETE.

## 4. Entry readiness & statuses

Status is independent from numeric score:

| State | Meaning |
|---|---|
| `DISCOVERED` | raw pattern found |
| `QUALIFIED` | valid inputs and basic historical liquidity |
| `WATCH` | setup promising, entry not confirmed or gate incomplete |
| `READY` | all defined ready gates pass; human decision remains |
| `TRIGGERED` | confirmed price condition after READY; check quote freshness |
| `INVALIDATED` | strategy thesis broken; show reason |
| `EXPIRED` | window elapsed; must rescan |
| `UNKNOWN` | missing evidence to make decision |

Entry readiness is a **nonprobabilistic** 0–100 ordered heuristic for candidates with score COMPLETE, weighted to trigger proximity (within valid range), confirmation age and remaining validity. Define zero at invalidation, not as a weak buy recommendation. Invalidated assets never appear in `Trade Ready` regardless of number.

## 5. Eligibility policy

`TRADE_READY = complete_valid_data AND historically_liquid AND supported_board/market AND confirmed_strategy AND trigger_still_valid AND execution_verified AND risk_budget_pass AND valid_stop_target AND no_hard_blocker`.

Examples hard blockers: missing live/executable quote, suspended stock, call auction without specialized fill model, price already too extended, invalid R:R, insufficient capital after lots/steps, bad candle, unknown fee/tick rules. For research mode, `TRADE_READY` can be disabled entirely when current quote provider unavailable; show EOD setup quality and `EXECUTION_UNKNOWN`.

**Data completeness** quality is not probabilistic confidence. Use `DATA_COMPLETE` or `MISSING` label, not 87% “AI confidence”.

## 6. Ranking

Default rank **separately for `(market, strategy_id, horizon)`**, score descending then readiness descending then stable canonical instrument_id. Store rank population size and `as_of`. `relative_percentile = 100 * (# comparable candidates with score <= this score) / count` (explicit tie handling), never interpreted as probability of profit.

A unified feed uses **balanced slots** from US, IDX, and Crypto; no combined global score/percentile until cross-market calibration validated. Deduplicate within view by underlying instrument but retain attached strategies; don't silently combine strategies into one score.

### Ranking modes

- `BEST_SETUP`: SQS desc, deterministic tie-breakers.
- `ENTRY_READINESS`: READY ahead of WATCH, then readiness desc, SQS as secondary.
- `RISK_FIRST`: valid stop, low modeled slippage, low liquidity participation, then setup score.
- `EXPECTED_NET_RETURN` **GATED** until validated predictive backtests and coverage thresholds met.

## 7. Evidence transparency

Every rank item provides `strategy_version`, `score_version`, `as_of`, raw factor values, passing and blocking rules, source and quote status; recorded `run_id`. Current quote refresh may change readiness but must not rewrite old score/signal snapshots.

## 8. Tests

- Exact score breakdown and deterministic tie order.
- Score high + no spread ⇒ `WATCH/UNKNOWN`, not READY.
- Same symbol in distinct markets remains distinct.
- Missing RVOL in required strategy ⇒ score null, not implicit 0.
- Arbitrary risk multiple target does not earn “structural resistance” points.
- Percentile among 1 candidate must be annotated sample size 1; not represented as meaningful predictive evidence.
