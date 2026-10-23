# GLOSSARY — Consistent Terms Across Project

| Term | Meaning |
|---|---|
| Swing trading | Positions held days to weeks, unlike intraday scalping |
| Long-only | Profits sought from price rises after buying (no short borrowing) |
| Liquid Universe | Instruments passing versioned historical liquidity filters |
| Opportunity | Discoverable candidate; **not** necessarily executable |
| Trade Ready | All required strategy, freshness, execution and risk gates pass; still no auto-order |
| ADV20 | Average traded **notional value** over 20 prior finalized sessions, native currency; estimated when volume×close |
| RVOL20 | Current finalized volume vs prior 20-volume mean, comparable within instrument/pair |
| ATR14 | Wilder average of true range over 14 bars, price volatility proxy |
| EMA20/50 | Exponential moving average of 20/50 closes; prices adjusted consistently |
| Setup Score (SQS) | Explainable heuristic quality 0–100, **not** probability |
| Entry readiness | Ranking of proximity/validity of entry, not win odds |
| Historical evidence | Outcome statistics of similar setups, only useful with valid data and enough observations |
| R multiple | Realized/planned P&L divided by initial trade risk; costs included when `net` |
| Gross R:R | Target upside divided by stop distance, before fees/slippage |
| MFE/MAE | Maximum favorable/adverse excursion between entry and exit/horizon |
| Barrier race | Whether target or stop touched first (or neither/ambiguous) in a window |
| TIMEOUT | Neither barrier touched before strategy horizon |
| Ambiguous bar | OHLC bar touches stop and target but unknown intrabar event ordering |
| OOS | Out-of-sample period not used to tune model |
| Purging | Exclude train examples whose label outcome overlaps test window |
| Look-ahead bias | Past decision accidentally uses future information |
| Survivorship bias | Historical sample includes only assets that survived to present |
| Point-in-time / as-of | Only facts available at the stated historical decision time |
| Immutable signal | Original published analysis never overwritten by later market events |
| Snapshot manifest | Versioned listing/hash of dataset files used in a run |
| Data provenance | Which provider/revision/time supplied a value |
| RAW price | Tradable price at event, distinct from split/total-return adjusted research series |
| Spread | Best ask minus best bid; potential friction, not alone full slippage |
| Tick size | Allowed price increment, specific to venue/price band/date |
| Lot size | Allowed trade quantity increment (BEI regular market 100 shares) |
| UNKNOWN | Data missing/invalid to decide; **not** false, zero, or a trade signal |
| EOD | End-of-day, finalized session information |
| GATED | Feature blocked by criteria until evidence/validation passes |
