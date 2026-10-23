# DESIGN — UX/UI Specification

**Version:** 0.1.0 · **Status:** design blueprint (no Figma/mockup signed off) · **Platform:** Flutter Android mobile-first, iOS optional.

## 1. Design principles

1. **Answer-first:** tampilkan status peluang, alasan dan risiko sebelum indikator detail.
2. **Progressive disclosure:** beranda sederhana, drill-down teknikal/fundamental dapat dibuka saat dibutuhkan.
3. **No fake certainty:** score selalu berlabel `Setup score`, bukan `Win probability`. Forecast hanya bila tervalidasi.
4. **Data transparency:** badge `LIVE`, `DELAYED`, `EOD`, `STALE`, `UNAVAILABLE` dan last update setiap view terkait.
5. **Risk visually prominent:** stop, invalidation, estimated cost dan eligibility setara penting dengan upside.
6. **Cross-market without false equivalence:** currency, kalender, metric, dan rankings dibedakan.

## 2. Navigation map

Bottom navigation **Home**, **Explore**, **Watchlist**, **Journal**; halaman **Asset Intelligence** dibuka dari card/search; **Screener Builder**, **Compare**, **Run History**, **Settings & Data Health** dari Explore/menus. Batasi tab utama menjadi empat supaya mudah dijangkau satu tangan.

```text
Home ─── opportunities / regimes / top alerts
  ├── Asset Intelligence ──> Trade Plan / Evidence / Chart / History
  └── Alerts
Explore ─── market / strategy / sort / results
  ├── Custom Screener Builder ──> Save/Validate/Run
  ├── Excluded Assets
  └── Compare Candidates
Watchlist ─── watch setups + recent triggers
Journal ─── paper/actual manual trades + analytics
Settings ─── data providers / sync health / privacy / backups
```

## 3. Screen specs

### Home

- Header: current market mode (US/IDX/Crypto/All), `last completed scan`, badge freshness, settings shortcut.
- Market regime summary **per market**; never one `market bullish` label applied to all.
- Sections: `Trade Ready` (may be empty), `Watch Closely`, `Recently Invalidated`, `Data Health Warnings`.
- Card: symbol + venue, latest *as-of* price, daily percent change with currency, strategy, Setup Score, state, 1–2 supporting factors, one risk factor.
- Tapping card → asset detail; any failed data gate clearly indicated.

### Explore / Screener Results

- Primary filters: Market segmented tabs; strategy chips; minimum score slider; sorting: Setup Score / Entry Readiness / Symbol; search.
- Advanced filters hidden in sheet; show active filter count and reset.
- Include `Excluded` toggle with reason and ability to open asset for study without misleading Trade Ready.
- Results grouped by market; `All` uses interleaved balanced groups, not one deceptively comparable global rank.
- Infinite list or pagination; deterministic snapshots and stable sort.

### Custom Screener Builder

- Rule groups nested `ALL`, `ANY`, `NOT`, add condition from typed catalog; display unit, description and valid range.
- Inline validate field + operator compatibility. Preview includes `matched / rejected / unknown` counts and examples of exclusions.
- Save **creates new version**, asks explicit name; edit and clone existing preset without overwriting history.
- Show `Run on latest finalized snapshot` and optional backtest replay, with data availability pre-check.
- Clearly signal when rule uses unsupported field on a selected market.

### Asset Intelligence

Sections ordered: (1) summary/status and freshness; (2) setup/risk plan; (3) chart with support, resistance, EMA and user-toggleable overlays; (4) positive/negative evidence and timestamps; (5) liquidity/execution feasibility; (6) historical record/projection if validated; (7) fundamental/event evidence if available.

- Sticky asset identity and quote timestamp; **not** a giant AI recommendation banner.
- Trade Plan shows `WAIT`, `READY`, `TRIGGERED`, `INVALIDATED`, `UNKNOWN`, `EXPIRED`; every status includes exact blocking/passing rules.
- Entry, stop and target are labelled **indicative planned levels**, converted to valid tick; `estimated slippage` if data supports it.
- A high score with `WAIT` must be shown as **not entry-ready**.
- Prediction UI when gate off: `Probabilities not validated` with no example percentages.

### Watchlist & Alerts

- Watchlist rows grouped `Approaching`, `Triggered`, `Invalidated`; quick note, rule, last checked, alert status.
- Alert detail links to **new analysis** and **original immutable snapshot**, showing differences.
- Deduplicate `(instrument_id, setup_id, event_type, event_version)`.
- Do not send persistent notifications for every candle or every price tick.

### Journal

- Record manually executed or paper order: market, broker/exchange, entry/exit timestamps, shares/units, fees, cash currency, stop plan, notes, screenshot optional.
- Separate `estimated/planned` and `actual` values; realized outcome based only on actual fills entered by user.
- Summary: R multiple, fees, win/loss, max drawdown for recorded trades, model/preset breakdown; `insufficient sample` prominently if applicable.

### Data Health / Settings

- Provider connectivity, latency, last successful EOD, data gaps, quote source, license/terms notes, backup status, API redaction test.
- Threshold presets and max risk with explicit `BASELINE` warning.
- Switch for strict mode: missing live quotes always blocks `EXECUTION_VERIFIED` (default ON).

## 4. ASCII wireframes (not pixel-perfect)

```text
┌──────────────────────────────────┐
│ SWING INTELLIGENCE   EOD 22:10  │
│ [US] [IDX] [CRYPTO] [ALL]        │
│ Market regime: US bullish       │
│ Trade Ready (2)  >              │
│ ┌──────────────────────────────┐ │
│ │ DEMO  [BREAKOUT] Score 84    │ │
│ │ READY | Entry 100 Stop 95    │ │
│ │ +Volume   -Earnings soon     │ │
│ └──────────────────────────────┘ │
│ Watch Closely (13)  >           │
│ Data status: ✓ 2 providers ⚠ 1  │
├──────────────────────────────────┤
│ Home  Explore  Watchlist Journal │
└──────────────────────────────────┘
```

```text
┌──────────────────────────────────┐
│ ASSET DEMO   US:NASDAQ           │
│ $100  EOD • updated Oct 22       │
│ 84/100 SETUP SCORE   [WAIT]      │
│ Reason: trigger not confirmed    │
│ Entry ~$101 Stop ~$96            │
│ Target ~$111 • RR 2.0 (gross)    │
│ [Price chart]                    │
│ + Strong trend, volume rising    │
│ - High event risk                │
│ Data: source / as_of / version   │
│ [Add to watchlist] [View audit]  │
└──────────────────────────────────┘
```

All symbols and prices above are fictitious **UI examples**, not analysis.

## 5. Component library and visual tokens

- Typography: 3 size tiers for hierarchy, tabular numbers for prices/scores, supports dynamic text scale 200%.
- Palette semantic: positive / negative / caution / neutral; never rely on color alone (`+`, `−`, icons, labels always visible).
- Spacing: 4pt base, comfortable touch area **at least 44 × 44 logical pixels** as target; verify Flutter platform semantics.
- Charts: pinch-zoom, pan, marker tooltips, crosshair, tap source/time; do not draw heavy overlays by default.
- Dark mode first is a preference, **both light/dark contrast tested**; avoid trading-terminal visual clutter.
- Offline states and loading skeleton must not reuse old values with live badge.

## 6. State design and microcopy

| State | Copy exemplar | Action |
|---|---|---|
| Loading | `Memuat data pasar...` | non-blocking skeleton |
| Empty filter | `Tidak ada aset memenuhi aturan. Lihat alasan penolakan.` | open exclusions |
| Stale quote | `Harga terakhir dari 14:23; data tidak lagi fresh.` | Refresh / source detail |
| Feature unknown | `Spread tidak tersedia; kelayakan eksekusi belum diverifikasi.` | maintain WAIT |
| Not validated | `Model probabilitas belum lolos pengujian.` | Show method, not numbers |
| Provider down | `Sumber data sementara gagal. Scan terakhir tetap bisa dibuka sebagai arsip.` | Retry |
| Invalidated | `Setup dibatalkan: harga menembus invalidation level.` | show original thesis |

## 7. Interaction & accessibility requirements

- Screen reader labels include market, currency, value, update time, status, meaning of score.
- User can reach core actions with screen reader & larger fonts; chart insights replicated as text.
- Keyboard handling, numeric input, local number grouping, explicit currency, confirmation before deleting journal entries.
- No financial decision solely communicated via animation/color; motion reduction respected.
- No hardcoded claim of 'live' if vendor only supplies delayed/EOD data.

## 8. Design acceptance checklist

- [ ] From Explore user can build and save a custom scan without code.
- [ ] From every result user can see score breakdown, blockers, and last-updated metadata.
- [ ] Data errors, unsupported market filters, zero results, empty journal, and offline states have meaningful UI.
- [ ] No probability shown when model is NOT_VALIDATED.
- [ ] Same symbol across exchanges disambiguated in every view.
- [ ] Navigation stable on small Android screens and accessibility text scaling.
- [ ] Widget/golden tests mapped to FR-016.

See [API_CONTRACT](docs/API_CONTRACT.md) for view models and [SCORING_RANKING](docs/SCORING_RANKING.md) for semantic labels.
