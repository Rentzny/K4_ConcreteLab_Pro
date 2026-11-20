# K4 ConcreteLab Pro v2.2 — Minimal Engineering + Analitik Lanjutan

Aplikasi Streamlit pengolahan hasil uji kuat tekan beton. Fitur analisis v2.0 dipertahankan, dengan navigasi **Beranda | Service | About**, homepage minimalis tanpa animasi, serta statistik lanjutan, grafik interaktif dan simulasi target mutu.

## Cara menjalankan

1. Jalankan `run_windows_PERBAIKAN.bat` (Windows) atau aktifkan Python lalu jalankan `streamlit run app.py`.
2. Kunjungi menu **Service** dan unggah CSV (contoh tersedia di halaman tersebut).
3. Baca audit input, edit data bila perlu, lihat statistik dan grafik, lalu unduh PDF/ZIP.
4. Menu **Beranda** tidak menampilkan hasil analisis, dan tidak ada CSV yang dimuat secara otomatis.

## Navigasi dan mobile

- Desktop: navigasi horizontal dari `st.navigation(position="top")`.
- Mobile: navigasi bawaan Streamlit beradaptasi pada layar kecil; perilaku persis menu perlu diuji di browser/HP setelah deploy.
- Data upload dan hasil edit disalin ke session state untuk bertahan saat berpindah halaman **dalam sesi yang sama**, bukan database permanen.
- Homepage sederhana: latar terang, warna netral, tiga kartu fitur, tanpa animasi atau video latar.

## Kebutuhan

`requirements.txt` memerlukan Streamlit versi **1.46+** untuk navigasi atas, ditambah pandas, NumPy, Matplotlib, Plotly dan ReportLab.

## File penting

- `app.py` — router, konfigurasi, gaya global
- `app_pages/home.py` — Beranda
- `app_pages/service.py` — aplikasi analisis dan ekspor v2.0
- `app_pages/about.py` — informasi proyek
- `concretelab/` — mesin perhitungan, quality, skenario, grafik, PDF
- `tests/` — tes otomatis yang bisa dijalankan dengan `pytest -q`
- `data/` — CSV contoh dan template

## Deployment GitHub → Streamlit Cloud

Timpa file lama dengan paket update v2.1 **di root repository** (jangan membuat folder baru bersarang). Lakukan `Commit to main` dan `Push origin` dari GitHub Desktop. Streamlit menggunakan `app.py` sebagai entrypoint. Periksa navigasi desktop dan HP setelah deploy.

## Batasan ilmiah

Data contoh bersifat ilustratif. Evaluasi mutu adalah simulasi numerik terbatas, **bukan sertifikat pengujian atau keputusan penerimaan beton nyata**. Tidak ada penyimpanan permanen untuk CSV yang diunggah dan jangan mengunggah data rahasia ke layanan publik tanpa perlindungan yang sesuai.


## Upgrade v2.2: statistik lanjutan, grafik & simulasi target

- **Service → Data & statistik:** P10, Q1, median, Q3, P90, IQR, SD, CV,
  serta interval bootstrap 95% rerata (hanya jika n ≥ 5). Pilih unit per
  silinder atau per hasil uji. Grafik rerata + rentang bootstrap interaktif.
- **Service → Evaluasi mutu:** rentang target f'c dapat digeser, kurva
  persentase silinder mencapai target per campuran dan jumlah campuran
  memenuhi **simulasi** tiga hasil uji ditampilkan terpisah. Angka “tidak
  dapat dievaluasi” tidak dianggap “gagal”.
- **Service → Visualisasi:** distribusi kumulatif interaktif (ECDF) dengan
  filter campuran dan garis target mutu.
- **Unduh laporan:** paket ZIP menyertakan CSV statistik lanjutan dan
  sensitivitas target. PDF tetap berdasarkan target utama dari sidebar.
- **Kebutuhan:** Tidak ada library tambahan; menggunakan NumPy, pandas,
  dan Plotly yang sudah tercantum di `requirements.txt`.

Uji mesin perhitungan dengan `python -m pytest -q tests`.
Tampilan UI Streamlit perlu diperiksa langsung setelah deploy.

**Batasan:** Angka CI bootstrap menggambarkan variasi rerata dalam
pengambilan ulang sampel secara statistik. Pada data kecil atau tidak
representatif, interpretasinya terbatas dan tidak memenuhi persyaratan
penerimaan mutu beton lapangan. Evaluasi mutu tetap simulasi pembelajaran.
