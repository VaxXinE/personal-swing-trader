# MULAI DI SINI — Setup aplikasi tanpa utak-atik source

> Proyek ini **alpha aplikasi riset trading pribadi**, bukan bot yang bisa melakukan transaksi. Mode `demo` berisi harga **sintetis**; mode `live` membaca provider publik secara *best effort*, dan bukan real-time bursa terverifikasi. Prediksi probabilistik dan sinyal trade-ready belum diaktifkan.

## 1. Menjalankan aplikasi sekarang (browser di laptop)

Persyaratan satu kali: **Python 3.11+** dan akses internet untuk mengunduh dependensi saat setup. Unzip repository, masuk folder `personal-swing-intelligence`, lalu:

- **Windows:** klik dua kali `scripts/start.bat` (atau lewat CMD).
- **macOS/Linux:** `bash scripts/start.sh`.

Setelah server berhasil jalan, buka **http://127.0.0.1:8000/**. Tidak perlu API key dan tidak perlu Flutter untuk mencoba seluruh dashboard browser.

Jika bermasalah, jalankan `python scripts/doctor.py`, lalu lihat terminal launcher. Pertama kali menjalankan akan memasang paket Python di `.venv/`; run berikutnya dapat memanfaatkan hasil instalasi itu. Tutup terminal atau tekan `Ctrl+C` untuk menghentikan server.

## 2. Mencoba data asli (riset EOD, bukan realtime)

Setelah mode demo berfungsi, stop server. Dari root repository:

- Windows: `scripts\start.bat --live`
- macOS/Linux: `bash scripts/start.sh --live`

Mode live mengambil saham AS/BEI lewat `yfinance` dan crypto melalui endpoint publik Binance. Sumber ini bisa diblokir, *rate-limited*, berubah atau mengembalikan data tidak lengkap. **Jika gagal, sistem akan melaporkan error, bukan memalsukan harga.** Beri izin penggunaan dan periksa persyaratan masing-masing sumber. `config/universe.json` berisi ticker yang hendak discan.

## 2b. Perluas daftar aset (Dynamic Liquid Universe V2)

Setelah `--live` berjalan, buka terminal baru di folder proyek, lalu:

```bash
source .venv/bin/activate
python scripts/sync_universe.py --markets US CRYPTO
```

Jika status sukses, kembali ke web aplikasi di port 8001 dan klik **Run Scan**. Lihat **Data Health** untuk jumlah aset yang ditemukan, dipilih, dianalisis, dikecualikan, atau gagal. Default discovery menambahkan maksimum 24 kandidat AS dan 18 pair crypto (beberapa bisa duplikat baseline).

IDX **belum dapat auto-sync dari bursa**, tapi **sekarang menerima XLSX langsung**. Unduh file Excel `Daftar Saham...xlsx` dari situs resmi BEI; pastikan ada kolom `Kode`, `Nama Perusahaan`, dan bila tersedia `Papan Pencatatan`. Jalankan:

```bash
python scripts/sync_universe.py --markets IDX --idx-file "$HOME/Downloads/Daftar Saham.xlsx" --idx-limit 35
```

Ganti nama/path file Excel sesuai hasil unduhan. Untuk melihat nama file, jalankan `ls -1 ~/Downloads/*.xlsx`. Alternatif alias: `--idx-xlsx`. Import CSV lama juga tetap bisa (`--idx-csv`). Bila workbook punya header di baris lain atau beberapa worksheet, parser akan memilih sheet dengan daftar ticker terbanyak. File sumber tidak diubah. Jika format tidak dikenali, sync akan gagal **tanpa menghapus hasil sinkronisasi IDX sebelumnya**. Setelah berhasil, kembali ke dashboard LIVE dan klik **Run Scan**. Default 35 kandidat tambahan IDX (maksimum 75 per sync); ini bukan impor semua saham sebagai kandidat sekaligus.

Perhatikan: daftar US yang baru ditemukan belum diperingkat berdasarkan likuiditas; crypto pra-seleksi menggunakan volume 24 jam, sedangkan filter historis memakai ADV20. **Keduanya tidak menjamin bisa dieksekusi.** Bila provider gagal, skrip mengembalikan error dan tidak mengganti daftar lama dengan data palsu. Baca `docs/DYNAMIC_UNIVERSE_V2.md`.

## 3. APK Android pribadi

**APK belum disertakan** karena Flutter dan Android toolchain belum tersedia pada environment pembuatan paket. Dua cara membuild:

1. **Tanpa install Flutter lokal:** buat repo GitHub privat dari folder ini, pilih tab **Actions → Verify API and build private Android APK → Run workflow**. Jika workflow berhasil, unduh artifact `swing-intelligence-private-android-apk` dan ekstrak `app-release.apk`.
2. **Dengan Flutter SDK:** jalankan `bash scripts/flutter_setup.sh` (atau `scripts\flutter_setup.bat`), lalu `cd apps/mobile && flutter build apk --release`. Build melakukan pemeriksaan analyzer pada setup shell; source Android scaffold akan dibuat otomatis oleh `flutter create`.

**Penting:** workflow GitHub bersifat belum dijalankan dalam environment paket ini. Jika gagal pada pipeline build, ikuti log Actions dan perbaiki sebelum menginstal APK. APK private menggunakan signing default Flutter template; build ulang dari environment lain bisa membutuhkan uninstall dan pemasangan ulang aplikasi. Ini **bukan** saluran update produksi yang stabil.

### Akses data dari emulator vs HP fisik

- Android emulator → backend di laptop: set URL `http://10.0.2.2:8000`; tersedia untuk **debug build**.
- Android fisik / APK release → gunakan URL **HTTPS lewat akses privat** (mis. Tailscale Serve atau reverse proxy TLS di VPN); masukkan Bearer token di halaman Settings aplikasi. Backend bind ke `127.0.0.1` secara default. Jangan membuka API langsung ke internet publik.
- Untuk server di interface non-loopback, atur `SWING_HOST=0.0.0.0` dan `SWING_API_TOKEN` minimal 32 karakter acak di `.env`, serta firewall yang hanya mengizinkan VPN. Lihat `docs/SECURITY.md`.

## 4. Mode seperti aplikasi pada HP via browser

`web/` memiliki PWA manifest/icon, bisa dipasang melalui **Add to Home Screen/Install app** di browser Android yang mendukungnya. Perangkat lain membutuhkan origin HTTPS yang tepercaya (contoh: proxy TLS internal/Tailscale Serve), bukan alamat `http://192.168.x.x`. PWA bukan APK Flutter dan tidak melakukan riset offline; hanya aset tampilan yang bisa di-cache. **Data, watchlist dan jurnal tersimpan di backend SQLite**, bukan HP.

## 5. Peta fitur yang benar-benar ada

| Ada pada alpha | Belum ada / belum divalidasi |
|---|---|
| Scanner dua strategi, tiga pasar, likuiditas, scoring transparan | Probabilitas harga atau machine learning tervalidasi |
| Builder rule AND/OR/NOT (API lengkap; UI builder dasar) | Push alerts, auto trading, real-time exchange feeds |
| Watchlist/journal paper, position sizing penelitian | APK teruji emulator/fisik, e2e Android |
| Demo offline + adapter EOD eksternal opsional | Universe listing penuh otomatis dan historis bias-free |

Untuk status yang lebih rinci, baca [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), lalu lanjut implementasi dari [docs/TASKS.md](docs/TASKS.md). Jangan membuat keputusan transaksi uang sungguhan hanya berdasarkan hasil alpha ini.
