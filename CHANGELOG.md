## v3.1 — Calm Engineering Homepage
- Beranda diperbarui dengan hero editorial minimalis, ilustrasi skematik beton statis, tiga kartu fitur, dan tombol nyata menuju Service/About.
- Tampilan responsif untuk desktop dan HP. Tidak ada animasi, auto-play, data atau grafik contoh di halaman Beranda.
- Gaya CSS di-scope hanya untuk beranda; modul Service, About, perhitungan, ekspor, arsip, dan QR v3.0 tidak diubah.
- Skema silinder dan rumus pada beranda merupakan ilustrasi konseptual, bukan data pengujian.

# Changelog

## v3.0 — Portable Project Archive & Report Traceability
- Arsip `.k4proj.zip` berisi CSV, metadata, checksum, dan PDF; dapat diimpor untuk mengembalikan analisis.
- SHA-256 file diverifikasi, data dihitung ulang, ZIP tak valid ditolak sebelum diproses.
- QR offline + ID laporan pada PDF, tanpa klaim tanda tangan digital atau validasi laboratorium.
- Penyimpanan riwayat SQLite lokal opt-in; nonaktif secara default untuk hosting publik.
- Service mendapat tab **Proyek & Riwayat**; Beranda dan About tetap minimalis.
- Semua fitur v2.2 tetap dipertahankan.
- Memperbaiki error Plotly ketika `visible` menerima `numpy.bool` pada grafik interval bootstrap.

# Changelog

## v2.1 — Minimal Engineering
- Menu **Produk** diganti menjadi **Service**.
- Navigasi tiga halaman Beranda / Service / About menggunakan Streamlit `st.Page` + `st.navigation(position="top")`.
- Homepage ringan, latar putih abu-abu, animasi sengaja ditiadakan.
- Upload CSV terlihat langsung di halaman Service, termasuk saat dibuka via HP.
- CSV dan edit tabel tersimpan sementara selama sesi navigasi, tidak disimpan ke server secara permanen.
- Seluruh analisis, grafik, simulasi, PDF, ZIP v2.0 tetap tersedia di Service.
- Minimal Streamlit 1.46 untuk navigasi atas.

## v2.0
- Audit CSV, edit tabel, perbandingan dataset, simulasi beban, grafik dan laporan otomatis.

## v2.2 — Statistik lanjutan & simulasi target mutu (fase pengembangan 1.2)
- Tambahan modul `concretelab/advanced.py`: kuartil Q1/Q3, P10/P90, median, IQR, CV,
  rata-rata, serta interval bootstrap 95% yang ditampilkan hanya bila sampel n >= 5.
- Tampilan **Service → Data & statistik** kini memiliki pilihan per silinder/per hasil uji,
  filter campuran dan grafik interval dengan Plotly, serta unduh CSV statistik.
- Tampilan **Service → Evaluasi mutu** kini memiliki slider rentang target f'c,
  grafik sensitivitas interaktif, ringkasan status terpisah untuk data yang belum dapat
  dievaluasi, dan unduh CSV simulasi target.
- Tampilan **Service → Visualisasi** memiliki ECDF interaktif per campuran.
- Paket ZIP menambahkan 4 CSV statistik dan sensitivitas. PDF utama tetap mengikuti
  data dan target resmi yang dipilih di sidebar, bukan penggeseran slider skenario.
- Upload-first, navigasi Beranda/Service/About, dan tampilan minimalis tetap dipertahankan.
- Tidak menggunakan data buatan untuk hasil; semua analisis berasal dari CSV aktif.
- Catatan metodologis: interval bootstrap hanya ilustrasi ketidakpastian rerata, bukan
  kriteria penerimaan beton atau jaminan mutu untuk sampel kecil.
