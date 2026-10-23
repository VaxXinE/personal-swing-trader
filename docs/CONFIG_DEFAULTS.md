# CONFIG_DEFAULTS — Canonical Parameter Registry (Research Baselines)

**Status:** all numbers here are **BASELINE UNVALIDATED** as of 2026-10-23. This document is the canonical location for default parameters; domain specs explain how used. A runtime implementation must store immutable JSON config versions+hash and never silently change past runs.

## Product/signal horizon

| Key | Default | Meaning |
|---|---|---|
| `analysis.timeframe` | `1d` | only finalized daily bars used for EOD signal |
| `analysis.horizon.equity` | `10 trading_sessions` | test 5/10/20, exchange calendar |
| `analysis.horizon.crypto` | `10 utc_days` | 24/7 UTC daily boundary |
| `analysis.direction` | `LONG_ONLY` | no short/leveraged/futures orders |

## Liquidity universe

| Key | US | IDX | Crypto |
|---|---:|---:|---:|
| `liquidity.adv20_native` | 10,000,000 USD | 10,000,000,000 IDR | 10,000,000 USDT |
| `liquidity.max_spread_pct` | 0.30% | 0.50% + tick-aware check | 0.15% |
| `liquidity.min_final_daily_bars` | 200 | 200 | 180 |
| `liquidity.min_price` | 5.00 USD | none | none |
| `liquidity.max_order_adv_participation` | 0.1% | 0.1% | 0.1% |

These are research gates, **not** claim of executable market impact. If spread/depth unavailable: eligibility UNKNOWN rather than false precision.

## Technical strategy

| Key | Default |
|---|---|
| `technical.ema_fast` | 20 |
| `technical.ema_slow` | 50 |
| `technical.ema_context` | 200 (context only) |
| `technical.atr_period` | 14, Wilder |
| `technical.rvol_window` | previous 20 bars excluding current |
| `pullback.proximity_atr` | [-0.5, +0.8] |
| `pullback.swing_lookback` | 5 completed bars |
| `pullback.stop_buffer_atr` | 0.25 |
| `pullback.chase_max_atr` | 0.5 |
| `breakout.resistance_lookback` | 20 **past** completed bars |
| `breakout.min_rvol` | 1.5 |
| `breakout.min_break_buffer_atr` | 0.1 (or >= 1 valid tick) |
| `breakout.extended_max_atr` | 1.5 |
| `breakout.stop_buffer_atr` | 0.5 |
| `target.min_gross_rr` | 2.0 target hypothesis, does not prove structural resistance |

## Scoring

| Component | Max |
|---|---:|
| Trend | 25 |
| Setup structure | 30 |
| Momentum/volume | 15 |
| Risk geometry | 20 |
| Market regime | 10 |

Details and source-specific rubric in [SCORING_RANKING](SCORING_RANKING.md); `score != probability`.

## Portfolio risk

| Key | Default |
|---|---:|
| `risk.per_trade_equity_pct` | 0.50% |
| `risk.max_open_risk_equity_pct` | 2.00% |
| `risk.max_single_position_equity_pct` | 20.00% |
| `execution.order_adv_participation_max_pct` | 0.10% |
| `execution.live_quote_required_for_trade_ready` | `true` |

**Do not** hardcode IDX tick price tables in this registry without effective-date metadata. They are market rules loaded from [UNIVERSE_LIQUIDITY](UNIVERSE_LIQUIDITY.md) / official sources, not strategy parameters.

## Versioning and experimentation

Change produces config version and SHA-256 hash, source rationale, date, benchmark and tests affected. Recommended experiment reporting: original defaults, altered parameter, markets, dataset period, number of trades, net expectancy, drawdown, coverage, cost sensitivity, OOS results. If a parameter has no evidence, leave baseline and label it explicitly. Never optimize on final untouched test period.
