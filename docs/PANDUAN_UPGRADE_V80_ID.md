# ConcreteLab Pro v8.0 — Panduan Upgrade (Indonesia)

## Ringkasan

Paket v8.0 dibuat berdasarkan **proyek lengkap v7.0**. Fitur utama:

- Halaman pembuka responsif: **Masuk**, **Daftar Akun**, **Lanjutkan sebagai Tamu**.
- Form pendaftaran: Email, Password, **Konfirmasi Password**; validasi cocok sebelum dikirim ke Supabase.
- **Akun pengguna baru langsung aktif**, tanpa persetujuan manual Administrator, **SETELAH menjalankan migrasi SQL v8.0**. Role tetap `user`, bukan `admin`.
- Email konfirmasi dari Supabase Auth, bila diaktifkan, **tetap diperlukan** sebelum login. Ini berbeda dari persetujuan manual Administrator.
- Panel Administrator, kendali 13 fitur analisis tamu, QR, jadwal, Service, laporan dan Proyek Saya v7 dipertahankan.
- Opsi **Ingat saya** berlaku untuk semua akun ketika `[auth_persistence].fernet_key` telah dikonfigurasi.

## Tahap A — Database terlebih dahulu (WAJIB)

1. Backup database melalui mekanisme yang tersedia di Supabase.
2. Masuk ke proyek Supabase **K4-ConcreteLab-Pro** → **SQL Editor** → **New query**.
3. Buka file `supabase/schema_v80.sql` dari ZIP, salin semua isinya dan **Run**.
4. Verifikasi default `account_status`:

```sql
SELECT column_name, column_default
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='k4_profiles'
  AND column_name='account_status';
```

**Hasil harapan:** `column_default = 'active'::text` (representasi dapat sedikit berbeda).

Migrasi bersifat kecil dan aman untuk dijalankan ulang: mengubah default profil akun **yang baru dibuat**, **tidak mengaktifkan otomatis akun lama yang pending/suspended**, tidak memodifikasi Admin, dan tidak menonaktifkan RLS.

## Tahap B — Pengaturan Supabase Auth

Supabase → **Authentication → Sign In / Providers → Email**:

- Pastikan pendaftaran akun baru diizinkan (jika ingin pendaftaran publik).
- Sebaiknya **Confirm Email tetap aktif**. Pendaftar baru akan memverifikasi email sebelum bisa login, tetapi tidak perlu menunggu persetujuan Admin.
- Jangan menonaktifkan konfirmasi email hanya untuk menghilangkan persetujuan Admin; keduanya berbeda.
- Sakelar pendaftaran di dashboard ConcreteLab mengatur **tampilan form** saja. Untuk memblokir pendaftaran melalui API, nonaktifkan signup di Supabase Auth juga.

## Tahap C — Upgrade GitHub

1. Unduh `K4_ConcreteLab_Pro_v8_0_UPDATE_GITHUB.zip`.
2. Ekstrak dan salin seluruh **isi folder** ke repository lokal `K4_ConcreteLab_Pro`, sejajar dengan `app.py`.
3. Replace file yang berubah; **jangan menghapus** `.git`, `.venv`, atau folder proyek pengguna.
4. GitHub Desktop → Changes → Commit (`Upgrade ConcreteLab Pro v8.0`) → Push origin.
5. Streamlit Cloud akan deploy otomatis. Config `[supabase]` yang sudah berfungsi tidak perlu diubah.

## Tahap D — Pengujian nyata setelah deployment

1. **Incognito/HP** → buka alamat utama website; halaman awal menampilkan **Masuk / Daftar Akun / Lanjutkan sebagai Tamu**.
2. Pilih **Lanjutkan sebagai Tamu** → Beranda → Service; coba upload CSV dan periksa izin berdasarkan setelan Admin.
3. Buka sesi Incognito baru → **Daftar Akun** → isi email baru dan dua password berbeda → aplikasi menolak.
4. Isi password cocok dan submit; verifikasi email jika diminta Supabase.
5. Login sebagai akun baru → **Proyek Saya**. Periksa akun pada Admin dashboard: `global_role=user`, `account_status=active`.
6. Login akun Admin lama → periksa menu Administrator, pengaturan 13 fitur tamu dan hak akun baru.
7. Pada HP, periksa susunan halaman vertikal serta fungsi kolom dan tombol.
8. Uji bahwa akun baru tidak bisa melihat proyek akun lain, dan tamu tidak bisa membuka proyek privat (pengujian RLS dua akun).
9. Pilih **Ingat saya** di perangkat pribadi (jika sudah diaktifkan di Streamlit Secrets); uji refresh lalu logout.

## Batasan

- Tanpa migrasi v8, form pendaftaran bisa berhasil tetapi profil tetap `pending` karena default dari schema v6.
- Akun `pending` dari versi lama **tidak diaktifkan otomatis** demi keamanan. Admin dapat mengaktifkannya manual.
- Fitur **Lanjutkan sebagai Tamu** tidak membuat akun anonim Supabase atau hak cloud; hanya membuka analisis publik sesi lokal berdasarkan izin Admin.
- Pilihan tamu disimpan di `st.session_state`, bukan cookie permanen. Refresh penuh sebagai tamu dapat menampilkan halaman sambutan lagi.
- Halaman verifikasi QR tetap tersedia melalui `?verify=...` tanpa masuk.
- Jangan mengirim password, refresh token, Fernet Key, atau secret/service-role key kepada siapa pun.
- Kode sudah diuji secara lokal dengan unit tests dan pemeriksaan sintaks; koneksi ke Supabase nyata, alur email, dan layout langsung di browser Streamlit Cloud harus diuji setelah deployment.
