"""ConcreteLab Pro v8 — Supabase account, registration, optional remember-me."""
import streamlit as st
from concretelab.cloud_ui import cloud_client, signed_user, logout, cloud_notice
from concretelab.cloud import get_profile
from concretelab.permissions import load_access_policy

st.title('Akun & Akses')
st.caption('Kelola profil, proyek cloud, dan hak akses. Pendaftaran akun baru v8.0 tidak memerlukan persetujuan manual Administrator.')
st.divider()

try:
    client, user = signed_user()
except Exception:
    st.error('Koneksi Supabase belum dapat digunakan. Periksa Secrets dan konfigurasi database.')
    st.stop()
if client is None:
    cloud_notice()
    st.stop()

if user is None:
    from concretelab.auth_views import render_auth_forms
    policy = load_access_policy(client, cloud_configured=True)
    render_auth_forms(client, registration_enabled=policy.registration_enabled, gateway=False)
    st.stop()

uid=str(user.id)
profile=None
try: profile=get_profile(client,uid)
except Exception: st.warning('Profil belum tersedia. Pastikan schema_v55.sql sudah dijalankan.')
role=(profile or {}).get('global_role','user')
status=(profile or {}).get('account_status','pending')
st.success('Kamu sudah login.')
st.write('**Email:**',getattr(user,'email','—'))
st.code(uid,language=None)
st.caption('ID pengguna ini digunakan untuk menambahkan anggota proyek. Bagikan hanya kepada pemilik proyek yang tepercaya.')
st.write('**Peran global:**',role)
st.write('**Status akses cloud:**',status)
if status == 'pending':
    st.warning('Akun lama masih berstatus pending. Hubungi Administrator untuk mengaktifkan akun ini. Akun yang didaftarkan setelah migrasi v8.0 langsung aktif.')
elif status == 'suspended':
    st.error('Akun ditangguhkan. Hubungi administrator. Proyek cloud tidak dapat dibuka.')
if st.button('Keluar dari akun',type='secondary'):
    logout()
    st.session_state['k4_guest_continue'] = False
    st.rerun()

if profile:
    with st.form('profile_edit'):
        display=st.text_input('Nama tampilan',value=profile.get('display_name','') or '',max_chars=100)
        save=st.form_submit_button('Simpan nama')
    if save:
        try:
            client.table('k4_profiles').update({'display_name':display.strip()}).eq('user_id',uid).execute()
            st.success('Nama berhasil diperbarui.')
        except Exception:
            st.error('Gagal memperbarui profil. Periksa izin Supabase.')

if role == 'admin' and status == 'active':
    st.divider()
    st.page_link('app_pages/admin.py',label='Buka Panel Administrator',icon='🛡️')
