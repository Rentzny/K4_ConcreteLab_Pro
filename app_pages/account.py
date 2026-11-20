"""ConcreteLab Pro v7 — Supabase account and optional remember-me sign-in."""
import streamlit as st
from concretelab.cloud_ui import cloud_client, signed_user, logout, cloud_notice
from concretelab.cloud import sign_in, sign_up, get_profile
from concretelab.permissions import load_access_policy
from concretelab.persistent_session import persistence_enabled

st.title('Akun & Akses')
st.caption('Login untuk proyek cloud dan dashboard Admin. Analisis Cepat tersedia untuk tamu sesuai kebijakan Administrator.')
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
    guest_policy=load_access_policy(client,cloud_configured=True)
    signup_allowed=bool(guest_policy.registration_enabled)
    auth_tabs=st.tabs(['Masuk', 'Daftar akun'] if signup_allowed else ['Masuk'])
    signin=auth_tabs[0]
    with signin:
        persistent_ok = False
        try:
            persistent_ok = persistence_enabled(st.secrets)
        except ValueError:
            st.warning('Kunci pengingat login belum valid. Periksa auth_persistence.fernet_key.')
        with st.form('k4_login_form'):
            email=st.text_input('Email',autocomplete='email')
            password=st.text_input('Password',type='password')
            remember = st.checkbox('Ingat saya selama 7 hari (hanya perangkat pribadi)',
                                   value=False, disabled=not persistent_ok)
            if not persistent_ok:
                st.caption('Opsi Ingat saya belum aktif. Admin perlu mengatur kunci enkripsi di Streamlit Secrets.')
            submitted=st.form_submit_button('Masuk',type='primary',use_container_width=True)
        if submitted:
            try:
                response=sign_in(client,email,password)
                if response.user and response.session:
                    # written on the NEXT rerun by signed_user, after cookie bridge mounts
                    st.session_state['k4_remember_enabled'] = bool(remember and persistent_ok)
                    st.success('Login berhasil. Buka Proyek Saya untuk menyimpan data.')
                    st.rerun()
                else: st.warning('Email atau password belum aktif. Periksa email verifikasi.')
            except Exception:
                st.error('Login gagal. Periksa kredensial atau verifikasi email.')
    if signup_allowed:
        signup=auth_tabs[1]
        with signup:
          with st.form('k4_signup_form'):
              new_email=st.text_input('Email baru',autocomplete='email')
              new_password=st.text_input('Password baru (minimal 8 karakter)',type='password')
              confirm_password=st.text_input('Ulangi password',type='password')
              signup_clicked=st.form_submit_button('Daftar',use_container_width=True)
          if signup_clicked:
              if new_password!=confirm_password:
                  st.error('Konfirmasi password berbeda.')
              else:
                  try:
                      res=sign_up(client,new_email,new_password)
                      st.success('Permintaan pendaftaran diterima. Periksa email untuk konfirmasi jika diminta oleh Supabase.')
                  except Exception:
                      st.error('Pendaftaran belum berhasil. Cek format email atau coba lagi.')
    if not signup_allowed:
        st.info('Pendaftaran baru sedang ditutup oleh administrator. Akun yang sudah ada tetap dapat masuk.')
    st.caption('Kredensial diproses oleh Supabase Auth. Aplikasi ini tidak menyimpan password di CSV atau GitHub.')
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
    st.warning('Akun menunggu persetujuan administrator. Analisis Cepat tetap bisa dipakai sesuai izin tamu.')
elif status == 'suspended':
    st.error('Akun ditangguhkan. Hubungi administrator. Proyek cloud tidak dapat dibuka.')
if st.button('Keluar dari akun',type='secondary'):
    logout(); st.rerun()

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
