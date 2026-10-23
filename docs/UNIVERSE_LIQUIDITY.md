# UNIVERSE_LIQUIDITY — Selection and Exclusion

**Status:** baseline parameters **UNVALIDATED**; market-specific gate design LOCKED.

## 1. Universe tiers

`ALL_DISCOVERABLE` = registry instruments with metadata; `HISTORICALLY_LIQUID` = passed historical screening; `OPPORTUNITY` = strategy candidate; `EXECUTION_VERIFIED` = current market quote/order-rule/risk gates pass; `TRADE_READY` = setup confirmation + execution eligibility. A candidate may be shown despite rejection with exact reason, but cannot be labelled Ready.

Never use current constituents/lifecycle to construct a historical universe; membership is evaluated **as of historical session** using available information.

## 2. Default baseline thresholds

| Rule | US equities | IDX | Crypto Spot |
|---|---|---|---|
| Venue | NYSE/Nasdaq/major US listings | BEI normal continuous-trading board | selected exchange, active USDT spot pairs |
| Historical ADV20 | >= 10,000,000 **USD/day** | >= 10,000,000,000 **IDR/day** | >= 10,000,000 **USDT/day** |
| Spread soft maximum | 0.30% | 0.50% **plus tick-aware cost check** | 0.15% |
| Historical candles | >= 200 completed equity sessions | >= 200 completed equity sessions | >= 180 complete UTC daily candles |
| Price constraint | >= 5 USD (default) | no fixed nominal price minimum | no fixed nominal price minimum |
| Exclusions | OTC/penny defaults; suspended/delisted | suspended and special-watch call auction from READY | inactive pairs, leveraged tokens, stablecoin directional candidates |

These are **initial selection hypotheses**, not guarantees of liquidity or performance. User-configurable profiles (strict/balanced/broad) must not silently mutate backtested presets.

## 3. Precise liquidity fields

- `adv20`: arithmetic mean **actual daily traded notional** of prior 20 finalized sessions, excluding current unfinished session. If actual notional unavailable, `close*volume` may be recorded as **estimated ADV** only and flagged. Do not overstate accuracy.
- `median20_turnover`: robustness to one anomalous trading day.
- `turnover_consistency`: proportion of prior 20 sessions above configurable per-market floor.
- `spread_pct = 100*(ask-bid)/((ask+bid)/2)` for positive best bid/ask, source, timestamp and market mode known.
- `spread_ticks` = normalized number of tick steps between bid and ask; market rules can depend on price, session, board, date.
- `participation_pct = 100 * intended_order_notional / adv20` with consistent currency conversion (as-of). Baseline cap **0.1% ADV20**; also hard limit cash and depth.
- `orderbook_depth` = cumulative ask-side value in specified bps band for buying, not simply 24h volume; default 50 bps band for study.

For crypto, calculate quote volume using exchange-supplied `quoteVolume` where possible; `BTC` base volume must not be compared to `ETH` base volume. For stocks, session's turnover in native exchange currency. FX conversion required only for cross-market monetary reports, never silently mixed.

## 4. Venue specifics

### US

Common stocks and ADRs initially. ETFs separate analysis track P1. `price >= $5` heuristic default; users can explore outside but no READY unless supported. Quote feed may represent only IEX (Alpaca Basic) rather than consolidated tape; mark coverage accurately. Halt/delist/inactive require explicit lifecycle data.

### IDX

Normal exchange traded equities; special-watch board uses periodic call auction and **incompatible default fill logic**, so exclude from READY. Regular lot **100 shares** per IDX docs. Fraction price follows rule/version effective on trade session; as of 2026-09 IDX referenced Kep-00136/BEI/09-2026 and tiers 1/2/5/10/25 IDR across bands; **load versioned rules rather than hardcoding timeless numbers**. Tick bands boundary and daily reference handling require official verification and unit tests.

### Crypto

Exchange- and pair-specific. Filter spot status, `PRICE_FILTER`, `LOT_SIZE`, `MIN_NOTIONAL`/`NOTIONAL`, quote asset, `MAX_NOTIONAL` if available; verify at runtime before declaring executable. Price data from Binance pair does not guarantee user can trade that pair via their own brokerage/exchange. Missing local exchange availability → informational scan only.

## 5. Evaluation policy

Evaluate gate states `PASS`, `FAIL`, `UNKNOWN`. Missing data ≠ fail score 0, and `UNKNOWN` cannot pass hard execution gate. Treat historical-liquid vs live-executable separately; don't claim real-time on delayed EOD data.

Reason codes: `NO_HISTORY`, `LOW_ADV`, `WIDE_SPREAD`, `SPREAD_UNKNOWN`, `NO_LIVE_QUOTE`, `HALTED`, `SUSPENDED`, `CALL_AUCTION`, `UNSUPPORTED_PAIR`, `ORDER_TOO_LARGE`, `DEPTH_INSUFFICIENT`, `RULES_UNAVAILABLE`, `NO_ORDER_ACCESS`, `DATA_INVALID`, `INSUFFICIENT_CASH`.

Persist `exclusions(instrument_id,as_of,universe_config_hash,reason_codes,source_snapshot_id)`; UI can browse these without calling them BUY candidates.

## 6. Test scenarios

- One-day 100× volume spike does not automatically pass median/consistency rule.
- Missing bid/ask cannot pass `EXECUTION_VERIFIED` even if ADV enormous.
- Same `BTC` listed on two crypto pairs is not duplicate instrument key, but underlying dedup applied to unified feed.
- IDX 1 tick could exceed percent spread threshold; test tick-aware cost.
- Historical run for an IPO before listing date must exclude asset.
- Failed quote fetch does not delete historical valid universe membership; merely degrades execution state.

See [RISK_EXECUTION](RISK_EXECUTION.md), [SCORING_RANKING](SCORING_RANKING.md) and [REFERENCES](REFERENCES.md).
