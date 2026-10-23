# Swing Research Gate V2 (v0.3.0-alpha)

This release adds **research-only** qualification separate from the existing heuristic Setup Score. It does not activate a trade-ready or probability gate and does not assert any strategy is profitable. Implemented in `backend/app/domain.py` as pure, deterministic `evaluate_research_gate`.

## Signal-bar checks

- All four existing technical criteria must pass; indicators and 20-day resistance are built from EOD candles available at signal time. Resistance **excludes the signal candle**.
- Historical liquidity must pass the original ADV20, median-turnover, and price checks. A passing historical check is not a broker/execution approval.
- Entry must exceed stop, with positive ATR14. Stop risk must be between **0.5 and 4.0 ATR** as an explicitly provisional research screen (not an exchange rule or a validated optimum).
- Structural target must exist above entry. The displayed hypothetical 2R line **is not** substituted for a real structural target.
- Gross R:R is `(target-entry)/(entry-stop)`. Cost-aware research R:R applies an **illustrative 0.1% per-side** combined trading-friction proxy: `(target-entry-0.001*(entry+target))/(entry-stop+0.001*(entry+stop))`. Require net R:R at least 2.0. Real commissions, spread, fees, tax, gap risk and fills are not represented; a successful gate is not trade permission.
- `PASS`: research criteria met; status remains WATCH or research-only. `WAIT`: technical or structural target pending. `BLOCKED`: invalid geometry or stop distance. `EXCLUDED`: historical liquidity gate failed. **All results always return `trade_ready: false` and `execution_validated: false`.**

## Backward compatibility & operations

- Existing `setup.score`, `setup.status`, strategy names, journal, backtest, and stored immutable run snapshots are left intact. A new `setup.research_gate` object is additive. Legacy snapshots may lack it; UI shows "Not calculated" instead of fabricated values.
- The user must click **Run Scan** after updating. On the new run, Strategy Engine V2 appears on Asset Detail, with individually labelled research criteria and modeled risk geometry.
- No database migration required. No model training, broker integration, or changes to historical orders.

## Testing

`PYTHONPATH=backend python -m pytest -q backend/tests` including regression tests for fees pushing RR below 2, too-tight stops, missing targets, liquid exclusion, no trade execution, and no future-bar dependence.

## Known limitations

Stop/ATR bands and 0.1% modelled cost are **design assumptions** requiring out-of-sample calibration. Existing asset price tick/lot rounding is illustrative, and corporate actions, exchange session calendars, order books, quote/FX freshness, and provider uncertainty must be validated independently before trading.
