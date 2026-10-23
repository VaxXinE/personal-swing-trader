# AGENTS.md — Instruksi untuk Coding Agent

Repo ini adalah aplikasi **private personal swing-trading decision-support**, bukan bot order dan bukan sistem sinyal yang menjamin profit. Baca [README](README.md), [PRD](PRD.md), [DECISIONS](docs/DECISIONS.md), [SECURITY](docs/SECURITY.md) dan spesifikasi domain terkait **sebelum** mengubah implementasi.

## Mandatory workflow per task

1. Sebutkan **requirement ID** dan acceptance test yang akan dipenuhi. Periksa dependensi pada [TASKS](docs/TASKS.md).
2. Implementasikan vertical slice sekecil mungkin: domain/pure function → tests → repository/provider → API → Flutter UI.
3. Jalankan formatter, static analysis, unit, contract dan integration tests relevan. Jangan klaim lulus bila belum dijalankan.
4. Tulis migration jika schema berubah; update contoh payload dan [CHANGELOG](CHANGELOG.md).
5. Tampilkan perubahan file, alasan trade-off, coverage tes, risiko, dan pekerjaan berikutnya saat handoff.

## Dilarang

- Hardcode token/secret, membuka backend tanpa auth ke jaringan publik, menaruh API key vendor di Flutter.
- Menggunakan Python `eval`, `exec`, dynamic SQL string dari input atau kode hasil LLM.
- Melabeli quote delayed/stale sebagai live; menerka bid/ask, financial ratio, atau probabilitas model.
- Melatih/test dengan data masa depan, membuat candle unfinished sebagai sinyal EOD.
- Mengubah old signal snapshots saat model berubah.
- Mengaktifkan real trades, short, futures, leverage, withdrawal permissions.
- Menambahkan AI-generated prediction percentage tanpa validation gate.
- Menyalin source proyek referensi tanpa memeriksa lisensi.

## Design conventions

- Python typed (`mypy` atau `pyright`), `ruff`, `pytest`, Pydantic schemas. Flutter `dart format`, `flutter analyze`, widget tests.
- Semua waktu canonical UTC, display sesuai zona bursa/Jakarta; Decimal untuk uang/kuantitas order.
- Domain modules **tidak** import FastAPI/SQLite/provider. Dependency inversion melalui ports/adapters.
- Symbol dengan canonical `instrument_id`; market status as-of, no look-ahead.
- Missing data `UNKNOWN`, never zero; preserve raw + normalized source and provenance.
- Score ≠ probability; risk gate may reject high score.
- Default networking bind `127.0.0.1`; private access melalui VPN/identity-aware proxy. Logging redact credentials.

## AI-assisted changes

Prompt ke agent harus menyebut scope, file spesifikasi, acceptance criteria, dan larangan scope creep. **Jangan auto-implement seluruh roadmap dalam satu PR.** Minta satu milestone atau satu task ID per putaran agar audit dan debugging lebih mudah.

## Handoff template

```
Task ID / FR IDs:
Files changed:
Behavior implemented:
Tests run + results:
Data assumptions / limitations:
Security + look-ahead checks:
Migration / docs updated:
Next task:
```
