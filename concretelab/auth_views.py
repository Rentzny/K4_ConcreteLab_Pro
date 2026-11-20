"""v8 responsive sign-in, self-registration and guest entry.

No custom HTML forms or JS, no password persistence in app state. Each
Streamlit session uses its own Supabase Auth client from cloud_ui.
"""
from __future__ import annotations
import streamlit as st
from .cloud import sign_in, sign_up
from .registration import check_registration
from .persistent_session import persistence_enabled

CHOICE_KEY = 'k4_v8_auth_choice'


def _choose(mode: str):
    st.session_state[CHOICE_KEY] = mode


def _continue_as_guest(*, gateway: bool):
    st.session_state['k4_guest_continue'] = True
    if gateway:
        st.rerun()
    else:
        st.switch_page('app_pages/home.py')


def render_auth_forms(client, *, registration_enabled: bool, gateway: bool):
    """Render native Streamlit widgets on desktop and phone-sized viewports."""
    options=['Masuk','Daftar akun'] if registration_enabled and client is not None else ['Masuk']
    current=st.session_state.get(CHOICE_KEY)
    if current not in options:
        st.session_state[CHOICE_KEY]='Masuk'

    with st.container(border=True, key='k4_v8_auth_card'):
        st.markdown('#### Akses akun')
        st.caption('Gunakan akun untuk menyimpan proyek dan mengelola data di cloud.')
        mode=st.segmented_control('Pilih metode akses', options=options,
                                  key=CHOICE_KEY, selection_mode='single',
                                  label_visibility='collapsed')
        if mode == 'Daftar akun' and registration_enabled and client is not None:
            st.markdown('##### Buat akun baru')
            with st.form('k4_v8_signup_form', clear_on_submit=False):
                new_email=st.text_input('Alamat email',autocomplete='email',key='k4_v8_register_email')
                new_password=st.text_input('Buat password (minimal 8 karakter)',type='password',
                                           key='k4_v8_register_password',max_chars=128)
                confirm_password=st.text_input('Konfirmasi password',type='password',
                                               key='k4_v8_register_confirm',max_chars=128)
                accepted=st.checkbox('Saya memahami bahwa data proyek milik saya hanya dapat diakses akun yang berwenang.',
                                     key='k4_v8_register_ack')
                created=st.form_submit_button('Buat Akun',type='primary',use_container_width=True)
            if created:
                valid,message=check_registration(new_email,new_password,confirm_password)
                if not valid:
                    st.error(message)
                elif not accepted:
                    st.warning('Centang konfirmasi penggunaan akun terlebih dahulu.')
                else:
                    try:
                        response=sign_up(client,new_email,new_password)
                        if getattr(response,'session',None):
                            st.success('Akun berhasil dibuat dan login aktif. Akses pengguna biasa langsung tersedia.')
                            st.session_state['k4_guest_continue']=False
                            st.rerun()
                        else:
                            st.success('Pendaftaran diterima. Jika Supabase meminta verifikasi email, buka tautan konfirmasi terlebih dahulu. Setelah verifikasi, akun baru otomatis aktif tanpa persetujuan Admin.')
                    except Exception:
                        # Auth intentionally avoids leaking whether an email exists.
                        st.error('Pendaftaran tidak berhasil. Periksa email, password, atau kebijakan pendaftaran.')
            st.button('Sudah punya akun? Masuk', key='k4_v8_switch_signin',
                      on_click=_choose,args=('Masuk',),use_container_width=True)
        else:
            st.markdown('##### Sudah punya akun? Masuk')
            if client is None:
                st.warning('Login belum tersedia. Administrator perlu mengatur koneksi Supabase. Mode tamu masih dapat dipilih.')
            else:
                try:
                    can_remember = persistence_enabled(st.secrets)
                except ValueError:
                    can_remember = False
                    st.warning('Kunci Ingat Saya tidak valid. Periksa Streamlit Secrets.')
                with st.form('k4_v8_login_form'):
                    email=st.text_input('Alamat email',autocomplete='email',key='k4_v8_login_email')
                    password=st.text_input('Password',type='password',key='k4_v8_login_password')
                    remember=st.checkbox('Ingat saya selama 7 hari (perangkat pribadi)',
                                         value=False,disabled=not can_remember)
                    clicked=st.form_submit_button('Masuk',type='primary',use_container_width=True)
                if clicked:
                    try:
                        response=sign_in(client,email,password)
                        if getattr(response,'user',None) and getattr(response,'session',None):
                            st.session_state['k4_remember_enabled']=bool(remember and can_remember)
                            st.session_state['k4_guest_continue']=False
                            st.rerun()
                        else:
                            st.error('Login belum berhasil. Periksa email, password, atau konfirmasi email.')
                    except Exception:
                        st.error('Login gagal. Periksa kredensial atau status konfirmasi email.')
                if not can_remember:
                    st.caption('Fitur Ingat Saya belum aktif. Admin dapat mengaturnya di Streamlit Secrets.')
            if registration_enabled and client is not None:
                st.button('Belum punya akun? Daftar sekarang',key='k4_v8_switch_signup',
                          on_click=_choose,args=('Daftar akun',),use_container_width=True)
            elif client is not None:
                st.caption('Pendaftaran akun baru sedang dinonaktifkan oleh administrator.')

        st.divider()
        if st.button('Lanjutkan sebagai Tamu',key='k4_v8_guest_continue',use_container_width=True):
            _continue_as_guest(gateway=gateway)
        st.caption('Tamu tidak perlu membuat akun. Fitur yang tersedia mengikuti pengaturan Administrator; proyek privat tetap terlindungi.')
