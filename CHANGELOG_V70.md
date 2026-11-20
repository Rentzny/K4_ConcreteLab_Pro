# ConcreteLab Pro v7.0 — Unified Administrator & Laboratory Dashboard

- Paket update langsung dari v5.5. Termasuk fitur kode v6.0 dan hotfix v6.0.1; tanpa instalasi kedua versi terpisah.
- Menu baru **Administrator** untuk akun dengan `global_role=admin` dan `account_status=active`.
- Dashboard Admin: KPI akun/pending/proyek/laporan/fitur tamu, ringkasan grafik status akun dan laporan, proyek terbaru.
- Guest Control: preset semua fitur analisis ON / akses dasar / semua OFF, 13 izin terperinci, dan pratinjau kebijakan.
- Manajemen akun: buka/tutup pendaftaran website, set status pending/active/suspended, pilihan peran tanpa mengetik UUID, opsi undangan melalui Edge Function Supabase yang terpisah.
- Audit Admin dan pemeriksaan keamanan; seluruh perubahan admin melalui Supabase RPC yang memeriksa peran di database.
- Opsi Ingat Saya (7 hari) melalui refresh token Supabase yang dienkripsi dalam cookie browser, dengan kunci khusus pada Streamlit Secrets.
- Perbaikan URL konfigurasi: menolak `/rest/v1` dan path API lain pada `supabase.url`.
- `schema_v55.sql` referensi untuk instalasi baru diperbaiki (digest hash langsung); **pengguna yang sudah memasang schema tidak boleh menjalankan ulang untuk upgrade kode ini**.
- Pengujian tambahan: ringkasan Admin, semua preset, fail-closed, dan guard konfigurasi.

**Batasan:** Login Google dan pembuatan akun privileged langsung dari Streamlit tanpa Supabase Edge Function belum tersedia. Tes live Streamlit browser/Supabase tetap diperlukan.
