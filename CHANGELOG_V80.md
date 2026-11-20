# ConcreteLab Pro v8.0

**Target:** upgrade langsung dari v7.0, dengan database v5.5+v6 sudah aktif.

Perubahan: landing login/daftar/tamu yang responsif, konfirmasi password, akun baru tanpa manual approval Admin, SQL migrasi default `active` (role tetap user), panduan upgrade dan tes.

Pelaksanaan: **jalankan `supabase/schema_v80.sql` sebelum deploy kode v8.0**. Verifikasi email dari Supabase bisa tetap diwajibkan dan sebaiknya dipertahankan. Tidak ada akun tamu cloud baru yang dibuat.
