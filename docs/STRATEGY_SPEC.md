# STRATEGY_SPEC — Deterministic Long-Only Swing Setups V0.1

**Status:** algorithms are **research BASELINES**, not profitable systems. After development each parameter/config change creates version; validate in [BACKTESTING](BACKTESTING.md).

## 1. Common semantics

- `bar[t]` = **finalized** daily candle available as of evaluation time. US/IDX indexed by exchange sessions, crypto by **UTC daily** windows.
- All indicators use observations `<= t` once candle `t` finalized; any lookback resistance for breakout uses bars `<= t-1`.
- `EMA20, EMA50, EMA200`, `ATR14` Wilder smoothing, `RVOL20` and reference highs computed by pure functions with explicit warmup.
- `ATR14(t) = WilderMA(TR,14)`; `TR_t = max(H_t-L_t, abs(H_t-C_{t-1}), abs(L_t-C_{t-1}))` with split handling.
- `RVOL20 = volume_t / mean(volume_(t-20..t-1))`; if denominator zero or missing: UNKNOWN. Crypto base-volume RVOL uses same pair consistently.
- Each strategy emits `DISCOVERED`, `QUALIFIED`, `WATCH`, `READY`, `TRIGGERED`, `EXPIRED`, `INVALIDATED` or `UNKNOWN`. Status based on time, conditions, eligibility, not score alone.
- Default horizon parameter `H=10` exchange sessions for stocks, `H=10` UTC crypto days; test `5/10/20` as sensitivity, no one-size-fits-all claim.
- `t` signal generated **after** `bar[t]` finalized. Trading model earliest hypothetical fill is **next tradable bar** `t+1` with conservative slippage/next-open gap handling. Intraday strategy requires separate audited feed and revised strategy version.

## 2. Strategy A: Trend Pullback `PULLBACK_V0_1`

**Stage 0 (eligibility):** instrument in historically liquid universe; sufficient warmup; valid price basis; no market data gaps; not under prohibited session state.

**Trend conditions (candidate):** `Close_t > EMA50_t`, `EMA20_t > EMA50_t`, `EMA50_t > EMA50_(t-5)`; EMA200 as context flag only for early tests (not compulsory until measured).

**Pullback structure:** in past 10 finalized sessions, price must have retraced toward EMA20 or previous confirmed support, while trend remains intact. Proposed measurable baseline: `distance_atr = (Close_t - EMA20_t) / ATR14_t` within `[-0.5, 0.8]`; and `min(Low_(t-5..t)) > EMA50_t - 1.0*ATR14_t` (this support check uses current EMA50_t by design; test alternate past-EMA comparison). These are candidate heuristics, not discovered best values.

**Confirmation:** last candle bullish (`Close_t > Open_t`), `Close_t > Close_(t-1)`, optional strength `Close_t > High_(t-1)` for stricter mode. Confirmation does not mean that entry happened.

**Entry trigger:** `entry_trigger = high_t + tick_size(high_t)` for next session; validate current market tick rule. If next open gaps above configured max chase distance (initial `0.5 ATR`), set `WAIT/EXPIRED`, do not assume favorable fill.

**Stop:** `raw_stop = min(low_(t-5..t)) - 0.25*ATR14_t` (buffer); round **down** to valid tick for long stop. Recalculate if market tick bands affected. `stop < planned_entry` must hold.

**Target:** structural resistance prior 60 bars (highest high of `t-60..t-1`, strictly above planned entry if exists). If none, optional **research target** `entry + 2*(entry-stop)` is explicitly labelled **R-multiple hypothesis**, *not* resistance or statistical forecast. Do not force Trade Ready simply because this synthetic 2R target exists: strategy config may require real structural target, otherwise `TARGET_UNSUPPORTED` WAIT.

**Invalidate:** break below structural stop region before entry, trend conditions fail, H session expiry, gap/price extension invalid. Save precise reason.

## 3. Strategy B: Breakout `BREAKOUT_V0_1`

**Prerequisites:** liquid market, enough finalized history; above EMA50 optionally required; exclude suspended/auction-only venue.

**Resistance:** `R_t = max(High_(t-20), ..., High_(t-1))` **excluding current `High_t`**. Use 20 prior complete sessions. A 20-bar base is a heuristic; optional consolidation rule `max(High_(t-20..t-1))/min(Low_(t-20..t-1)) - 1 <= 0.20` provisional. Test volatility-normalized alternative, don't assume all markets share 20%.

**Breakout confirmation:** `Close_t > R_t + max(tick_size(R_t), 0.1 * ATR14_t)`; `RVOL20 >= 1.5`; `Close_t > EMA50_t`; optional candle-close strength filter. Candidate is flagged `EXTENDED` if `Close_t - R_t > 1.5*ATR14_t` (initial).

**Entry:** on next session, conditional valid limit/stop-entry around the breakout area. Since intraday price sequence is unknown in daily-only data, simulation must define conservative fill convention; **never** treat signal day close as attainable after close.

**Stop:** `min(Low_t, R_t - 0.5*ATR14_t)` minus tick buffer, with strategy-specific upper bound on risk distance. Stop lower than entry and above zero. If stop too far / position can't be sized, reject.

**Target:** first valid next resistance beyond entry, if detected; otherwise research-only `2R` heuristic with `TARGET_UNSUPPORTED` state unless config explicitly enables hypothetical risk target for study. Do not turn unknown future structure into fake target.

**False breakout / invalidate:** close returns below `R_t` under invalidation policy (initial 1 completed candle), abnormal gap, H expiry, or market/data eligibility loss.

## 4. State machine

`DISCOVERED -> QUALIFIED -> WATCH -> READY -> TRIGGERED -> FILLED` (FILLED **only** by explicit manual/paper entry). `WATCH/READY -> INVALIDATED/EXPIRED`; `TRIGGERED -> SKIPPED/EXPIRED` if no trade. Events append-only. `Trade Ready` means candidate with valid, timely setup and execution feasibility; not order submission.

**Market opens / gaps:** if price jumps above trigger/expected entry, recompute R:R using new modeled open/quote, cash and risk. No stale stop/target as if fill at old price. Data lacking intraday path cannot assert event order.

## 5. Input and output contract

```python
@dataclass(frozen=True)
class SetupCandidate:
    instrument_id: str
    strategy_id: str
    strategy_version: str
    evaluated_at: datetime
    data_snapshot_id: str
    state: str
    feature_values: Mapping[str, Decimal | None]
    trigger: Decimal | None
    stop: Decimal | None
    target: Decimal | None
    reason_codes: tuple[str, ...]
```

This is a specification sketch, not runnable complete application code. Use `Decimal` for proposed executable prices, numeric arrays for technical computations.

## 6. Invariant and golden tests

- `[high]` of current bar excluded from historical breakout resistance.
- Two-bar unfinished stream can update UI quote but **cannot** create daily strategy signal.
- `Close_t == resistance` is not breakout.
- A price gap above chase threshold results in WAIT rather than backfilled favorable price.
- If no valid structural target and research target disabled, no READY.
- Historical replay recomputes same candidate for same data/config version.
- Corporate actions do not produce artificial structural lows or ATR jumps.
- All bar edge cases: NaN/0 ATR, zero volume, short history, nontrading date, halted venue are `UNKNOWN/REJECT`.

## 7. Parameter registry

Every strategy config stores `ema_fast`, `ema_slow`, `atr_period`, `warmup`, `lookback`, `rvol_min`, `pullback_atr_range`, `buffer_atr`, `gap_tolerance_atr`, `target_mode`, `horizon`, `eligible_market`, `effective_from`, `config_hash`. **No optimal parameter claims** until walk-forward tests.
