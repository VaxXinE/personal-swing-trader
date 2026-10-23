# GOAL — Visi dan Prinsip Produk

**Status:** LOCKED untuk identitas produk · **Owner:** developer/user tunggal · **Date:** 2026-10-23

## North Star

> Membantu satu trader menemukan peluang swing long-only di US Stocks, IDX, dan crypto spot secara luas, **memahami alasannya**, mengetahui batas risiko, dan mengaudit hasil analisis terhadap kondisi pasar yang nyata.

Produk ini adalah **decision-support**, bukan pemberi sinyal profit pasti dan bukan bot transaksi. Optimasi utama: **keputusan lebih terinformasi dengan data transparan**, bukan volume notifikasi atau jumlah indikator.

## Pilihan produk yang sudah dikunci

- Personal: **satu developer sekaligus satu pengguna**, privat, tidak dipublikasikan ke publik.
- Mobile pertama: **Flutter Android**; dukungan iOS opsional nanti.
- Tiga pasar: saham AS, saham BEI, crypto **spot**; tidak ada margin/short/leverage atau auto-order.
- **Swing trading** daily-first dengan bantuan intraday; saham target studi 3–20 sesi bursa, crypto 3–20 hari kalender (parameter dipilih dan dicatat per strategi).
- **Broad Discovery + Liquid Universe**: banyak kandidat dapat dieksplorasi, tetapi Trade Ready lewat filter ketat.
- Dua strategi awal: **Trend Pullback** dan **Breakout**; reversal ditunda.
- Ranking **per pasar dan strategi**; skor setup bukan probabilitas profit.
- Perhitungan kuantitatif deterministik; LLM hanya alat bantu penjelasan terikat sumber, jika kelak digunakan.

## Outcomes yang ingin dicapai

1. **Coverage yang jujur:** setiap aset tercakup/ditolak dengan alasan dan status data.
2. **Discoverability:** pengguna dapat menyaring, menyimpan, membandingkan kandidat tanpa data yang saling bertentangan.
3. **Explainability:** setiap setup punya feature values, entry/stop/target, R:R, alasan mendukung/menolak, versi aturan.
4. **Risk discipline:** sistem menolak sinyal bila data atau eksekusi tidak layak.
5. **Measurability:** prediksi/sinyal historis tidak ditimpa; hasil dibandingkan dengan outcome dan benchmark.
6. **Reliability:** kegagalan provider/stream menghasilkan status `STALE/UNKNOWN`, **bukan** nilai yang dikarang.

## Metrik penerimaan engineering (target, bukan hasil yang sudah dicapai)

| Metrik | Target awal | Cara ukur |
|---|---|---|
| Traceability | 100% sinyal disimpan bersama rule/data/model version | audit DB |
| Source attribution | 100% informasi harga/feature yang dipakai punya provider dan timestamp | automated contract test |
| Data integrity | 0 candle terduplikasi yang lolos materialisasi; OHLC invariant terpenuhi | ingestion checks |
| Duplicate alert | 0 push ganda untuk event key identik | idempotency tests |
| Determinism | Identik untuk data snapshot, code/config version dan seed yang sama | golden tests |
| Mobile usability | tugas scan → detail → watchlist dapat diselesaikan tanpa layar debug | manual usability checklist |
| Offline/stale | semua layar terkait menampilkan status jelas, tidak klaim live | UI tests |
| Forecast trust | **tidak menampilkan confidence numerik** sampai validasi lulus | feature gate tests |

**Tidak** menetapkan win rate, ROI, atau annualized return target sebelum data backtest tersedia. Mengoptimalkan untuk win rate tertentu tanpa memeriksa expectancy dan drawdown bisa menyesatkan.

## Anti-goals

Aplikasi sosial; jual sinyal; onboarding multi-user; subscription; auto trading; klaim prediksi 90% akurat; scraping agresif/pembobolan pembatasan; data palsu dengan badge real-time; 100 indikator tanpa tujuan.

## Prinsip keputusan

1. Data quality di atas visual polish; keamanan di atas convenience berisiko.
2. Simpel sampai ada alasan terukur untuk kompleksitas.
3. Risk/eligibility **terpisah** dari scoring.
4. Tidak ada sinyal karena hanya 'AI bilang begitu'.
5. Aplikasi berani menjawab **NO TRADE**, **WAIT**, atau **UNKNOWN**.

## Tahap akhir visi

Private mobile terminal dengan screener, analytical drill-down, price-scenario yang tervalidasi, backtest/paper journal, alert, dan observability pribadi. Pekerjaan tahap implementasi ada di [ROADMAP](docs/ROADMAP.md).
