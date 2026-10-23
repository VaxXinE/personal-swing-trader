# EXPLANATION_POLICY — Evidence-First Analysis

**Status:** LOCKED trust boundary and explanation requirements; provider sources optional / staged.

## 1. What the analysis must answer

For every asset setup, explain in Indonesian (technical terms acceptable):
1. **Kenapa terdeteksi?** actual strategy conditions and values, with comparisons/thresholds.
2. **Kenapa menarik?** price structure, momentum, liquidity, regime, and supporting available fundamental facts.
3. **Kenapa bisa salah?** contradictory evidence, market event, weak data, liquidity or technical invalidation.
4. **Di harga berapa?** planned entry/stop/target in native currency, tick valid, net/gross RR distinguished.
5. **Kapan berubah?** as-of scan, expiry or invalidation rule, next expected scan.
6. **Seberapa terbukti?** model/data validation state and original event outcome if available.

## 2. Deterministic evidence record

Each reason has `rule_id`, `observed_value`, `operator`, `threshold`, `passed`, `source`, `source_event_at`, `available_at`, `snapshot_id`, `severity`, `human_template_key`. Use a template formatter as first implementation, no generative LLM required.

```json
{
  "rule_id": "BREAKOUT_RVOL_MIN",
  "observed_value": "1.8",
  "operator": ">=",
  "threshold": "1.5",
  "passed": true,
  "source": "provider_candle_snapshot",
  "available_at": "2026-10-22T20:05:00Z",
  "severity": "SUPPORTING",
  "human_template_key": "rvol_above_threshold"
}
```

Example only; not actual market evidence.

## 3. Fundamental and crypto context

- Equity fundamental: revenue/earnings cash flow/leverage/valuation trends with company reporting type, currency, filing version, publication timestamp. Ratios need sector-specific semantics; bank liabilities aren't software-company debt.
- Near-term catalysts: earnings, guidance, regulatory filing, dividends and announcements. Only factual event with authoritative source.
- Crypto: on-chain/unlock/TVL/token supply events **only if provider reliable and timestamp available**; no P/E/ROE analogy. Verify event identity, exchange vs chain distinction.
- Technical evidence can't establish causation for price moves. Wording: “bertepatan dengan” or “didukung oleh indikator” rather than causal “naik karena X” without evidence.
- If fundamental/event provider unavailable, show `FUNDAMENTAL_UNAVAILABLE`, do not hallucinate rationale or reduce technical score by default.

## 4. Optional LLM explainer gate

LLM can **paraphrase** a structured evidence bundle, never decide price, change risk limits, compute independent score, modify strategy config, run tools/order, or invent data. Retrieve only source-linked approved evidence; constrain output to a schema with reason IDs; verify referenced IDs exist, values match, and HTML/Markdown safely rendered. Untrusted news prompt injection treated as inert content. If verification fails, fall back to deterministic templates.

## 5. UI requirements

Every positive reason can expand to observed number + timestamp + source, every negative reason shown near positive ones; risk prominently displayed, not buried in disclaimer. `UNKNOWN` facts separated from negative facts. Display data/projection age with label; no artificial confidence decimals.

## 6. Test cases

- Bad or contradictory news feed never overrides validated raw price and never executes any instruction.
- Missing filing can't become “earnings improved”.
- Different timeframe data noted; no comparing daily RVOL with intraday current unfinalized volume.
- A high score with R:R blocker must show blocker before “bullish” promotional copy.
- Two snapshots at different times have different evidence version while earlier original remains intact.
