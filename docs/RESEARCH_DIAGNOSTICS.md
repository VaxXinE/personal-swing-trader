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
