"""Account page: Supabase email/password authentication + admin role management."""
import streamlit as st
from concretelab.cloud_ui import cloud_client, signed_user, logout, cloud_notice
from concretelab.cloud import sign_in, sign_up, get_profile

st.title('Akun & Akses')
st.caption('Mode tamu tetap dapat menggunakan Service tanpa login. Login diperlukan hanya untuk proyek cloud.')
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
    signin, signup = st.tabs(['Masuk', 'Daftar akun'])
    with signin:
        with st.form('k4_login_form'):
            email=st.text_input('Email',autocomplete='email')
            password=st.text_input('Password',type='password')
            submitted=st.form_submit_button('Masuk',type='primary',use_container_width=True)
        if submitted:
            try:
                response=sign_in(client,email,password)
                if response.user and response.session:
                    st.success('Login berhasil. Buka Proyek Saya untuk menyimpan data.')
                    st.rerun()
                else: st.warning('Email atau password belum aktif. Periksa email verifikasi.')
            except Exception:
                st.error('Login gagal. Periksa kredensial atau verifikasi email.')
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
    st.caption('Kredensial diproses oleh Supabase Auth. Aplikasi ini tidak menyimpan password di CSV atau GitHub.')
    st.stop()

uid=str(user.id)
profile=None
try: profile=get_profile(client,uid)
except Exception: st.warning('Profil belum tersedia. Pastikan schema_v55.sql sudah dijalankan.')
role=(profile or {}).get('global_role','user')
st.success('Kamu sudah login.')
st.write('**Email:**',getattr(user,'email','—'))
st.code(uid,language=None)
st.caption('ID pengguna ini digunakan untuk menambahkan anggota proyek. Bagikan hanya kepada pemilik proyek yang tepercaya.')
st.write('**Peran global:**',role)
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

if role=='admin':
    st.divider()
    st.subheader('Administrasi Pengguna')
    st.caption('Hak Admin hanya bisa diberikan oleh admin lain atau melalui SQL Editor pemilik Supabase. '
               'Pengguna tidak dapat menaikkan perannya sendiri.')
    try:
        people=client.table('k4_profiles').select('user_id,email,display_name,global_role').order('created_at',desc=True).limit(100).execute().data or []
        st.dataframe(people,hide_index=True,use_container_width=True)
        with st.form('admin_role'):
            target_uid=st.text_input('UUID pengguna yang akan diubah')
            target_role=st.selectbox('Peran global',('user','admin'))
            confirm=st.checkbox('Saya sudah memeriksa identitas pengguna')
            change=st.form_submit_button('Ubah peran')
        if change:
            if not confirm or not target_uid.strip():
                st.error('Konfirmasi identitas pengguna sebelum mengubah peran.')
            else:
                try:
                    client.rpc('k4_admin_set_role',{'p_user':target_uid.strip(),'p_role':target_role}).execute()
                    st.success('Peran telah diperbarui berdasarkan izin server.')
                except Exception:
                    st.error('Gagal mengubah peran. Hanya admin sah yang boleh melakukannya.')
    except Exception:
        st.error('Daftar pengguna tidak bisa dimuat. Periksa schema dan izin RLS.')
