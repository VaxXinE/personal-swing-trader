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
