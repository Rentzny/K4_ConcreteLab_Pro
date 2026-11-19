# K4 ConcreteLab Pro — Riwayat Pengembangan

## v2.0 — Smart Audit, What-if & Dataset Comparison

### Fitur baru

- **Audit input baris-per-baris**: kesalahan diberi nomor baris CSV, kolom, kategori, dan saran perbaikan. Tidak ada data yang dihapus otomatis.
- **Pengaturan upload-first dipertahankan**: tanpa CSV, tidak ada hasil statistik, grafik, atau PDF.
- **Simulasi beban**: skenario perubahan beban maksimum dari -50% sampai +100% dan grafik sensitivitas lima skenario. Perhitungan baru tidak mengubah CSV maupun PDF utama.
- **Bandingkan CSV**: membaca berkas pembanding secara opsional dan menampilkan selisih rata-rata serta CV antar-campuran, tanpa menggabungkan sampel.
- **Tab audit input**: riwayat temuan yang bisa diunduh sebagai CSV.
- **Ekspor diperluas**: paket ZIP dan CLI mencakup `audit_input.csv` serta metadata versi.
- **Cache hasil ekspor**: PDF dan ZIP dipersiapkan lagi hanya jika CSV atau parameter laporan berubah.
- **CI GitHub Actions**: menjalankan sintaks dan seluruh uji otomatis pada Python 3.11 dan 3.13.

### Fitur tetap ada

- `BendaUji`, validasi data, perhitungan MPa, statistik, outlier screening, simulasi SNI terbatas, empat grafik, dan PDF A4 multi-halaman.
- Dashboard upload-first, data editor, unduh CSV, ZIP, PDF, dan CLI lokal.

### Catatan penting

- Verifikasi Python/perhitungan dan pembuatan PDF dilakukan lokal; **dashboard Streamlit belum diuji end-to-end di browser pada lingkungan pengembangan ini** karena paket Streamlit tidak tersedia di sana.
- Untuk laboratorium nyata, sesuaikan dengan standar yang berlaku dan protokol validasi serta keamanan data.
