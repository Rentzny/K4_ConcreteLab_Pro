# K4 ConcreteLab Pro

**Aplikasi web dan mesin analisis kuat tekan beton yang dibuat dari proyek PjBL K4 Teknik Sipil.**

Aplikasi ini melanjutkan notebook `Proyek_K4_Beton_FINAL_PDF_Otomatis.ipynb`. Rumus dasar, konsep fungsi/class, dan struktur CSV tetap kompatibel. Versi ini **tidak mengganti** notebook lama; gunakan sebagai pengembangan dan demonstrasi aplikasi.

> **Penting:** Data contoh **ilustratif**, bukan data laboratorium nyata. Kriteria numerik SNI pada aplikasi adalah **simulasi pendidikan dengan asumsi tertentu**, bukan bukti pemenuhan seluruh standar atau sertifikat penerimaan beton. Penggunaan di laboratorium nyata harus diverifikasi oleh personel berwenang.

## Fitur yang sudah dibuat

- **Web dashboard** menggunakan Streamlit; dapat dibuka dari browser di laptop/HP jaringan lokal jika konfigurasi firewall mengizinkan.
- **Upload CSV** dan **editor tabel** untuk mengubah beban, diameter, ID uji, dan menambah/menghapus baris.
- **Validasi kuat:** kolom wajib, ID unik, nilai positif/terhingga, pasangan uji, umur, diameter, dan urutan pengujian opsional.
- **Core Python terpisah**: `BendaUji`, fungsi perhitungan, statistik, koefisien variasi (CV), rekap pasangan, outlier ±2SD.
- **Evaluasi simulasi** jendela tiga hasil uji berurutan, dua ambang numerik, dan status *tidak dapat dievaluasi* bila data tak memenuhi asumsi.
- **Simulasi sensitivitas target** saat mutu rencana diubah.
- **Empat grafik** (histogram, rata-rata dan SD, boxplot, tren) serta grafik interaktif Plotly.
- **PDF A4 otomatis** dari data CSV terkini; berisi statistik, dua grafik, tabel hasil uji, evaluasi, dan catatan keterbatasan.
- **Paket ZIP hasil lengkap**: 6 CSV (termasuk input dan jendela tiga uji), 4 PNG, PDF, metadata JSON dengan hash SHA-256 sumber.
- **Mode terminal**: jalankan `cli.py` untuk ekspor otomatis tanpa browser.
- **Tes otomatis**: data contoh, validasi, kasus error, target fleksibel, ekspor PDF/ZIP, perubahan data CSV.

## Cara menjalankan di Windows — paling mudah

1. Ekstrak file ZIP proyek ke folder, contoh `D:\KULIAH\SEMESTER 3\Bahasa Pemrograman\PJBL\K4_ConcreteLab_Pro`.
2. Klik dua kali **`run_windows.bat`** (Windows harus memiliki Python yang bisa dipanggil; skrip akan mencari Python 3.13 terlebih dahulu).
3. Saat pertama kali dijalankan, skrip membuat `.venv` dan memasang pustaka dari `requirements.txt` (**memerlukan internet**).
4. Buka **`http://localhost:8501`** di browser jika belum terbuka otomatis.
5. Tanpa unggahan apa pun, aplikasi langsung memakai data contoh 18 silinder. Unggah `kuat_tekan_beton.csv` milikmu lewat sidebar untuk memakai data lain.
6. Sesuaikan f'c di sidebar. Lihat tab Ringkasan, Data & Statistik, Evaluasi, Visualisasi, atau Unduh Laporan.
7. Unduh **PDF** atau **paket ZIP**. Mengedit tabel di browser **tidak menimpa CSV asli**.

### Cara lewat Terminal VS Code

Di Terminal VS Code, pastikan kamu berada pada folder `K4_ConcreteLab_Pro`, lalu jalankan:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternatif jika `py -3.13` tidak ditemukan, gunakan `python -m venv .venv` dengan Python minimal 3.11.

**Catatan VS Code:** aplikasi Streamlit dijalankan dari **Terminal**, bukan dengan tombol `Run All` notebook. Notebook lama tetap memakai `Restart + Run All` seperti biasa.

## Cara ekspor otomatis tanpa web (CLI)

```powershell
.\.venv\Scripts\python.exe cli.py --input data\contoh_18_silinder.csv --target 30 --output hasil
```

Untuk data pribadi:

```powershell
.\.venv\Scripts\python.exe cli.py --input kuat_tekan_beton.csv --target 32 --output hasil
```

Ini membuat PDF, empat grafik, CSV statistik dan evaluasi, serta paket ZIP di folder `hasil`.

## Format CSV wajib

| Kolom | Satuan | Contoh | Keterangan |
|---|---|---|---|
| `id_benda_uji` | teks | U01 | ID unik per silinder |
| `campuran` | teks | A | Penanda tipe campuran |
| `umur_hari` | hari | 28 | Wajib positif |
| `diameter_mm` | mm | 150 | Wajib positif |
| `beban_maksimum_kN` | kN | 500 | Wajib positif |
| `id_pengujian` | teks | A01 | ID hasil uji yang menggabungkan 2 silinder |
| `urutan_uji` | bilangan bulat | 1 | **Opsional** tetapi disarankan; satu nilai sama untuk pasangan silinder dalam satu hasil uji; urutan penilaian 3 hasil uji |

Contoh: `data/contoh_18_silinder.csv`. Semua angka menggunakan **titik desimal** dalam CSV. Kolom opsional `urutan_uji` mendukung pengambilan sampel berurutan yang lebih jelas daripada pengurutan berdasarkan ID.

Jika data diunggah tidak memenuhi asumsi 2 silinder per pengujian, diameter 150 mm, dan umur 28 hari, program **tetap menghitung kuat tekan**, tetapi status simulasi penerimaan campuran terkait menjadi **Tidak dapat dievaluasi**.

## Rumus yang digunakan

- Luas penampang: `A_mm2 = π × diameter_mm² / 4`.
- Kuat tekan: `fc_MPa = 1000 × beban_maksimum_kN / A_mm2`.
- Rata-rata, simpangan baku sampel, median, minimum, maksimum, dan `CV = simpangan_baku / rata_rata × 100%`.
- Outlier **indikatif**, bukan keputusan menghapus data: `|fc - mean_campuran| > 2 × SD` jika `n ≥ 5` per campuran.
- Simulasi kriteria numerik untuk `f'c <= 35 MPa`: semua rata-rata bergerak 3 hasil uji >= f'c; tidak ada hasil uji < f'c − 3,5 MPa. Jika `f'c > 35 MPa`, batas individual menjadi 0,9 f'c. **Sumber logika:** kriteria numerik yang digunakan pada notebook K4; perlu verifikasi standar dan penerapan lapangan.

**Penting membedakan:** tabel per *silinder* untuk distribusi/statistik dan tabel per *hasil uji* untuk simulasi penilaian; keduanya tidak sama.

## Pengujian program

Instal dependensi dev (`requirements-dev.txt`) lalu:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tes dibuat pada `tests/test_engine.py`. Semua tes inti lulus pada lingkungan pembuatan paket. Antarmuka web membutuhkan pengujian tambahan pada Windows setelah memasang Streamlit (komponen ini tidak dapat dijalankan pada lingkungan pembuat karena Streamlit tidak tersedia).

## Berbagi aplikasi online

- Gunakan GitHub repository untuk kode aplikasi (jangan unggah berkas CSV nyata yang mengandung informasi rahasia).
- Pada Streamlit Community Cloud, pilih repo tersebut dan entrypoint **`app.py`**; `requirements.txt` di root mengatur dependensi.
- Untuk tugas kelas, lebih aman menjalankan di localhost terlebih dahulu. Cloud membutuhkan internet; data yang diunggah diproses di server hosting.
- Colab tidak diperlukan untuk dashboard Streamlit. Jika ingin memakai Colab untuk analisis, gunakan `cli.py` atau notebook lama dan pastikan lokasi CSV di Drive sudah benar.

Dokumentasi resmi: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Struktur folder

```
K4_ConcreteLab_Pro/
├── app.py                      # UI web
├── cli.py                      # Mode terminal
├── concretelab/
│   ├── engine.py               # Perhitungan dan validasi
│   ├── plots.py                # Gambar statistik
│   └── reporting.py            # PDF dan ZIP
├── data/
│   ├── contoh_18_silinder.csv
│   └── template_kosong.csv
├── tests/test_engine.py
├── contoh_output/
│   └── Laporan_Otomatis_K4_Beton.pdf
├── requirements.txt
├── requirements-dev.txt
├── run_windows.bat
└── README.md
```

## Fitur yang *belum* disertakan (tahap produksi)

- Integrasi otomatis ke mesin UTM/CTM, IoT, dan alat laboratorium.
- Multiuser/login aman, database permanen, tanda tangan digital, audit trail berbasis server.
- QR-code verifikasi laporan dan sinkronisasi hasil beberapa proyek secara real-time.
- Model AI prediksi kuat tekan: membutuhkan data laboratorium nyata dengan variasi komposisi, umur, dan kontrol kualitas; 18 data ilustratif **tidak mencukupi**.
- Sertifikasi laboratorium atau jaminan kesesuaian seluruh klausul standar.

## Kredit penggunaan AI dan sumber

Pengembangan aplikasi dan dokumentasi dibantu ChatGPT/OpenAI. Siswa/kelompok tetap wajib memahami rumus, menguji aplikasi, memverifikasi data dan metode, serta menyatakan bantuan AI sesuai aturan integritas akademik dosen.
