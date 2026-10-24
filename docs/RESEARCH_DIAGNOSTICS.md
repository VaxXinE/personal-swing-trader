# Research funnel diagnostics — genuine provider data, no execution

This is the next small step of TSK-027 (diagnostics only). A reproducible offline
comparison of unchanged `PULLBACK` and `BREAKOUT` strategy rules over **the same
candle revisions and universe evidence**. It does not change entry/exit/volume/R:R
requirements, data basis, holdout split, broker fees, or the sample threshold.

## Run

```sh
python scripts/research_diagnostics.py --mode demo --instrument-id US:NASDAQ:MSFT
python scripts/research_diagnostics.py --mode demo --instrument-id US:NASDAQ:MSFT --json
python scripts/research_diagnostics.py --mode live --instrument-id IDX:IDX:BBCA --json
```

For LIVE the SQLite archive must already contain that instrument's previously
captured Yahoo/Binance provider candles (from an explicit research ingestion);
the script **never downloads price data**. The `--as-of`,
`--expected-snapshot-sha256` and `--expected-universe-evidence-sha256`
options pin the result to previously recorded evidence. Failed quality gates,
incomplete history, wrong source, and mismatched digests return a nonzero error
instead of a fabricated strategy assessment.

Each strategy reports: eligible signal bars, qualified technical setups,
research gate passes, completed hypothetical trades, nonoverlapping-skipped bars,
development and holdout sample counts, stage-specific multi-label rejection
counts, and the deepest bottleneck stage. Reason totals can exceed the number of
evaluated signals because more than one condition may fail on a single bar. No
"likelihood", performance confidence, or win-rate conclusion is inferred from
these reasons. Performance metrics remain null below the existing 20-trade
minimum, and holdout results are descriptive only.

The GitHub [real market pilot](../.github/workflows/real-market-research.yml)
now calls this CLI for BOTH strategies for each of seven genuine provider series,
only after historical quality passes. It prints aggregates and hashes to CI logs,
never uploads or republishes vendor OHLCV. New research diagnostics are not a
substitute for verified corporate actions, delisted historical universe, or
out-of-sample walk-forward and cost-sensitivity testing.

Coding approach: apply upstream Anti-Slop comment hygiene and Ponytail's
minimal-diff/default-standard-library guidance; no installer or executable
third-party hooks.


## Exact rejection combinations (2026-10-25)

Each evaluated signal that fails technical qualification now increments one **exclusive**
combination bucket (sorted `|`-separated reason codes) alongside the existing,
overlapping per-reason counters. The public replay diagnostics include
`unique_setup_rejected_bars`, `exclusive_setup_rejections`, and
`setup_rejection_combinations`. The research CLI prints the five most frequent
combinations, not an unbounded arbitrary probability distribution.

These diagnostic identities must hold: `unique_setup_rejected_bars +
qualified_setups == eligible_signal_bars` and `sum(combinations.values()) ==
unique_setup_rejected_bars`. Exclusive `RR_BELOW_MIN` counts reveal when
risk/reward was the **only** rejection reason; frequent `RR_BELOW_MIN` alone
cannot establish that relaxing the threshold would produce safe entries.

The March/October 2026 pilot covered 7 provider-reported symbols and yielded
zero qualified PULLBACK/BREAKOUT setups despite 1,505 evaluated signal bars
per strategy. Do not optimize thresholds on those same assets and then describe
them as an untouched validation sample. Any future strategy amendment needs
a declared hypothesis, separate chronological evaluation, corporate-action
review, and comparison with an unchanged baseline; all claims remain
`RESEARCH_ONLY`.


## Observed real-provider baseline — run 40127182684

[GitHub Actions, 25 October 2026](https://github.com/VaxXinE/personal-swing-trader/actions/runs/40127182684)
replayed the unchanged PULLBACK and BREAKOUT strategies on seven provider-reported
series captured on ephemeral CI runners for 1 April 2025 through 20 October
2026 (IDX data starts 8 April 2025). Every source passed the structural
quality gate, with a narrowly reviewed March 2026 exchange closure in IDX.

| Instrument | Eligible signal bars per strategy | PULLBACK: only `RR_BELOW_MIN` | BREAKOUT: only `RR_BELOW_MIN` | Qualified setups / completed trades |
| --- | ---: | ---: | ---: | ---: |
| MSFT | 171 | 6 | 0 | 0 / 0 |
| NVDA | 171 | 9 | 0 | 0 / 0 |
| AAPL | 171 | 7 | 0 | 0 / 0 |
| BBCA | 148 | 8 | 0 | 0 / 0 |
| BBRI | 148 | 2 | 1 | 0 / 0 |
| BTCUSDT | 348 | 12 | 0 | 0 / 0 |
| ETHUSDT | 348 | 30 | 0 | 0 / 0 |
| **Total** | **1,505** | **74** | **1** | **0 / 0** |

The `RR_BELOW_MIN`-only counter is a **diagnostic exclusion**, not a
counterfactual trade count. Even if that constraint were changed, the research
gate, next-bar fills, and outcomes would still need separate evaluation.
Most other failed bars have **multiple simultaneous** setup rejections.
These seven assets were not sampled as a complete historic/delisted universe;
the result is not an objective strategy-wide performance estimate. Do not
tune and retest the same data claiming independent out-of-sample validation.

## Fixed EARLY/LATE signal-period diagnostics (2026-10-25)

Backtest V2 now reports `diagnostics.signal_periods` in every replay, and `research_diagnostics.py` includes the same windows in JSON and terminal output for both PULLBACK and BREAKOUT. The two fixed chronological halves divide **eligible signal indices after the 210-bar warmup and before the last horizon bars**; the midpoint uses integer division. Each period includes UTC first/last signal dates, eligible signal bars, qualified setups, research gate passes, trades, overlap-skipped bars, multi-label rejection reasons, and **disjoint** combinations/exclusive rejection counts.

The sum of EARLY+LATE funnels and disjoint combinations must equal the unchanged global funnel. Indicators always use historical prefixes, not a new indicator reset at the window boundary. A simulated trade can exit after the window containing its signal, but its diagnostic attribution remains on that original signal date. The existing 75/25 development/holdout partition is unchanged.

**Not an untouched OOS test:** these same 2025–2026 vendor histories were already inspected before adding periods. The split is strictly an *exploratory stability diagnostic*, and `validated`, `point_in_time_validated`, and `execution_verified` remain false. Zero trades cannot support walk-forward returns, profitability, fee-sensitivity metrics, confidence bands or minimum-sample claims. Any prospective validation requires a frozen universe, rules, exchange calendars, fees and independent later observations **before** examining that period.
