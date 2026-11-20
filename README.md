# K4 ConcreteLab Pro v4.0 — Professional Visual Analytics & Reporting

Aplikasi analisis kuat tekan beton berbasis **Streamlit**. Website mempunyai menu **Beranda | Service | About**, tampilan minimalis, serta area unggah CSV besar di tengah halaman Service. Sebelum CSV valid diunggah, **tidak ada grafik, tabel analisis, atau PDF** yang ditampilkan.

## Peningkatan v4.0 (berdasarkan versi 3.1)

**Service → Executive Summary** kini menampilkan KPI dinamis, rerata seluruh silinder, persentase silinder mencapai target, perbandingan rerata ± SD, status simulasi per campuran, dan interpretasi teknis yang konservatif. Tidak ada angka hasil 18 silinder yang dikunci dalam kode.

**Service → Visual Analytics** sekarang memakai enam visual Plotly dengan palet campuran yang konsisten: histogram, boxplot, tren hasil uji, perbandingan rerata ± simpangan baku, ECDF, dan grafik pencapaian target. Grafik dapat difilter per campuran tanpa mengubah PDF utama. Navigasi Beranda–Service–About, homepage v3.1 dan uploader CSV interaktif tidak berubah.

**Laporan PDF v4.0** dari CSV terkini memuat ringkasan eksekutif, tabel kinerja, 4 grafik cetak lebih rapi, hasil simulasi, semua baris benda uji, dan QR laporan. Data contoh 18 silinder menghasilkan **6 halaman A4**; jumlah halaman dapat berubah untuk CSV lain. ZIP ekspor menambahkan `hasil/ringkasan_kinerja_profesional.csv` dan `hasil/Ringkasan_Eksekutif.txt`.

**Status keamanan dan ilmiah:** "silinder mencapai target" tidak setara dengan "campuran memenuhi simulasi SNI". Simulasi bukan sertifikat mutu laboratorium; QR/checksum bukan tanda tangan digital. Riwayat SQLite hanya opsional di komputer sendiri, tidak aktif pada hosting publik.

### Meng-update GitHub dari versi 3.1

1. Cadangkan folder repository lokal. Unduh `K4_ConcreteLab_Pro_v4_0_UPDATE_GITHUB.zip` dan ekstrak terpisah.
2. Salin **isi** ZIP ke akar repository lokal, sejajar dengan `app.py`, lalu pilih **Replace** jika diminta. Jangan menghapus `.git` dan `.venv`.
3. GitHub Desktop → **Changes**: periksa berkas baru/berubah → summary `Upgrade Professional Visual Analytics v4.0` → **Commit to main** → **Push origin**.
4. Pada website Streamlit setelah deploy, buka Service: tanpa CSV harus tetap kosong; setelah upload pilih tab Executive Summary dan Visual Analytics.
5. Jalankan tes lokal dengan `python -m pytest -q tests` jika dependensi pengembangan tersedia. GitHub Actions akan menguji pada push dan pull request.

### Data contoh dan PDF contoh

Berkas `data/contoh_18_silinder.csv` untuk pembelajaran saja. PDF contoh berada di `contoh_output/Laporan_Otomatis_K4_Beton.pdf`. Data CSV asli pengguna tidak disimpan permanen di server secara otomatis.

## Fitur yang dipertahankan dari v2.2

- Validasi CSV dengan rincian baris, editor data, deteksi duplikasi/angka tidak sah.
- Analisis kuat tekan silinder, pengelompokan dua silinder per pengujian, statistik dan evaluasi simulasi SNI dengan pemeriksaan asumsi.
- Statistik lanjutan (Q1/Q3, persentil, IQR, CV, bootstrap ilustratif), grafik interaktif, sensitivitas target dan skenario beban.
- Bandingkan dua dataset CSV, unduh PDF, CSV, grafik dan ZIP hasil.

## Fitur baru v3.0

1. **Service → Proyek & Riwayat → Buat arsip proyek** menghasilkan berkas `K4_...k4proj.zip` berisi CSV tervalidasi, metadata nama proyek, penanggung jawab, target, waktu, ID versi, checksum SHA-256, dan salinan PDF.
2. **Service → Buka arsip proyek sebelumnya** memulihkan CSV beserta parameter proyek ke sesi browser. Pemeriksaan otomatis menolak ZIP rusak, struktur mencurigakan, hash tidak cocok, data tidak sah, atau ringkasan perhitungan yang tidak sesuai. ZIP tidak diekstrak ke server.
3. **PDF mulai v3.0** mendapatkan satu halaman identitas laporan: ID deterministik berbasis CSV ternormalisasi/target/nama proyek, QR offline berisi ID dan SHA-256 untuk membantu pengecekan. PDF versi 3.0 memiliki 5 halaman; versi 4.0 memiliki 6 halaman untuk contoh 18 silinder.
4. **Riwayat SQLite lokal** (opsional, nonaktif secara default): menyimpan beberapa arsip analisis dan memulihkan kembali di instalasi pribadi. Database berada pada folder `_local_data/` yang masuk `.gitignore`.

**QR/SHA-256 bukan tanda tangan digital dan tidak membuktikan keaslian sertifikat atau identitas laboratorium.** Pemeriksaan hash hanya mendeteksi perubahan dibandingkan metadata dalam arsip; pihak ketiga tetap bisa membuat ulang arsip beserta checksum. Data ilustratif tidak membuktikan mutu konstruksi nyata.

## Jalankan di Windows

1. Simpan folder aplikasi di komputer dan buka menggunakan VS Code.
2. Jalankan `run_windows_PERBAIKAN.bat` untuk membuat lingkungan Python (via uv bila tersedia) dan menjalankan Streamlit.
3. Browser membuka `http://localhost:8501`.
4. Pilih **Service**, unggah CSV dan coba tab **Proyek & Riwayat**.
5. Unduh berkas `.k4proj.zip` setiap kali ingin menyimpan satu versi kerja. Arsip tersebut dapat diimpor lagi dari halaman Service.

Alternatif terminal (setelah venv dan requirements terpasang):

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Mengaktifkan riwayat SQLite (HANYA pada komputer pribadi)

Mode ini **tidak memiliki login, otorisasi, ataupun isolasi data antar pengguna**. Jangan mengaktifkannya untuk aplikasi Streamlit Cloud publik atau komputer bersama.

```powershell
$env:K4_ENABLE_LOCAL_HISTORY = "1"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Arsip tersimpan di `_local_data/history.sqlite3`. Jangan mengunggah folder ini ke GitHub atau membagikannya; pastikan memiliki backup. Riwayat dari browser di Streamlit Community Cloud tetap tidak permanen; pengguna harus **mengunduh ZIP proyek**.

## Deploy ulang dari repository GitHub

- Unduh `K4_ConcreteLab_Pro_v4_0_UPDATE_GITHUB.zip`.
- Ekstrak, lalu **salin isinya** ke root repository `K4_ConcreteLab_Pro` di laptop (satu level dengan `app.py`). Pilih Replace bila diminta. Jangan menimpa atau menghapus folder `.git` maupun `.venv`.
- Di GitHub Desktop, periksa Changes, isi summary, klik `Commit to main`, lalu `Push origin`.
- Di Streamlit Community Cloud, periksa status deployment dan pastikan halaman Service berfungsi. `requirements.txt` tetap sama; tidak perlu pustaka baru.
- **Jangan unggah** token/API key, data laboratorium rahasia, SQLite, atau `.env` ke repository publik.

## Verifikasi dan batasan

Tes unit/mesin analisis:

```powershell
python -m pytest -q tests
```

Versi ini belum menyediakan **akun multiuser, otentikasi, database permanen pada cloud, tanda tangan digital, atau verifikasi QR melalui server publik**. Untuk sistem laboratorium produksi diperlukan backend aman, backup, audit, dan verifikasi standar pengujian.
