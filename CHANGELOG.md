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
