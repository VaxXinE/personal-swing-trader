# RISK_EXECUTION — Long-Only, Manual Fill, Position Sizing

**Status:** rules baseline unvalidated; no real-order connectivity.

## 1. Baseline personal risk guardrails

- Risk per proposed trade **0.5% account equity** (adjustable, logged).
- Max sum planned open-stop risks **2.0% equity** (adjustable). Does not guarantee max portfolio loss; overnight gaps can exceed stops.
- Max single-position capital allocation **20% equity** baseline; cap correlated groups/market exposure separately.
- Max position notional `<= available_cash` in trade currency; FX conversion needs as-of timestamp and conversion fee.
- Max participation <= **0.1% ADV20** (experimental baseline); quotes/depth/fee readiness required for live execution-ready status.
- No leverage, borrowing, short selling, spot crypto withdrawal, margin or real order submission.

## 2. Price plan

Price levels derived from [STRATEGY_SPEC](STRATEGY_SPEC.md). Validate `entry > stop > 0`, `target > entry` and executable tick increments. `R = entry - stop`; `reward_risk_gross = (target - entry)/R`. For net metric, deduct estimated round-trip fees, spread and slippage under recorded assumptions; don't present gross RR as net.

Stop can slip below desired level, especially during overnight gaps, BEI limit restrictions or volatile crypto. Show `risk_at_stop` as **planned model estimate**, not worst-case loss.

## 3. Position sizing algorithm

1. Read `equity`, `free_cash`, existing portfolio exposures and user risk setting.
2. Compute `risk_budget = equity * risk_pct`.
3. Compute `per_unit_planned_loss = (entry - stop) + estimated_unit_roundtrip_execution_cost`. Reject if <=0.
4. `qty_by_risk = floor_to_order_step(risk_budget / per_unit_planned_loss)`.
5. `qty_by_cash = floor_to_order_step(free_cash / (entry + estimated_unit_entry_cost))`.
6. `qty_by_alloc = floor_to_order_step((equity*max_alloc_pct)/entry)`.
7. `qty_by_liquidity = floor_to_order_step((ADV20*participation_cap)/entry)` after currency consistency.
8. `qty = min(all 4, optional-depth-cap)`; recheck exact fee model & order rules; if zero/under notional minimum -> reject.
9. Verify cumulative open risk, sector/market correlation caps and available units; return explanation per limiter.

Use `Decimal` and round **down** to allowed increment for quantity. IDX market regular lot = 100 shares; US fractional equities depend on user's broker (do not assume availability); crypto exchange `LOT_SIZE/MARKET_LOT_SIZE` step and min notional. Price tick rounding for long-buy limit, stop, target should use deliberate directional policy and validate resulting R:R; don't use generic `round()` which can move stop adversely.

## 4. Example (pure arithmetic, not a trade recommendation)

Equity 10,000,000 IDR, risk 0.5%=50,000 IDR, entry 2,000 IDR/share, stop 1,900 IDR/share. Planned price risk 100/share. Without fees, risk-based units=500 shares=5 lots and notional=1,000,000 IDR. With fees/slippage, resulting recommended units may be lower. Must additionally check capital, tick/market rules, liquidity and portfolio risk.

## 5. Fees / execution model

- Per broker/exchange configurable commission minimum, tier, trade tax, spread and slippage; source and effective date required.
- For backtest, model fills no earlier than possible; next-open baseline and pessimistic slippage.
- Intrabar simultaneous stop and target: conservative stop-first for estimated P&L unless smaller timeframe confirms sequence. Predictions treat label ambiguous distinctly.
- Partial fills, no fill, out-of-hours, halt/suspension, BEI daily limit/auction state and crypto order-rule errors must be modeled or flagged unsupported.
- Position entries are **not** executed by this app: `planned`, `paper`, and `actual manually recorded` states clearly distinct.

## 6. Risk plan response

```json
{
  "eligible": false,
  "status": "EXECUTION_UNKNOWN",
  "reasons": ["SPREAD_UNKNOWN"],
  "entry": "2000",
  "stop": "1900",
  "target": "2200",
  "currency": "IDR",
  "planned_risk_pct": "0.50",
  "max_order_qty": null,
  "fee_model_version": "fees-v0.1",
  "risk_disclaimer": "Stops are not guaranteed fills"
}
```

Illustrative result, not a validated trading setup.

## 7. Tests

- `qty` multiple of IDX 100 and crypto step, never exceeds cash/risk/ADV caps.
- Fee increase can reduce position; no zero/negative stop distance; valid tick rounding.
- High SQS with unknown quote => not execution verified.
- Currency USD vs IDR mixed without FX quote => hard failure.
- Broker fractional shares not supported => integer rounding.
- Gap under stop => realized P&L can exceed nominal planned risk; do not cap artificially.
