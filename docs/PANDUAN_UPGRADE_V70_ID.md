# Panduan upgrade ConcreteLab Pro v7.0 — Langsung dari v5.5

## Kondisi proyek Anda sekarang

Dari pengujian sebelumnya, akun administrator sudah **berhasil login** dengan peran `admin` dan `account_status=active`. Database Supabase telah memperoleh schema v5.5 **dan migrasi v6.0** (tabel `k4_public_settings` muncul). Anda menyampaikan kode aplikasi **v6.0 belum dipasang**. Paket UPDATE v7.0 ini **sengaja mencakup seluruh perubahan kode dari v5.5 → v6.0 → hotfix v6.0.1 → dashboard v7.0 sekaligus**.

**Jadi: jangan jalankan ulang schema_v55.sql atau schema_v60.sql jika tabel dan akun masih seperti kondisi di atas.** Migrasi tidak perlu diulang saat hanya memperbarui kode. Buat backup database sebelum perubahan besar di masa depan.

## Apa yang sudah ada setelah upgrade

- Navigasi Beranda, Service, About, Proyek Saya, Akun tetap ada. Menu **Administrator** muncul otomatis saat akun aktif dengan `global_role='admin'` login.
- Dashboard Admin (v7) dengan metrik jumlah akun, akun pending, proyek, laporan, 13 izin tamu, grafik status akun/laporan, audit admin.
- Tamu boleh menggunakan analisis sesuai 13 izin; pilih preset semua ON, dasar, semua OFF, atau atur tiap fitur.
- Form pendaftaran email/password memakai Supabase Auth. Admin dapat menyetujui, menangguhkan, mengaktifkan akun dan mengubah peran dengan memilih akun dari daftar **tanpa mengetik UUID**.
- Cara mengundang pengguna: dari Supabase Dashboard → Authentication → Users → Invite User; atau melalui Edge Function opsional jika di-deploy terpisah. **Tidak ada tombol yang membuat akun dengan hak istimewa secara langsung tanpa izin backend**.
- Opsi *Ingat saya selama 7 hari*: mengandalkan browser cookie terenkripsi + token refresh Supabase. Opsi ini hanya aktif jika kunci Fernet dipasang pada Streamlit Secrets.
- Service, analitik v4, registrasi sampel v5, PDF, QR, arsip, Proyek Saya, dan persetujuan laporan tetap tersedia.

## A. Pasang file v7.0 ke GitHub Desktop

1. **Cadangkan** proyek di komputer (contoh folder `K4_ConcreteLab_Pro`) atau buat branch backup pada GitHub Desktop.
2. Unduh `K4_ConcreteLab_Pro_v7_0_UPDATE_GITHUB.zip` dan **ekstrak**.
3. Buka folder hasil ekstrak. **Salin ISI folder** (misalnya `app.py`, `app_pages`, `concretelab`, `requirements.txt`, dst.) ke folder GitHub yang berisi `app.py` lama.
4. Saat Windows meminta konfirmasi, pilih **Replace the files in the destination**. **Jangan hapus `.git` atau `.venv`**.
5. Periksa tab **Changes** di GitHub Desktop. Pastikan tidak ada `secrets.toml`, cookie, password atau file basis data lokal yang ikut berubah.
6. Isi Summary `Upgrade ConcreteLab Pro v7.0 Unified Admin Dashboard`, lalu **Commit to main → Push origin**.
7. Pantau redeploy Streamlit. Jika terjadi error, buka Manage app → Logs lalu kirim traceback tanpa secret.

**Tidak perlu menginstal file UPDATE v6.0 atau hotfix v6.0.1 terlebih dahulu.** Semua komponennya ada di UPDATE v7.0 ini.

## B. Periksa Streamlit Secrets

Konfigurasi lama `[supabase]` yang **sudah berhasil untuk login** tetap digunakan. Jangan mengubah URL, key, ataupun membuat project Supabase baru. Contoh struktur (hanya placeholder):

```toml
public_base_url = "https://ALAMAT-WEBSITE.streamlit.app"

[supabase]
url = "https://PROJECT-ID.supabase.co"
publishable_key = "sb_publishable_ISI_KEY"
```

**Penting:** URL harus berupa Project URL dasar, **tanpa `/rest/v1/`**. Jangan menaruh `service_role`, `sb_secret_`, database password, atau nilai `auth_persistence.fernet_key` di GitHub.

### Opsional: Agar tetap login sesudah F5 / Ctrl+F5

Pada komputer Windows, buka **PowerShell** untuk membuat kunci enkripsi *Fernet* yang acak:

```powershell
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
([Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_') + '=')
```

Salin **hasilnya secara pribadi**, lalu di Streamlit Cloud → Manage app → Settings → Secrets, **tambahkan di bagian bawah** (di luar `[supabase]`):

```toml
[auth_persistence]
fernet_key = "TEMPEL_KUNCI_ACAK_POWERSHELL"
```

Klik Save. Login kembali pada website → **Akun** → centang **Ingat saya selama 7 hari** sebelum klik Masuk. Lalu coba F5. Logout harus membersihkan token tersimpan. Cookie dipasang via JavaScript dan **tidak HttpOnly**, jadi opsi ini hanya untuk perangkat pribadi tepercaya; pencurian cookie terenkripsi tetap berpotensi dipakai mengulang sesi.

Bila tidak ingin fitur Ingat Saya, **biarkan `[auth_persistence]` tidak dikonfigurasi**. Login biasa tetap bekerja, tetapi F5 mungkin mengharuskan login kembali karena sesi Streamlit ter-reset.

## C. Coba dashboard Administrator v7.0

1. Buka website, klik **Akun → Masuk** dan login sebagai Admin yang sebelumnya sudah aktif. **Jangan buat akun baru**.
2. Di navigasi atas, klik **🛡️ Administrator** atau gunakan tautan **Buka Panel Administrator** dari halaman Akun.
3. Pada **Ringkasan**, periksa total akun, status pending, proyek, laporan dan grafik.
4. Pada **Akses Tamu**, klik preset **Semua Analisis ON** jika ingin tamu memakai seluruh *analisis publik*, lalu coba browser Incognito tanpa login. Ubah ke **Akses Dasar** atau **Semua Analisis OFF** untuk menguji bahwa Service benar-benar menerapkan aturan.
5. Pada **Pengguna & Akun**, akun baru masuk `pending`, pilih berdasarkan nama/email, set `active` dan klik simpan setelah konfirmasi. **UUID tidak perlu diisi manual**.
6. Pada **Audit & Keamanan**, periksa log perubahan admin.

**Batas akses tamu:** Semua fitur analisis ON **tidak** memberikan hak untuk melihat proyek privat, mengelola pengguna, membuka audit, atau menyetujui laporan.

## D. Pengujian keamanan yang perlu dilakukan setelah pemasangan

- Jalankan incognito tanpa login: preset **OFF** harus menolak upload CSV; preset **ON** mengizinkan analisis.
- Logout Admin, refresh; cookie sebelumnya harus dibersihkan. Ulangi dalam tab baru.
- Daftarkan satu akun uji terpisah. Sebelum disetujui, status `pending`, tidak boleh membuka proyek cloud. Admin kemudian aktifkan dan uji lagi.
- Akun pengguna biasa tidak boleh melihat menu Administrator atau mengakses `/admin`; semua RPC admin juga wajib ditolak Supabase.
- Dua akun berbeda tidak boleh bisa saling membaca proyek pribadi (uji lewat API/RLS, bukan hanya dengan melihat tombol).

**Batas pengujian paket:** Tes Python offline dilakukan; tes login nyata dengan cookie di browser, deployment Edge Function, dan integrasi RLS dua akun memerlukan pengujian pada Supabase/Streamlit milik Anda. Jangan simpan data rahasia sebelum pengujian tersebut beres.

## E. Jika error

- **Administrator tidak muncul**: login ulang, periksa profile `global_role='admin'`, `account_status='active'`, dan URL web yang benar. Database v6 sudah terpasang.
- **Koneksi Supabase gagal**: periksa Secret `[supabase] url` **tanpa** `/rest/v1`.
- **Ingat Saya nonaktif**: periksa Secret `[auth_persistence] fernet_key`, jangan gunakan publishable key sebagai Fernet key.
- **Tidak bertahan setelah refresh**: centang Ingat Saya saat login, pastikan cookie browser diterima, periksa Streamlit Logs. Plugin cookie bergantung pada browser dan mungkin diblokir oleh ekstensi atau aturan browser.
- **Tamu tidak bisa upload**: periksa preset pada Administrator dan keberhasilan load `k4_public_settings`.
- **Tombol undangan gagal**: Supabase Edge Function itu opsional; undang via Supabase → Authentication → Users → Invite User.

**Perlu diingat:** hasil kuat tekan dan evaluasi mutu adalah perhitungan/simulasi; aplikasi tidak otomatis menerbitkan sertifikat laboratorium resmi.
