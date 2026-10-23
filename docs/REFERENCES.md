# REFERENCES — External Sources and Implementation Inspiration

**Reviewed:** 2026-10-23. Links and vendor rules can change; check again before implementation/deployment. These links are **references**, not blanket permission to use market data or copy source code. No source repo was fully security-audited in this documentation effort.

## Official market/provider documentation

1. [BEI — Jam dan Mekanisme Perdagangan](https://www.idx.id/id/produk-layanan/jam-dan-mekanisme-perdagangan/) — lot 100, fractional ticks, board and sessions. As of review the page refers to **Kep-00136/BEI/09-2026**; historical rules need effective-date versioning.
2. [BEI — Saham dan Papan Pemantauan Khusus](https://www.idx.id/id/produk/saham/) — periodic call auction explanation and special-board context.
3. [Binance Spot API filters](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md) — PRICE_FILTER, LOT_SIZE, MARKET_LOT_SIZE, MIN_NOTIONAL/NOTIONAL.
4. [Binance Spot WebSocket streams](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md) — kline `x` finality, UTC/UTC+8 options, reconnect expectations.
5. [SEC EDGAR application APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) — public companyfacts/submissions; reporting period vs publication date.
6. [SEC EDGAR fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) — documented rate access restrictions (review actual limits each time).
7. [yfinance README](https://github.com/ranaroussi/yfinance) — research-oriented personal-use caution and adjusted-price behavior.
8. [Alpaca market data](https://docs.alpaca.markets/docs/about-market-data-api) — IEX vs SIP distinctions/entitlements; verify latest plan details before API integration.
9. [DuckDB Parquet](https://duckdb.org/docs/stable/data/parquet/overview) — filter/projection pushdown, research storage.

## Quantitative / programming references

- [Microsoft Qlib](https://github.com/microsoft/qlib) — quantitative research pipelines and workflows.
- [VectorBT](https://github.com/polakowo/vectorbt) — vectorized quantitative exploration; audit fill/fee assumptions before trust.
- [Backtesting.py](https://github.com/kernc/backtesting.py) — backtest modeling concepts.
- [Lightweight Charts](https://github.com/tradingview/lightweight-charts) — charting ideas; license and Flutter integration evaluated separately.
- [CCXT](https://github.com/ccxt/ccxt) — exchange abstraction inspiration, verify supported rate limits/market rules.
- [OpenBB/OpenBQ lineage](https://github.com/openbq-org/OpenBB) — modular data adapters; confirm active maintenance before dependency choice.
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — baseline temporal splitting, overlapping-label purging separately required.
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html) — empirical probability reliability.

## Product benchmark references

- [TradingView](https://www.tradingview.com/) — chart/screens/alerts inspiration.
- [FINVIZ](https://finviz.com/) — US equity filters, ranking/heatmaps.
- [Stockbit](https://stockbit.com/) — Indonesia equity analysis patterns.
- [StockAnalysis](https://stockanalysis.com/) — fundamental layout and financial presentation.
- [TrendSpider](https://trendspider.com/) — strategy and automated technical-analysis ideas.

## Engineering and trust notes

- Do **not** paste code from reference repos into proprietary project without checking dependency license, notices, copyleft obligations, maintenance and vulnerability state.
- Any unofficial provider may break without notice, throttle or change fields; use adapters and provenance.
- For crypto, price quote from one exchange is not globally universal; display the venue and pair.
- All liquidity thresholds, strategy parameters, risk budgets, and scores in our docs are **unvalidated design baselines**, not external source findings.

## Research log template (fill with experimental evidence later)

```
Date (UTC):
Topic / instrument / market:
Source URL + retrieved timestamp:
Rule version / data snapshot hash:
Hypothesis:
Method / dataset period:
Finding and limitations:
Decision / ADR link:
```
