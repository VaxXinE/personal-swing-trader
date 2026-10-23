# BACKTESTING — Honest Event-Driven Evaluation

**Status:** mandatory validation design. No backtest has been executed yet.

## 1. Purpose

Evaluate whether each **versioned** strategy and rank policy improves decision quality after realistic execution costs. Avoid using backtest to manufacture an attractive win rate. Track signal quality independently from manual trader behavior.

## 2. Timeline discipline

At end of finalized candle `t`, generate features and signal using data **known as-of t**. Next eligible session `t+1` can fill under explicit simulation rules. At horizon/stop/target resolve outcome and append immutable result. `available_at` matters as much as economic event date. Equity market sessions vary with holidays/DST; crypto session unit is UTC day.

No entry at candle close when signal requires knowing the full closing candle. No same-bar high/low event ordering if sequence unknown. Raw tradable price for fills, consistently split-adjusted series if used for research.

## 3. Data requirements

- OHLCV complete and validated; source/price basis/currency and revision labelled.
- Historical universe per date, listing/delisting/halt/board state included when available.
- Corporate actions handled (splits, dividends, rights, ticker changes); no survivorship bias claims if missing lifecycle dataset.
- Portfolio exposure, cash availability, lot/tick step/fees as-of time.
- Historical bid/ask/depth if available. If unavailable, estimates clearly marked and sensitivity scenarios required.

## 4. Simulation execution model V0.1

- Signals evaluated after final bar; trade earliest next session.
- `NEXT_OPEN_CONSERVATIVE`: fill modeled at next open plus adverse slippage, **only if** entry condition would reasonably trigger; if open gaps too high cancel/recalculate.
- Stop/target fill: first touch of valid barrier in chronological data; ambiguous both-touched same bar conservatively stop-first P&L or label ambiguous for model training.
- Fees include commission, taxes when known, spread and slippage; `0bps`, base, high stress scenarios reported—not just ideal.
- Halt/call-auction unsupported bars cannot be executed under continuous-trading model.
- Holding horizon H: exit at next valid opportunity after expiry, apply documented exit slippage.
- Entire portfolio backtests impose max concurrent exposures and finite available cash; independent signal tests reported separately.

## 5. Dataset splits / research protocol

- Time-based development + tune + untouched test blocks (dates stored in experiment manifest). No future information on params, delisting or earnings.
- For ML overlapping H labels, purge cross-boundary examples and embargo where warranted.
- Compare with benchmark: relevant index/ETF where available, buy-and-hold market proxy, naive breakout/pullback baseline, or no-trade cash if appropriate.
- Parameter sensitivity neighborhoods and re-running under conservative fees must be reported to spot overfitting.
- Multi-asset correlation and event clustering reduce effective sample size; don't claim statistically meaningful outcomes solely from count of alerts.

## 6. Required outputs

| Metric | Definition / caveat |
|---|---|
| Net expectancy (R) | mean realized R after fees/slippage incl losses and timeouts |
| Profit factor | gross profits / abs gross losses; undefined when no losses |
| Drawdown | peak-to-trough based on realistic marked portfolio equity curve |
| Win rate | wins / closed trades; not sufficient alone |
| Time-in-market | capital exposure duration |
| Turnover and fees | transaction count, volume, total cost |
| MAE/MFE distributions | intratrade adverse/favorable excursions |
| Baseline delta | performance difference net of costs |
| Coverage | # assets, missing sessions, listings and delistings captured |
| Stability | by market, regime, year, strategy and parameter neighborhood |
| Ambiguity | fraction same-bar stop/target unresolved |

Plot out-of-sample equity/drawdown by market and strategy; disclose test period, costs, universe restrictions, market data provider, parameter hashes.

## 7. Acceptance/golden cases

- Breakout rolling resistance **shifted**; if no prior resistance crossing, no signal.
- Earnings known two days after quarter end cannot influence day before release.
- Split event corrected; no fake stop-out solely due to price adjustment.
- Next session opens beyond entry by >chase tolerance ⇒ no favorable historic fill.
- Target and stop hit in same daily candle ⇒ conservative/no assumed winning sequence.
- Delisted historical constituent included when source supports; otherwise coverage warning.
- Reproducing run from snapshot + config + seed yields identical results.
- Increasing fees reduces (or leaves unchanged) strategy net results for same executions.

## 8. Promotion gate

Promote a strategy variant from `RESEARCH` to `PERSONAL_PAPER` only after dataset quality, OOS tests, baseline comparison, cost stress, and edge-case review pass. `PERSONAL_LIVE_DECISION_SUPPORT` requires forward validation; **never** implies system will place orders. Promotion recorded in [DECISIONS](DECISIONS.md).
