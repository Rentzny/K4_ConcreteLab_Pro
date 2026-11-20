# Panduan pemasangan ConcreteLab Pro v5.5 — Login, Database, Workspace, Approval

## Apa yang benar-benar sudah dibuat

* Mode tamu: **Beranda → Service → About** tetap dapat dipakai tanpa akun Supabase.
* **Akun:** daftar dan login email/password melalui Supabase Auth, logout, profil.
* **Database:** PostgreSQL Supabase dengan *Row Level Security* (RLS) dan kebijakan pemilik/anggota proyek.
* **Proyek Saya:** membuat proyek, berbagi dengan UUID akun pengguna, menyimpan versi CSV, memuat ulang snapshot.
* **Laporan:** versi laporan (metadata + snapshot), pengajuan, pemeriksaan oleh supervisor/pemilik, revisi, penolakan, persetujuan. Pembuat tidak boleh menyetujui sendiri.
* **Admin:** daftar pengguna dan memberi hak admin global (melalui RPC dan aturan server; promosi admin awal manual).
* **Audit:** peristiwa penyimpanan snapshot, draft dan perubahan status laporan dicatat trigger di database.
* **QR online:** laporan berstatus disetujui memperoleh URL verifikasi publik yang menampilkan metadata terbatas dan hash CSV.

**Belum termasuk:** login Google SSO, penyimpanan PDF asli di Supabase Storage, tanda tangan digital, email otomatis, kamera QR di dalam website, dan pengujian end-to-end Cloud dengan Supabase milik pengguna. Google login memerlukan alur OAuth yang aman dan konfigurasi tambahan; **jangan menganggap sudah aktif**.

## Langkah 1. Backup GitHub

Di GitHub Desktop pastikan perubahan v5.0 telah di-*push*. Bisa buat branch baru `upgrade-v5-5` terlebih dahulu untuk menguji tanpa mengganggu produksi. Jalankan SQL di Supabase sebelum menyalakan menu cloud di website publik.

## Langkah 2. Buat project Supabase

1. Buka https://supabase.com/dashboard, buat project (pilih region terdekat).
2. Buka **SQL Editor** → New query. Salin seluruh isi `supabase/schema_v55.sql`, lalu Run.
3. Di **Authentication** → Providers, pastikan Email aktif. Tentukan pengaturan konfirmasi email, URL situs, dan redirect yang sesuai (jangan sembarang menonaktifkan verifikasi email untuk produksi).
4. Di **Project Settings** → API, salin **Project URL** dan **publishable/anon key**. **JANGAN gunakan** `service_role` atau `sb_secret_` key. Jangan unggah file secret ke GitHub.

## Langkah 3. Isi secrets di Streamlit Cloud

Di dashboard Streamlit: Manage app → Settings → Secrets. Isi berdasarkan `supabase/secrets.example.toml`, mengganti URL, key, dan alamat app asli. **Jangan gunakan key contoh secara literal**. Klik Save, lalu reboot aplikasi jika diperlukan.

Untuk uji lokal, isi `.streamlit/secrets.toml` di laptop (file ini sudah diabaikan oleh `.gitignore`).

## Langkah 4. Bootstrap admin pertama

1. Daftar satu akun melalui halaman Akun, konfirmasi email, lalu login.
2. Jalankan perintah ini **manual melalui SQL Editor Supabase** (ganti email contoh):

```sql
UPDATE public.k4_profiles SET global_role='admin'
WHERE user_id=(SELECT id FROM auth.users WHERE email='EMAIL_ADMIN_ANDA');
```

Jangan masukkan email admin atau password dalam source code GitHub.

## Langkah 5. Jalankan tes akses (WAJIB sebelum data nyata)

1. Buat akun A dan B terpisah.
2. Login A, buat Proyek A, simpan snapshot; login B dan pastikan Proyek A **tidak** terlihat.
3. B mencoba membaca URL/ID snapshot proyek A melalui API: harus ditolak oleh RLS.
4. Pemilik A menambahkan B sebagai *viewer*, B dapat membaca proyek tapi **tidak** menyimpan snapshot.
5. Ubah B menjadi *technician*: B dapat menambah snapshot namun tidak dapat menyetujui laporan kecuali diberi izin supervisor.
6. A membuat draft lalu mengajukan; **A tidak bisa menyetujui laporan miliknya sendiri**, walaupun pemilik proyek.
7. B sebagai supervisor menyetujui; QR harus menampilkan hanya metadata status, ID, dan hash, tanpa CSV atau data pribadi.
8. Cabut akses B, pastikan proyek dan snapshot tidak lagi bisa dibaca.
9. Ulangi tes setelah setiap perubahan kebijakan SQL atau plugin keamanan.

**Penting:** 93+ tes Python di paket ini bersifat lokal. Tanpa kredensial Supabase, tes tidak dapat membuktikan RLS online sudah benar.

## Desain hak akses

| Peran | Baca data | Tambah snapshot | Review laporan | Kelola anggota |
|---|---|---|---|---|
| Tamu | Tidak, kecuali analisis CSV sementara | Tidak | Tidak | Tidak |
| Pengguna proyek (pemilik) | Ya | Ya | Ya, kecuali laporan sendiri | Ya |
| Viewer | Ya | Tidak | Tidak | Tidak |
| Technician | Ya | Ya | Tidak | Tidak |
| Supervisor | Ya | Ya | Ya, kecuali laporan sendiri | Ya |
| Admin global | Ya | Ya | Ya, kecuali laporan sendiri | Ya |

Peran **Admin** disimpan di `k4_profiles.global_role` dan *tidak dapat diubah oleh pemilik akun*. Peran teknisi/supervisor diberikan per proyek melalui tabel `k4_project_members`.

## Penyimpanan dan batasannya

- **CSV disimpan sebagai teks snapshot hingga 10 MB** di Supabase (data sensitif memerlukan persetujuan pemilik).
- Setiap snapshot adalah versi baru. Database menulis SHA-256 dari isi snapshot.
- **PDF belum disimpan** ke Supabase Storage. Aplikasi dapat membuat PDF dari snapshot yang dibuka kembali lewat Service dan pengguna mengunduhnya secara lokal.
- Status persetujuan adalah **review internal aplikasi**, bukan sertifikasi laboratorium atau tanda tangan elektronik.
- QR membuktikan bahwa metadata yang disetujui tersedia di database dan mencocokkan fingerprint yang dicatat; bukan jaminan mutu beton nyata.
- Konfigurasi layanan berbayar/limit Supabase, email verification, dan kebijakan backup berada di bawah pengelola proyek.
- Session login tersimpan di memori sesi Streamlit; jika browser disegarkan, pengguna bisa perlu login ulang.
- **Jangan menguji data rahasia** sampai pemeriksaan RLS dua akun selesai.

## Troubleshooting

| Gejala | Penyebab / tindakan |
|---|---|
| Service berjalan tetapi Akun menampilkan belum dikonfigurasi | Isi `supabase.url` dan `supabase.publishable_key` di Secrets |
| `relation k4_projects does not exist` | Jalankan SQL schema v5.5 pada project Supabase yang benar |
| `permission denied` | Pastikan user login dan keanggotaan proyek sesuai; periksa RLS di SQL Editor |
| Login gagal | Verifikasi email, provider email, dan pengaturan autentikasi |
| QR tidak muncul | Pastikan laporan `approved` dan `public_base_url` valid HTTPS |
| Tidak dapat mereview | Peran harus supervisor/pemilik/admin, pembuat laporan lain, status `submitted` |
| Website Cloud error setelah update | Lihat Manage app → Logs, cek secrets/requirements dan jangan tampilkan kredensial |
