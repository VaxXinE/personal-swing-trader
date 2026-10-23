# PREDICTION_VALIDATION — Forecast Laboratory and Release Gate

**Status:** GATED. **There is no trained model, no measured accuracy, and no validated forecast at document creation.**

## Why forecasting is separate

An LLM explanation is **not** a price forecast model. SQS rank describes rule quality, not empirical odds. Forecasts must be reproducible, calibrated, measured on out-of-sample historical and forward data, and labelled with samples/uncertainty.

## 1. Distinct research targets

- **Barrier race:** given a **specific executable entry**, stop, target and horizon H, label which event occurs first: `TARGET_FIRST`, `STOP_FIRST`, `TIMEOUT`.
- **Close-horizon distribution:** quantiles of `log(Close_(t+H)/entry_fill)` with corporate-action/holding-period conventions documented. This differs from within-window touch outcomes.
- **MFE/MAE:** maximum favorable/adverse excursion observed **between entry and exit/horizon**, not unconditional peak-to-trough levels.
- **Net trade expectancy:** expected R multiple *after modeled fees/slippage*, conditional on strategy/regime; must be estimated from labeled trades, not scores.

Sum of mutually exclusive barrier probabilities approx 1 within numerical tolerance. When both stop and target touched inside one OHLC bar with unknown path, label `AMBIGUOUS` and apply a declared conservative convention for strategy P&L; do **not** mislabel as known target-first. For prediction training, exclude ambiguous labels or use an explicitly justified separate class/policy and sensitivity test.

## 2. Training feature controls

Allowed only inputs `feature.available_at <= prediction.created_at`: lagged returns, EMA distances, ATR%, RVOL, relative strength vs market, market regime, structure characteristics, liquidity features with fresh timestamp, event flags published on time. Exclude future adjusted fundamentals, total next-day volume, late revisions. Features identical between historical train and live inference paths.

## 3. Model progression

1. **Baseline A:** unconditional base rate by market, strategy, horizon, regime.
2. **Baseline B:** nearest comparable historical conditional bucket / logistic regression.
3. **Optional ML:** gradient-boosted classifiers with careful time-series CV; quantile regression for distribution.
4. **Calibration:** fit on validation split distinct from training/test; sigmoid/isotonic only where sample size sufficient. Compare Brier score, log loss, calibration curve, reliability by probability bin.
5. **Forward paper validation:** append-only predictions saved at creation time, observed later without changes.

No Transformer/LSTM requirement. If ML not outperform baselines OOS after fees and in reliability, do not use it in final UI.

## 4. Temporal splitting

- Split by chronological **event availability** time, not random rows; e.g. train older years, calibration immediately later, test latest untouched block.
- Labels for H-session outcomes overlap: **purge training examples whose outcome window overlaps validation/test start**; configurable embargo if appropriate.
- Nested tuning conducted *inside* historical training window, not on final test set; avoid selection bias across dozens of variants.
- Survivorship: include delisted and historical eligible instruments where datasets support, otherwise explicitly report limited coverage and no strong claim.
- Freeze final test once per candidate model; rerunning until favorable violates scientific evaluation.

## 5. Validation card requirements

Prediction panel must show model ID + hash/version, training/validation/test date ranges, market, strategy, horizon, sample N, valid data coverage, fraction ambiguous, calibration and baseline delta, confidence interval where appropriate, evaluation date, and `STATUS`.

Release gate requires, at minimum:
- [ ] No leakage/invariant tests pass; train/validation/test separation audited.
- [ ] Adequate effective independent samples for every subgroup shown (threshold decided *before* experiment and logged); enough positives/negatives/timeouts to calibrate.
- [ ] Calibration curve, Brier/log loss, quantile empirical coverage reported OOS and forward.
- [ ] Baseline comparison and execution-cost sensitivity reported; no severe regime-specific degradation hidden by aggregate.
- [ ] Outlier/event/low-volume robustness and confidence ranges documented.
- [ ] Model registered as `VALIDATED_FOR_RESEARCH` by explicit manual review; production forecast release recorded as decision.

If any required check fails => response `forecast_status: NOT_VALIDATED` and hide probabilities in consumer UI.

## 6. API contract (when gated on)

```json
{
  "status": "NOT_VALIDATED",
  "model_version": null,
  "horizon": {"value": 10, "unit": "TRADING_SESSIONS"},
  "probabilities": null,
  "price_quantiles": null,
  "validation": null,
  "reason": "Forecast has not passed release criteria"
}
```

The default above is actual intended behavior until model validation completes. P10/P50/P90 and `target_first` numbers must never be inserted as examples in production UI.

## 7. Model drift/retrain

Monitor realized calibration, sample coverage, model vs baseline, feature distribution changes, provider revisions, regime shifts and data missingness. Drift ⇒ degrade to baseline/NOT_VALIDATED, not automatic unreviewed retraining. Every model release has rollback and immutable artifact/hash.

## 8. Research tooling reference

scikit-learn `TimeSeriesSplit` with gap **alone may be insufficient** for overlapping labels; implement event purging specifically. See [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html), [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), and [BACKTESTING](BACKTESTING.md).
