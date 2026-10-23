# Backtest V2: conservative, chronologically segmented research replay

`GET /v1/backtests/{instrument_id}?strategy=PULLBACK&horizon=10` retains its existing endpoint and now returns `version: 2.0-research`, `development`, `holdout`, and `metrics` objects in addition to the old `trades`, `samples`, `net_expectancy_r`, `validated`, `status` keys.

**Contract**

- Signal on completed bar *i* uses OHLCV and indicators from bars 0..i only; entry is eligible **next bar**. No future bars are used to compute signal, ATR, structural target, or liquidity gate.
- Only `QUALIFIED` setups that pass Research Gate V2 and historical liquidity are examined. This stricter filter may return **zero trades**, which is an honest result.
- One position at a time per instrument/strategy, skip overlapping signals. A pending limit/stop order is good for the next bar only; no fill if price does not touch the entry. Long-only.
- No chasing an opening gap greater than 0.5 ATR. STOP beats TARGET when both could be touched on the same OHLC bar; down-gap stops exit at bar open where worse. Closing exit at chosen horizon if neither barrier hit.
- Hypothetical friction is fixed at 0.1% on **both entry and exit**, including in stop-loss risk denominator. **Not actual broker fees or taxes**.
- Chronological 75%/25% partition based on *entry bar index*, with first eligible signal after 210-bar warmup. Future outcomes may extend across partition boundaries; partitions are descriptive, not parameter optimization or point-in-time OOS validation.
- Performance metrics (`net_expectancy_r`, win rate, profit factor, drawdown) are withheld with `status: INSUFFICIENT_SAMPLE` when fewer than **20 completed positions** exist in each segment. No win probability is reported.
- `validated` always `false`, even when sample counts are large. Limitations explicitly include survivorship, missing delistings/corporate action validation, OHLC barrier ambiguity, cost approximation, exchange rule gaps and incomplete independent holdout testing.

To inspect without triggering LIVE provider calls, use the app's **demo** data mode or offline fixtures. If macOS displays "Malicious Script Blocked" during LIVE scans, stop LIVE workflows and investigate separately; no software patch alone is evidence that the warning has been resolved.

## Zero-trade diagnostics

`replay(...)["diagnostics"]` adds backward-compatible stage counts:
`eligible_signal_bars`, `qualified_setups`, `research_gate_passed`,
`completed_trades`, and independent rejection reason maps for technical setups,
research-gate checks and next-bar hypothetical entries. Reason maps are
**multi-label** (a candle may fail multiple checks); do not sum as unique bars.
These explain sample scarcity without relaxing strategy parameters.

For DEMO testing without external market providers:

```bash
SWING_DATA_MODE=demo PYTHONPATH=backend python - <<'PY'
from app.domain import INSTRUMENTS
from app.providers import demo_bars
from app.backtest import replay
from pprint import pprint
ins = next(x for x in INSTRUMENTS if x.symbol == 'MSFT')
r = replay(ins, demo_bars(ins), 'PULLBACK', 10)
pprint(r['diagnostics'])
PY
```

## Diagnostic result: all baseline DEMO fixtures can legitimately return zero

`demo_bars()` uses pseudo-random deterministic price paths and quote-turnover estimates,
**not** a scenario generator calibrated to exercise every trading pattern. In
particular it does not deliberately generate 1.5x+ relative-volume breakout days,
while `detect_strategy` requires breakout confirmation **and** structural targets
with minimum risk/reward. For the 310-bar demo fixtures, only 90 bars are eligible
for the 210-bar-warmup / 10-bar-horizon test. An all-zero result is a limitation
of these fixtures; it is **not** evidence the strategy is bad or good in markets.

Run a bounded offline batch report without starting a server or fetching live data:

```bash
python scripts/backtest_demo_diagnostics.py
python scripts/backtest_demo_diagnostics.py --json
```

The end-to-end smoke fixtures in `backend/tests/test_backtest_integration.py`
intentionally engineer one qualifying PULLBACK and BREAKOUT signal each, using the
**real** strategy calculations, liquidity checks and research gate (no stubs),
then verify next-day entry/target and the `validated: false` contract.
The very profitable individual synthetic fixture is deliberately NOT a performance
claim or an input for strategy parameter tuning. Do not relax live criteria solely
to make the DEMO generator print trades. Next research milestone: real
point-in-time historical candidate universe, split-adjustment checks, transaction
friction measured by market, and held-out multi-symbol period tests.


## Archived-replay integration

For read-only, locally stored observation candles, use `GET /v1/history/backtests/{instrument_id}?source=SYNTHETIC_FIXTURE&price_basis=SYNTHETIC` in DEMO mode or `python scripts/archive_backtest.py`. The replay result includes an observation-time cutoff and SHA-256 fingerprint so the same revisions can be requested explicitly. No new provider calls are made. This does **not** establish vendor point-in-time availability or validated execution prices. See [ARCHIVED_BACKTEST_INTEGRATION](ARCHIVED_BACKTEST_INTEGRATION.md).
