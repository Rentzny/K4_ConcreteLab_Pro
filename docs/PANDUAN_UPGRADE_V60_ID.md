# Panduan Pemasangan K4 ConcreteLab Pro v6.0

**Upgrade dari v5.5 ke v6.0 — Admin Control Center & Guest Access**

> **Jangan langsung push aplikasi sebelum migrasi SQL dijalankan dan akun Admin disiapkan.** v6 menutup akses tamu sementara saat backend Supabase dikonfigurasi tetapi izin belum bisa diverifikasi, agar tidak mengabaikan keputusan administrator.

## 1. Apa yang sudah tersedia pada kode

- **Beranda, Service, About** tetap ada dan fitur analisis, grafik, simulasi, PDF, CSV, ZIP, QR, dan jadwal versi sebelumnya dipertahankan.
- **Akun**: login Supabase email/password, daftar akun, keluar, status *pending/active/suspended*. Password dikelola Supabase Auth; tidak disimpan di Streamlit.
- **Administrator**: menu hanya muncul setelah server mengenali akun aktif berperan admin.
- **Kendalikan tamu**: 13 sakelar fitur; preset *Semua Analisis*, *Hanya Dasar*, *Semua Ditutup*. Izin dibaca ulang setiap render halaman; perubahan berlaku saat pengunjung melakukan interaksi/rerun atau refresh.
- **Pendaftaran**: sakelar formulir pendaftaran, verifikasi email (jika diaktifkan di Supabase), dan persetujuan admin untuk akses cloud.
- **Akun pengguna**: admin dapat menyetujui/menangguhkan akun dan mengubah peran pengguna (`user`/`admin`).
- **Audit administrator**: perubahan hak akses tamu, status akun, dan peran tercatat pada database.
- **Undang akun lewat email**: opsional jika Edge Function `k4-admin-invite` sudah di-deploy dengan aman. Alternatif: **Supabase → Authentication → Users → Invite User**.

**Batasan:** “Semua fitur tamu ON” hanya mengaktifkan analisis publik (upload CSV, edit, statistik, grafik, simulasi, bandingkan, unduhan, arsip lokal, jadwal, audit, metode). Itu **bukan** akses database proyek privat, hak admin, persetujuan laporan, atau daftar pengguna. Akun `pending/suspended` diperlakukan sama dengan tamu pada halaman Service dan ditolak RLS pada proyek cloud.

## 2. Urutan pemasangan yang aman

1. **Backup** data Supabase dan pastikan kode v5.5 dalam GitHub sudah ter-*commit*. Jika perlu buat branch `upgrade-v6` untuk menguji sebelum mengubah `main`.
2. Pastikan Supabase v5.5 aktif, database dan `supabase/schema_v55.sql` sudah pernah dipasang. Jika belum, **pasang schema_v55.sql dulu**.
3. Buka Supabase Dashboard → SQL Editor → New query. Salin seluruh isi `supabase/schema_v60.sql` lalu **Run**. Migrasi menambah tabel pengaturan, status akun dan audit log. Akun lama yang sudah ada dijadikan aktif sekali; akun yang baru mendaftar setelah migrasi akan `pending`.
4. Verifikasi akun admin awal: gunakan akun yang kamu sendiri buat dan email-nya sudah terverifikasi. Di SQL Editor jalankan (ganti email):

   ```sql
   UPDATE public.k4_profiles
   SET global_role='admin', account_status='active'
   WHERE user_id=(SELECT id FROM auth.users WHERE email='EMAIL_ADMIN_MILIKMU');
   ```

   Jangan memasukkan email asli dan password ke repo publik atau membagikannya di chat.
5. Di Streamlit Community Cloud → Manage app → Settings → Secrets, pastikan `supabase.url` dan `supabase.publishable_key` milik proyek benar. **Hanya anon/publishable key**; jangan gunakan `service_role` / `sb_secret_` di Streamlit.
6. Pasang **UPDATE v6** ke folder repo GitHub lama: salin seluruh isi ZIP ke root `K4_ConcreteLab_Pro`, pilih *Replace* dan jangan hapus `.git`/`.venv`.
7. Jalankan pengujian lokal melalui `.venv` setelah memasang dependensi. Lakukan **Commit → Push origin**. Di Streamlit, cek Beranda, Service tanpa login, menu Akun dan menu Administrator setelah login sebagai admin.
8. Uji dengan browser privat/incognito sebagai tamu dan ulangi setelah setiap perubahan kebijakan.

## 3. Kontrol yang bisa diubah oleh Admin

Dalam menu **Administrator → Akses Tamu**:

- **Aktifkan Semua Analisis**: semua 13 fitur analisis tamu aktif (tanpa akses cloud privat).
- **Hanya Akses Dasar**: upload CSV, ringkasan, statistik, grafik, dan metode aktif.
- **Nonaktifkan Akses Tamu**: Service menolak analisis tamu sampai izin dihidupkan kembali.
- **Izin terperinci**: pilih sendiri editor, kualitas, simulasi, perbandingan CSV, audit, download PDF/CSV/ZIP, arsip lokal, dan jadwal sampel.

Perubahan disimpan di `k4_public_settings` melalui **RPC yang memverifikasi `k4_is_admin()` di database**. Sistem menolak jika aturan tidak dapat dibaca pada deployment yang telah dikonfigurasi Supabase. Pengunjung yang sedang membuka halaman mungkin perlu berinteraksi atau refresh untuk memuat izin terbaru.

## 4. Pembuatan akun, login, dan Admin

1. Pengguna melakukan **Akun → Daftar akun** menggunakan email/password. Konfirmasi email jika diminta oleh Supabase.
2. Pengguna dapat login, tetapi akun baru masih `pending`; akses proyek cloud ditolak hingga admin memberi persetujuan.
3. Admin login → Administrator → Pendaftaran dan Persetujuan Akun → pilih akun → status `active`.
4. Admin boleh mengubah akun menjadi `suspended` ketika akses perlu dihentikan; RLS memeriksa status aktif untuk membaca/mengubah proyek cloud.
5. Admin bisa mengundang akun baru melalui `Supabase Dashboard → Authentication → Users → Invite User` tanpa Edge Function.

**Peringatan keamanan pendaftaran:** sakelar “Tampilkan formulir pendaftaran” hanya mengubah UI. Untuk benar-benar mencegah signup publik, kamu harus mengatur **Supabase Auth settings**. Akun yang dibuat langsung melalui endpoint Supabase tetap **pending**, jadi belum memperoleh akses database proyek.

## 5. Opsi undang akun langsung dari panel Admin (Edge Function)

Bagian ini opsional. Jika tidak dipasang, fitur akun/login dan sakelar tamu tetap dapat bekerja dengan database v6.

- Persiapkan Supabase CLI di komputer tepercaya dan hubungkan ke proyek yang benar.
- Deploy fungsi `supabase/functions/k4-admin-invite/index.ts` melalui `supabase functions deploy k4-admin-invite --no-verify-jwt` **hanya karena fungsi memverifikasi JWT pengguna dengan Supabase Auth di dalam kode, kemudian memeriksa status admin aktif di database**. Jangan hapus verifikasi ini.
- Secret `SUPABASE_SERVICE_ROLE_KEY` hanya boleh berada pada **Supabase Edge Function Environment**. Gunakan fasilitas secret management di Supabase. **JANGAN** menaruhnya pada kode GitHub atau Streamlit Secrets.
- Fungsi hanya mengizinkan admin aktif untuk mengirim email undangan dan membatasi 10 undangan per jam per admin. Setelah pengguna menerima undangan, status akun tetap `pending` hingga admin mengaktifkan.
- Jika fungsi belum di-deploy, gunakan menu undangan dari Supabase Dashboard saja.

## 6. Uji akses yang WAJIB sebelum digunakan orang lain

| Pengujian | Hasil yang benar |
|---|---|
| Tamu, semua izin ON | Bisa analisis CSV dan unduh laporan, **tidak** bisa mengakses Proyek Saya privat |
| Tamu, semua izin OFF | Tidak bisa menjalankan analisis di Service |
| Tamu, grafik OFF | Tab Visual Analytics terkunci; fungsi grafik tidak dieksekusi |
| Tamu, ekspor OFF | Tombol unduh CSV, PDF, ZIP, label, ICS tidak ditampilkan/berfungsi |
| Tamu, editor OFF | Tidak bisa mengubah CSV melalui editor |
| Akun baru | Status pending, tidak bisa membuat/membaca proyek cloud |
| Akun aktif | Bisa mengelola proyek sendiri sesuai RLS |
| Akun ditangguhkan | Tidak bisa membaca/mengubah proyek lewat API Supabase |
| Akun B mengakses proyek A | Ditolak jika belum menjadi anggota |
| Pengguna biasa membuka `/admin` | Ditolak, termasuk pemanggilan RPC admin langsung |
| Akun biasa mencoba menaikkan peran sendiri | Ditolak di database |
| Admin mengubah izin tamu | Berlaku pada rerun/refresh kunjungan tamu berikutnya |
| Pembuat laporan menyetujui laporan sendiri | Ditolak di backend |

**Catatan:** Pengujian unit Python tidak menggantikan tes langsung dengan 2–3 akun sungguhan dan database Supabase. Lakukan di project Supabase uji dahulu, terutama RLS/Edge Function. Jangan memasukkan data laboratorium rahasia sebelum pengujian keamanan berhasil.

## 7. Perbaikan masalah umum

- **Service tidak menampilkan upload setelah upgrade:** pastikan `schema_v60.sql` sudah dijalankan; konfigurasi Supabase benar; semua fitur tamu tidak di-OFF-kan.
- **Akun dapat login tetapi Proyek Saya tertutup:** akun masih `pending`/`suspended`, minta admin mengubahnya menjadi `active`.
- **Administrator tidak muncul di navigasi:** logout lalu login lagi, periksa `k4_profiles.global_role='admin'` dan `account_status='active'`.
- **Undangan email tidak berfungsi:** Edge Function belum di-deploy; gunakan menu Supabase Dashboard atau periksa log Edge Function.
- **Dapat membuat proyek tapi data tidak terlihat untuk pengguna lain:** periksa membership project/RLS, bukan mematikan RLS.
- **Ingin kembali ke versi sebelumnya:** rollback commit dari GitHub Desktop dan **jangan otomatis menghapus tabel/migrasi database**; lakukan backup dulu.

Versi ini merupakan sistem prototipe internal, **bukan layanan laboratorium tersertifikasi**. QR, metadata persetujuan, dan hash bukan tanda tangan digital maupun bukti pemenuhan mutu beton.
