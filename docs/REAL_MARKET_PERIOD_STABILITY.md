# Seven-asset chronological technical-gate stability — 2026-10-25

Research-only evidence from [live provider CI #40127352391](https://github.com/VaxXinE/personal-swing-trader/actions/runs/40127352391), commit `78ded744`. Two unchanged strategies were replayed on the same previously captured, quality-gated provider-reported candles with a 10-bar horizon. This is retrospective exploratory analysis, **not** an independent holdout, point-in-time universe, execution test, or strategy optimization.

## Disjoint diagnostic periods

| Asset | Market | EARLY eligible, per strategy | LATE eligible, per strategy | PULLBACK qualified EARLY/LATE | BREAKOUT qualified EARLY/LATE |
|---|---|---:|---:|---:|---:|
| MSFT | US | 85 | 86 | 0 / 0 | 0 / 0 |
| NVDA | US | 85 | 86 | 0 / 0 | 0 / 0 |
| AAPL | US | 85 | 86 | 0 / 0 | 0 / 0 |
| BBCA | IDX | 74 | 74 | 0 / 0 | 0 / 0 |
| BBRI | IDX | 74 | 74 | 0 / 0 | 0 / 0 |
| BTCUSDT | Crypto spot | 174 | 174 | 0 / 0 | 0 / 0 |
| ETHUSDT | Crypto spot | 174 | 174 | 0 / 0 | 0 / 0 |
| **Total** | **7** | **751** | **754** | **0 / 0** | **0 / 0** |

Each half is defined by **signal index**, after the original 210-bar indicator warmup and excluding the last 10 bars without complete possible outcomes. Reported totals reconcile to the earlier 1,505 signal opportunities **for each strategy**, across seven instruments. A single historical signal is not an independent trade; evaluation of both strategies is not an independent sample. All 14 asset-strategy pairings have the `TECHNICAL_SETUP` bottleneck in both halves.

## Observed combinations from actual provider runs

Reject labels are disjoint when recorded as the **full sorted set per bar**, but a bar can contain several reasons. The top combinations printed by the CI jobs are:

- MSFT PULLBACK, EARLY: `CONFIRMATION_PENDING|PULLBACK_NOT_NEAR_SUPPORT|RR_BELOW_MIN|TREND_NOT_ALIGNED` — 35 of 85. LATE: `CONFIRMATION_PENDING|PULLBACK_NOT_NEAR_SUPPORT|RR_BELOW_MIN` — 13 of 86 (tied with a four-reason combination at 13).
- BBCA PULLBACK, EARLY: four-reason combination `CONFIRMATION_PENDING|PULLBACK_NOT_NEAR_SUPPORT|RR_BELOW_MIN|TREND_NOT_ALIGNED` — 45 of 74. LATE: `CONFIRMATION_PENDING|RR_BELOW_MIN` — 17 of 74.
- BTCUSDT BREAKOUT, EARLY: `BREAKOUT_NOT_CONFIRMED|RR_BELOW_MIN|RVOL_LOW|TREND_NOT_ALIGNED` — 140 of 174. LATE: the same four-reason combination — 76 of 174.
- NVDA BREAKOUT, EARLY: the same four-reason combination — 37 of 85; LATE: `BREAKOUT_NOT_CONFIRMED|RR_BELOW_MIN|RVOL_LOW` — 43 of 86.

These examples are not a fitted ranking of strategy parameters. They show that **multiple technical conditions commonly fail together**, rather than one independently identifiable threshold universally explaining all 0-trade outcomes.

## Decision gate for following work

1. Keep production/research strategy rules unchanged. A 0-trade sample cannot support win rate, expectancy, stop/target return sensitivity, portfolio allocation, or model calibration.
2. Freeze a prospective experimental comparison protocol **before** examining new later observations: source & historical universe, base strategy, candidate hypotheses, lookback windows, friction models, adjustment policy, error budgets, minimum sample sizes and evaluation boundaries.
3. Research complete exchange calendars and genuine historical instrument lifecycle/adjustment evidence; `VENDOR_UNVERIFIED`, backfilled observation timestamps, and sampled present-day universe remain unresolved.
4. To produce reproducible diagnostics from a local LIVE archive, use `python scripts/research_diagnostics.py --mode live --instrument-id US:NASDAQ:MSFT --json` and keep the SHA-256 plus observation cutoff. CI SQLite files are ephemeral and OHLCV is not redistributed.
5. Until a separately observed prospective period satisfies sample and data-quality gates, **nothing here is a statistical performance claim**. The Android build and backend tests only verify implementation behavior.

No provider OHLCV, API secrets, broker orders, fee estimate changes or third-party installer scripts are committed.
