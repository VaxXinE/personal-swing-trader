# API_CONTRACT — Private REST/WebSocket V1

**Alpha note:** `DEMO` is an explicit synthetic fixture state; implemented response/enpoint subset differs from target contract. See [IMPLEMENTATION_STATUS](../IMPLEMENTATION_STATUS.md) and generated FastAPI OpenAPI for actual implemented endpoints.

**Base:** `/v1` · **Transport:** HTTPS via VPN/access proxy for remote client; loopback HTTP acceptable only on single-host dev. Default network not publicly reachable. All examples **mock data**.

## 1. Conventions

- JSON UTF-8; `snake_case`; UTC RFC3339 timestamps; decimals serialized as **strings**; source and freshness metadata required on market-sensitive responses.
- `X-Request-ID` returned; private API auth through Tailscale identity-aware proxy/session token as configured; **never** embed permanent bearer token in Flutter bundle.
- Pagination: `limit` 1..100, opaque `next_cursor`. Input size limits and query time budget.
- Writes support `Idempotency-Key` for duplicate safe operations. Version changes return new record rather than silently overwriting.
- `as_of` is data evaluation time, `generated_at` response time. `data_status` enum `DEMO|REALTIME|DELAYED|EOD|STALE|UNAVAILABLE` separate from `quality`.
- Always include `instrument_id`, `market`, `exchange`, `quote_currency` where instrument is displayed.

## 2. Endpoints

| Method | Path | Purpose | FR |
|---|---|---|---|
| GET | `/health/live` | process health, no sensitive details | NFR-008 |
| GET | `/health/ready` | DB/data store dependencies checked (auth protected) | NFR-008 |
| GET | `/v1/markets/status` | session calendars/provider health | FR-018 |
| GET | `/v1/instruments` | search, market, status, cursor | FR-001/004 |
| GET | `/v1/instruments/{id}` | instrument metadata and lifecycle | FR-001 |
| GET | `/v1/universe` | as-of included instruments and configs | FR-003 |
| GET | `/v1/universe/exclusions` | reason codes, filter counts | FR-004 |
| POST | `/v1/screeners/validate` | validate typed AST only; no execute | FR-006 |
| POST | `/v1/screeners` | create saved screener version | FR-007 |
| GET | `/v1/screeners` | list versions | FR-007 |
| POST | `/v1/screeners/runs` | submit scan, returns job handle | FR-006/007 |
| GET | `/v1/screeners/runs/{id}` | status + snapshot metadata | FR-007 |
| GET | `/v1/opportunities` | filter/rank published runs | FR-008–010 |
| GET | `/v1/instruments/{id}/analysis` | explanations/levels/data lineage | FR-011 |
| POST | `/v1/risk/size` | deterministic sizing calculation | FR-012 |
| GET/POST | `/v1/watchlist` | watchlist list/add | FR-013 |
| DELETE | `/v1/watchlist/{id}` | soft-remove record | FR-013 |
| GET | `/v1/signals/{id}` | original immutable signal and events | FR-014 |
| GET/POST | `/v1/journal/trades` | personal paper/manual trade journal | FR-014 |
| GET | `/v1/forecasts/{signal_id}` | null probabilities until model validated | FR-020 |
| GET | `/v1/jobs` | job history + errors | FR-018 |
| GET | `/v1/stream/watchlist` | authenticated private stream P1 | FR-022 |

## 3. Example: opportunities response

```json
{
  "generated_at": "2026-10-23T12:10:00Z",
  "run_id": "run_demo_001",
  "as_of": "2026-10-22T20:00:00Z",
  "data_status": "EOD",
  "market": "US",
  "strategy": "PULLBACK_V0_1",
  "items": [{
    "instrument_id": "US:NASDAQ:DEMO",
    "quote_currency": "USD",
    "setup_score": 85,
    "score_status": "COMPLETE",
    "entry_readiness": 42,
    "eligibility": "WATCH",
    "blocking_reasons": ["ENTRY_TRIGGER_NOT_MET"],
    "prediction_status": "NOT_VALIDATED",
    "last_final_candle_at": "2026-10-22T20:00:00Z",
    "source": "example_fixture"
  }],
  "next_cursor": null
}
```

Never return made-up prices. If quote unavailable return explicit null and data state. `as_of` here illustrative; exact US close varies by DST and calendar.

## 4. Example: screener AST validation

```json
{
  "markets": ["US","IDX"],
  "timeframe": "1d",
  "op": "AND",
  "children": [
    {"field":"close","operator":"GT_FIELD","value":"ema_50"},
    {"field":"rvol_20","operator":"GTE","value":1.5}
  ]
}
```

Server applies whitelist typed fields (`price`,`percent`,`currency`,`ratio`,`enum`,`bool`), valid operators for each type, allowed market/timeframe, max depth 5, max nodes 50, finite numeric bounds and max query time. **No** `eval`, untrusted SQL fragments, user-provided Python snippets, arbitrary expressions in rules, or arbitrary filesystem paths. Unavailable field is `UNKNOWN`, not false unless expression semantics explicitly selected; `NOT UNKNOWN` never silently yields true.

## 5. Error codes

```json
{
  "error": {
    "code": "DATA_UNAVAILABLE",
    "message": "Bid/ask belum tersedia; kelayakan entry tidak dapat diverifikasi.",
    "request_id": "req_example",
    "retriable": true,
    "details": {"field": "quote.bid_ask"}
  }
}
```

Use 400 invalid request, 401 unauthenticated, 403 forbidden, 404 not found, 409 version/state conflict, 422 typed rule invalid, 429 local rate limit, 503 provider/data outage. Messages never leak API keys, raw stack traces, private file paths, or entire provider payloads.

## 6. WebSocket (optional P1)

Event envelope `{type,event_id,instrument_id,event_at,received_at,data_status,sequence,payload}`. Client handles reconnect, gap detection and REST snapshot reconciliation; server controls subscriptions to watchlist instruments only. Real-time label only when actual feed entitlement/timestamp supports it.

## 7. Versioning, test and docs

OpenAPI generated from FastAPI/Pydantic; contract-test Flutter DTO serialization; schema-breaking change increments `/v2` or feature-negotiated version. Any response field that affects trading interpretation needs regression fixture. UI must show provenance at detail level.
