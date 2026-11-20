# ConcreteLab Pro v6.0.1 — Perbaikan Login Hilang Setelah Refresh

Masalah sebelumnya: Supabase client dan session JWT hanya disimpan dalam `st.session_state`. Pada refresh penuh (F5/Ctrl+F5), WebSocket baru dibuat dan session state hilang. Ini bukan masalah akun Administrator.

## Perubahan kode

- Tambah centang **Ingat saya selama 7 hari (hanya perangkat pribadi)** di halaman Akun → Masuk.
- Jika dipilih, *refresh token* Supabase disimpan sebagai cookie yang **dienkripsi oleh Fernet di sisi server** menggunakan kunci dari Streamlit Secrets.
- Setelah browser reload, token cookie didekripsi di server dan diverifikasi ulang melalui `Supabase Auth.refresh_session()`. Cookie berisi token refresh **terbaru** setelah token diputar.
- Logout menghapus cookie dan mengakhiri sesi Supabase.
- Mode tamu, 13 pengaturan fitur, proyek privat, RLS database, dan fitur analisis tetap sama. **Tidak ada SQL migrasi baru.**
- Jika pengaturan enkripsi belum ada atau cookie diblokir browser, login biasa masih berfungsi tetapi tidak menetap setelah refresh.

## Tahap 1 — Pasang paket update

1. Backup proyek dan GitHub repository jika perlu.
2. Ekstrak `K4_ConcreteLab_Pro_v6_0_1_FIX_LOGIN.zip`.
3. Salin isi ZIP ke **root repository K4_ConcreteLab_Pro**, sejajar dengan `app.py`. Timpa file yang berubah; **jangan hapus** `.git`, `.venv`, atau Secrets.
4. GitHub Desktop: Commit dengan summary `Fix persistent Supabase login v6.0.1`, lalu Push origin.
5. Streamlit Community Cloud akan memasang paket tambahan dari `requirements.txt`.

## Tahap 2 — Buat kunci enkripsi menggunakan Windows PowerShell

Jalankan **kode berikut pada PowerShell lokal**, bukan pada Supabase SQL Editor:

```powershell
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
([Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_') + '=')
```

Output akan berupa string acak sekitar 44 karakter. **Jangan bagikan ke chat, GitHub, atau screenshot.** Simpan privat karena orang yang memiliki kunci dapat mendekripsi cookie sesi.

## Tahap 3 — Tambahkan ke Streamlit Secrets

Buka Streamlit Community Cloud → Manage app → Settings → Secrets.
**Pertahankan** konfigurasi `public_base_url` dan `[supabase]` lama; **tambahkan** bagian ini di luar `[supabase]`:

```toml
[auth_persistence]
fernet_key = "PASTE_KUNCI_RAHASIA_DARI_POWERSHELL"
```

**PENTING:** Jangan menggunakan `sb_publishable_...` sebagai kunci enkripsi. Jangan memasukkan key ke repo.

Contoh struktur lengkap TANPA kredensial nyata:

```toml
public_base_url = "https://nama-website.streamlit.app"

[supabase]
url = "https://id-proyek.supabase.co"
publishable_key = "sb_publishable_..."

[auth_persistence]
fernet_key = "KUNCI_RANDOM_PRIBADI_DARI_POWERSHELL"
```

Klik Save. Pastikan tidak ada dua blok `[supabase]` atau `[auth_persistence]`.

## Tahap 4 — Uji

1. Buka website → **Akun** → **Keluar dari akun** jika masih login.
2. Masuk kembali, centang **Ingat saya selama 7 hari**.
3. Setelah berhasil login, tekan **F5** sekali (bukan tombol rerun Streamlit).
4. Halaman mungkin sesaat menampilkan mode tamu ketika komponen cookie dimuat; setelah beberapa saat, pengguna seharusnya kembali masuk tanpa password.
5. Klik **Keluar dari akun**, kemudian refresh lagi; kali ini seharusnya tetap logout.
6. Uji juga di browser Incognito untuk memastikan sesi terpisah.

## Catatan keamanan dan batas pengujian

- Cookie berasal dari komponen JavaScript, bukan cookie HttpOnly. Token di dalamnya terenkripsi; tetapi cookie terenkripsi tetap dapat **disalin dan dipakai ulang** bila perangkat atau sesi browser disusupi. Gunakan hanya pada perangkat pribadi yang dipercaya.
- Tombol logout membatalkan sesi; mengganti kunci Fernet di Secrets akan membuat seluruh cookie lama tidak bisa dipakai.
- Mode ini **opt-in**, tidak otomatis mengingat login semua orang.
- Telah diuji melalui 141 tes Python (1 tes integrasi cloud sengaja dilewati); pengujian khusus sesi memakai mock Supabase & cookie. Belum diuji pada browser/Streamlit Cloud dengan akun nyata.
- Pemasangan dan mengaktifkan opsi ini tidak memerlukan schema SQL baru dan tidak mempengaruhi RLS Supabase.
