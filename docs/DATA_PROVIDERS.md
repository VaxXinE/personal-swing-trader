# DATA_PROVIDERS — Source Strategy and Fallback

**Status:** candidate adapters, not provider entitlement verification. Private use does **not** waive API/ToS restrictions.

## Priority matrix

| Domain | Initial candidate | Strength | Known limitation / rule |
|---|---|---|---|
| US/IDX OHLCV research | yfinance | Simple historical equities, `.JK` symbols for Indonesia | Unofficial Yahoo access; user must comply with terms, missing/rate-limited data possible; adjusted prices need explicit config |
| US fundamentals | SEC EDGAR companyfacts/submissions | Primary US regulatory filings | Company mapping, normalizing XBRL, point-in-time release; fair access/request headers |
| US quotes optional | Alpaca market data | Documented feeds | Free IEX feed is **not** full consolidated US market; entitlements differ |
| IDX listings/rules | IDX official pages/files | Status boards, sessions, lot/tick rules | Stable machine-readable history and quotes not guaranteed |
| IDX prices first pass | yfinance `.JK` | Cheap prototype | Check completeness, timezone and adjustments; official turnover/order book may be missing |
| Crypto spot | Binance public REST/WebSocket | Exchange metadata, OHLCV, bid/ask, quote volume, depth | Exchange/pair-specific; reconnect/rate limits; availability and access rules vary by jurisdiction |
| Filing/news P1 | SEC + market-specific public announcements | Real source evidence | No LLM invented dates, labels or guidance |

Do not imply any provider supplies information it does not. Example: `yfinance` OHLCV is **not** proof of real-time IDX order book. If missing, output `UNKNOWN` and reject `EXECUTION_VERIFIED`.

## Provider interface

```python
class MarketDataProvider(Protocol):
    async def instruments(self, as_of: datetime) -> list[Instrument]: ...
    async def candles(self, instrument_id: str, timeframe: str,
                      start: datetime, end: datetime) -> CandleBatch: ...
    async def quote(self, instrument_id: str) -> Quote | Unavailable: ...
    async def rules(self, instrument_id: str, as_of: datetime) -> MarketRules: ...
```

Adapters return provenance, `as_of`, `available_at`, `received_at`, `adjustment_method`, `currency`, `market_timezone`, `quality_flags`. They never return sentinel prices like zero for unavailable data.

## Fallback policy

1. Primary fails → retry with exponential backoff within rate budget and record failure.
2. Secondary source available → normalize, cross-check difference and identify provider chosen. A fallback cannot silently change from adjusted to unadjusted prices.
3. Source mismatch beyond configured tolerance → `DATA_CONFLICT`, quarantine from signals until inspected.
4. Missing quotes → use archival EOD for research only and show *data delayed/stale*; **cannot** mark execution verified.
5. Never bypass anti-bot, CAPTCHAs, auth or paywalls, and never redistribute data contrary to terms.

## Rate limiting & fetch hygiene

- Per-provider token bucket; bounded concurrency, explicit User-Agent where required, no high-frequency polling for swing strategy.
- SEC fair access guidelines currently mention 10 requests/second maximum; set safer local budget and revisit latest documentation.
- Provider calls timeout and support circuit breaker; record request ID but redact credentials.
- Crypto stream: handle ping/pong, reconnect, gap backfill; do not trust first update as final candle.
- Quotes tag entitlement: `REALTIME`, `DELAYED`, `EOD`, `UNKNOWN` based on documented feed and actual timestamp.

## Validation before expanding to full universe

Pilot 10–20 instruments per market; compare at least several known corporate actions and holidays, price/volume deltas between trusted sources when allowed, completeness and latency. Store findings in research log (new future file) before enabling full scanning.

## Sources

- [yfinance README](https://github.com/ranaroussi/yfinance#readme) (personal-use caution)
- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- [Alpaca data feed overview](https://alpaca.markets/support/data-provider-alpaca)
- [IDX hours and trading mechanics](https://www.idx.id/id/produk-layanan/jam-dan-mekanisme-perdagangan/)
- [Binance Spot API docs](https://github.com/binance/binance-spot-api-docs)
