# OPEN_QUESTIONS — Known Unknowns and Safe Defaults

None of these prevents scaffolding, test fixtures, pure strategy code or data-quality work. They **do** gate claims about live data or production-ready trading conditions.

| ID | Question | Interim default | Blocking which milestone? |
|---|---|---|---|
| OQ-001 | Where does backend run 24/7? home PC, mini PC, VPS? | local laptop / manual EOD runs | always-on alert M6 |
| OQ-002 | Exact brokers/exchanges user trades on? fractional US equity, crypto pairs? | informational analysis only, no broker-specific fill guarantee | execution_verified for each instrument M3 |
| OQ-003 | Approved and available real-time bid-ask for US/IDX? | `UNKNOWN` execution spread; EOD research mode only | Trade Ready on those markets |
| OQ-004 | Official IDX as-of listings/board history, turnover, corporate actions? | best available data with provenance and coverage warning | full-market historical validity M5 |
| OQ-005 | Currency base and portfolio capital? | risk module accepts explicit currency/equity, no inferred value | personalized position sizing M4 |
| OQ-006 | Risk parameter fine tuning? | 0.5% per trade, 2% sum, 20% max per asset, versioned | strategy promotion M5 |
| OQ-007 | Which crypto exchange/legal regional endpoints? | Binance **public data as research** if access permitted | actual exchange execution checks M3 |
| OQ-008 | What data retention/backup target? | encrypted local/secondary backup suggested | reliable M6 operation |
| OQ-009 | Are official US market lifecycle/delisting historical datasets available? | incomplete survivorship coverage warning | strong OOS market-wide claims M5 |
| OQ-010 | Should fundamental news feeds be integrated? | UI placeholders marked unavailable; no unsupported score impact | P1 only |
| OQ-011 | What exact acceptable SLO for app latency and provider freshness? | measure baseline in pilot, do not invent SLA | M4/M6 tuning |
| OQ-012 | When to promote forecast confidence/probabilities? | never by default; requires research review | M7 |

## Research action for each open question

- Document vendor source URL/terms and checked date.
- Run instrument-level pilot and quantify coverage, lag, missingness and biases.
- Decide with explicit ADR and alter gate/tests as needed.
- Do not fill unavailable values with guesswork or UI placeholders that appear real.
