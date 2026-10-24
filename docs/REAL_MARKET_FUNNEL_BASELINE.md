# Real-market strategy funnel baseline — 2026-10-25

**Research only.** This baseline comes from seven successful GitHub-hosted provider jobs on commit `0ff765d`: [real-market workflow run #40126055476](https://github.com/VaxXinE/personal-swing-trader/actions/runs/40126055476). The backend and private Android build passed separately in [run #40126055447](https://github.com/VaxXinE/personal-swing-trader/actions/runs/40126055447). No real orders were placed. This is a reproducible diagnostic *observation*, not out-of-sample validation.

All 7 provider archives were reported as `VENDOR_UNVERIFIED` and `STRUCTURAL_PASS`. IDX BBCA/BBRI each had one explicitly reviewed March-2026 exchange-holiday gap. Neither pricing adjustments nor full market calendars are certified.

## Fixed strategy evaluation: PULLBACK and BREAKOUT (10 bars)

| Market | Instrument | Archived bars | Eligible signals, each strategy | PULLBACK qualified / simulated trades | BREAKOUT qualified / simulated trades |
|---|---|---:|---:|---:|---:|
| US | MSFT | 391 | 171 | 0 / 0 | 0 / 0 |
| US | NVDA | 391 | 171 | 0 / 0 | 0 / 0 |
| US | AAPL | 391 | 171 | 0 / 0 | 0 / 0 |
| IDX | BBCA | 368 | 148 | 0 / 0 | 0 / 0 |
| IDX | BBRI | 368 | 148 | 0 / 0 | 0 / 0 |
| CRYPTO | BTCUSDT | 568 | 348 | 0 / 0 | 0 / 0 |
| CRYPTO | ETHUSDT | 568 | 348 | 0 / 0 | 0 / 0 |
| **Total** | **7** | **3,045** | **1,505 per strategy** | **0 / 0** | **0 / 0** |

This is 3,010 *strategy–signal-bar evaluations*, not 3,010 independent trade observations. Every asset/strategy reached the bottleneck `TECHNICAL_SETUP`, *before* the research gate and next-bar entry stages. Do not infer performance, win rate or edge from a zero-trade sample.

## Dominant rejection patterns observed in actual CI logs

| Instrument | PULLBACK `RR_BELOW_MIN` | BREAKOUT `BREAKOUT_NOT_CONFIRMED` | BREAKOUT `RVOL_LOW` |
|---|---:|---:|---:|
| MSFT | 156 / 171 | 160 / 171 | 157 / 171 |
| NVDA | 153 / 171 | 160 / 171 | 164 / 171 |
| AAPL | 144 / 171 | 156 / 171 | 157 / 171 |
| BBCA | 141 / 148 | 144 / 148 | 126 / 148 |
| BBRI | 139 / 148 | 143 / 148 | 131 / 148 |
| BTCUSDT | 332 / 348 | 333 / 348 | 305 / 348 |
| ETHUSDT | 338 / 348 | 336 / 348 | 300 / 348 |

**Important:** rejection codes are multi-label. A single candle can fail risk/reward, trend and support simultaneously; those counts must never be summed to estimate separate unsuccessful trades. This is not a threshold-calibration study.

### Engineering interpretation

The current `detect_strategy` requires a *previously observed structural target* higher than the hypothetical entry, with potential reward/risk at least **2:1**. Breakout further requires price above the prior 20-bar resistance plus buffer, and relative volume at least **1.5×** its prior 20-bar mean. These conditions can jointly be rare. They are not logically impossible—the existing engineered signal fixtures demonstrate successful qualifications—but these seven vendor-reported histories produced none.

## What this baseline does and does not justify

1. **Keep strategy rules unchanged** for now. A high rejection rate does not establish which threshold should change or whether the strategy is economically useful.
2. Next analytical prerequisite is a **pre-registered multi-period, multi-universe research plan**, including IPO/delisting and adjusted-vs-tradable-price treatment, separate market cost models, and a true untouched out-of-sample period.
3. Before examining results from alternative rules, define their hypothesis, expected effects, minimum sample size, risk controls and held-out comparisons. Optimizing thresholds directly on these seven assets would invite selection bias.
4. Real OHLCV is fetched into **ephemeral CI SQLite** only. No original prices, provider credentials, unverified research results, or broker actions are committed. Local `history.sqlite` does not auto-sync from GitHub Actions.
5. The fingerprint for each asset is printed by its CI job, and `scripts/research_diagnostics.py --mode live --instrument-id ID --json` reproduces the same funnel from its pinned local archive. Provider backfills and point-in-time membership remain unverified.
