# Dynamic Liquid Universe V2 — Engineering Contract

**Status:** Implemented as opt-in discovery + audited historical liquidity gate, 2026-10-23. **NOT** a whole-market liquid screener, real-time exchange listing service, or trade-execution validator.

## Goal

Expand the initial 19-symbol manual registry without hardcoding more names, using public listing/trading metadata where permitted, then require the existing 20-session historical turnover gate before assets appear in default Explore. Every scan result is still research-only.

## Modes and data lifecycle

1. `config/universe.json`: stable user-maintained baseline, authoritative on duplicate canonical IDs.
2. `python scripts/sync_universe.py --markets US CRYPTO`: user-initiated discovery. This command uses known HTTPS provider hosts (no user-supplied API URL). It writes `data/discovered_universe.json` atomically; the file is gitignored.
3. `--markets IDX --idx-file <path.xlsx>`: import an **official IDX Excel listing** (CSV is also accepted) with `Kode`, `Nama Perusahaan`, optionally `Papan Pencatatan`. Does not fetch/scrape unofficial IDX APIs. Rows from Papan Pemantauan Khusus are excluded **only if** column is present; absence of board info is NOT a status verification.
4. In LIVE mode only, `registry.get_instruments('live')` merges baseline + discovery, up to 250 unique canonical IDs. DEMO intentionally uses the 19 baseline instruments to keep tests deterministic.
5. **Run Scan separately** to compute OHLCV history, 20-session ADV/median turnover, EOD indicators, score, and exclusion reasons. Latest scan is stored as an immutable snapshot. A new sync DOES NOT mutate an old scan.
6. GET `/v1/universe/discovery` provides source/sync provenance and counts; `/v1/opportunities` provides per-market attempted/analyzed/excluded/errors coverage from the last scan. Data Health shows both. No network calls during ordinary screen viewing.

## Provider-specific behavior

| Market | Discovery | Eligibility caveat |
|---|---|---|
| US | Nasdaq Trader `nasdaqlisted.txt` and `otherlisted.txt`; exclude ETF/test/special instruments and known Nasdaq financial status issues | Official directory has no turnover. Deterministic month-rotating symbol sample is NOT the top liquid companies or full-US scan. Provider may change text fields. The 20-day ADV filter runs later. |
| Crypto | Binance spot `exchangeInfo` + rolling-24h `/ticker/24hr` in USDT, capped top-ranked by recent quote volume | 24-hour quote volume only prescreens candidates. It is not ADV20. The scanner checks final daily candles, historical turnover, spread when available and active-symbol status. Region/provider availability may vary. |
| IDX | Direct .xlsx import (or CSV) from IDX listing page | No reliable public automatic IDX directory adapter is claimed. File age, board/suspension status and tick histories need independent verification. |

Listings do NOT prove active accessibility at the user's broker. A symbol's live tradability / corporate action / exchange calendar / split handling remain incomplete. Quote freshness and transaction cost can prevent execution verification even when a historical liquidity filter passes.

## CLI examples

```bash
# From repository root, with .venv activated or python3 accessible:
python scripts/sync_universe.py --markets US CRYPTO
python scripts/sync_universe.py --markets US --us-limit 15
python scripts/sync_universe.py --markets IDX --idx-file "$HOME/Downloads/Daftar Saham.xlsx" --idx-limit 35
# After sync, start (or keep) the live backend and click Run Scan in dashboard:
bash scripts/start.sh --live --port 8001
```

Set each per-market limit from 1 to 75; baseline + discovery cannot exceed 250 combined. Default is 24 US + 18 crypto; IDX defaults to 35 when explicitly imported. A provider failure gives a nonzero CLI exit and retains the last successful candidates for that market rather than secretly substituting made-up symbols. Provider errors are visible in CLI output. If a source's response format changes, parser fails closed.

## Performance and operational safety

- Market-data collection is still **sequential** and can be slow. The command only updates listing candidates; OHLCV requests happen later during Run Scan. For large universes, run the scan via `python scripts/scan_once.py` in a terminal instead of relying on an HTTP request that a browser might abandon.
- Successful LIVE provider reads cache in memory for a bounded 15-minute bucket to reduce accidental repeated calls; they are EOD, not live bids for order placement. No failures are cached.
- Avoid repeated manual discovery calls; providers have network restrictions and rate limits. Endpoint and schema changes are treated as errors, not as missing liquidity.
- Dynamic files are local under `data/` and excluded from Git; `.env`/keys/journals remain excluded. Do not deploy CLI discovery as an unauthenticated public API.
- No trading execution, authenticated broker support, real-time alerts, ML forecasts, or benchmark-calibrated cross-market score in this release.

## Verification and known limitations

Tests use local fixture responses and exercise parser validation, 24h-vs-ADV distinction, IDX XLSX/CSV, shifted headers, multiple sheets, malformed workbook, fail-preserving snapshot, registry precedence, and API coverage. No real provider production connectivity was verified in the build environment. US 'liquid' candidates may be few when the directory's selected samples are illiquid. A future US price/volume first-stage source would improve candidate selection, but should not be fabricated from directory membership.

Suggested next steps: official IDX status/calendar integration, batched historical data retrieval with provider throttling, quote freshness/reconciliation, proper time-aware historical universe snapshots, and price-source confidence validation.

## IDX official XLSX importer (0.2.1-alpha)

The importer reads `.xlsx` using a constrained OOXML parser with no runtime spreadsheet dependency. Shared strings and inline string cells are supported; formulas are **never evaluated**. It selects the worksheet with the most valid IDX codes and searches for known column headers within the first 40 nonempty rows. Column order can vary; blank or explanatory rows before the header are allowed. Source files are read-only and not uploaded to any service.

Accepted headers include `Kode`, `Kode Saham`, `Nama Perusahaan`, `Nama Emiten`, and optionally `Papan Pencatatan`. Valid listed codes must be exactly four A-Z letters. The user-exported sheet is not an authoritative live suspension feed. A malformed/oversized Excel file fails closed and does not replace the previous successful discovery snapshot. An eight-megabyte compressed size and 36-megabyte inflated XML limit reduce zip-bomb risk. `.xls` and `.xlsm` are deliberately not accepted.

IDX discovery remains capped at 75 new candidates per sync. A successful import does not imply Yahoo Finance daily OHLCV is available for every ticker; check Data Health after Run Scan.

## IDX selection and scan coverage (0.2.2-alpha)

The official IDX listing is sorted by code, not liquidity. Earlier builds sampled the first 35 ticker rows (mostly A-prefixed stocks). New imports sample from across the valid listing using a deterministic SHA-256 order that is stable within each UTC calendar month. Samples are not liquidity-ranked or guaranteed to pass the historical liquidity gate. The baseline instruments remain in the merged registry. To see a new IDX sample, run the `--markets IDX --idx-file ...` sync command again; an ordinary `git pull` does not mutate local universe data.

The `/v1/opportunities` `coverage` now includes `liquidity_passed` and `insufficient_history` per market. An instrument lacking 60 completed candles is a rejected research input (`category: INSUFFICIENT_HISTORY`), not necessarily an HTTP/provider outage. Every attempt is counted once per asset even though each analyzed asset may produce multiple strategy evaluations. `liquidity_passed` is historical only and does not mean an order is executable.
