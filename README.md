# K4 ConcreteLab Pro v3.0 — Project Archive & Traceability

Aplikasi analisis kuat tekan beton berbasis **Streamlit**. Website mempunyai menu **Beranda | Service | About**, tampilan minimalis, serta area unggah CSV besar di tengah halaman Service. Sebelum CSV valid diunggah, **tidak ada grafik, tabel analisis, atau PDF** yang ditampilkan.

## Fitur yang dipertahankan dari v2.2

- Validasi CSV dengan rincian baris, editor data, deteksi duplikasi/angka tidak sah.
- Analisis kuat tekan silinder, pengelompokan dua silinder per pengujian, statistik dan evaluasi simulasi SNI dengan pemeriksaan asumsi.
- Statistik lanjutan (Q1/Q3, persentil, IQR, CV, bootstrap ilustratif), grafik interaktif, sensitivitas target dan skenario beban.
- Bandingkan dua dataset CSV, unduh PDF, CSV, grafik dan ZIP hasil.

## Fitur baru v3.0

1. **Service → Proyek & Riwayat → Buat arsip proyek** menghasilkan berkas `K4_...k4proj.zip` berisi CSV tervalidasi, metadata nama proyek, penanggung jawab, target, waktu, ID versi, checksum SHA-256, dan salinan PDF.
2. **Service → Buka arsip proyek sebelumnya** memulihkan CSV beserta parameter proyek ke sesi browser. Pemeriksaan otomatis menolak ZIP rusak, struktur mencurigakan, hash tidak cocok, data tidak sah, atau ringkasan perhitungan yang tidak sesuai. ZIP tidak diekstrak ke server.
3. **PDF v3.0** mendapatkan satu halaman identitas laporan: ID deterministik berbasis CSV ternormalisasi/target/nama proyek, QR offline berisi ID dan SHA-256 untuk membantu pengecekan. PDF contoh 18 silinder menjadi 5 halaman (sebelumnya 4).
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

- Unduh `K4_ConcreteLab_Pro_v3_0_UPDATE_GITHUB.zip`.
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
