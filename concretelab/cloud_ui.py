"""Streamlit session adapter; client never shared across users."""
import streamlit as st
from .cloud import get_supabase_settings,new_client,authenticated_user

CLIENT_KEY = 'k4_cloud_client_private_session'

def cloud_client():
    settings=get_supabase_settings(st.secrets)
    if settings is None: return None
    old=st.session_state.get(CLIENT_KEY)
    old_settings=st.session_state.get('k4_cloud_settings')
    if old is None or old_settings!=settings:
        st.session_state[CLIENT_KEY]=new_client(*settings)
        st.session_state['k4_cloud_settings']=settings
    return st.session_state[CLIENT_KEY]


def signed_user():
    client=cloud_client()
    return client,authenticated_user(client)


def logout():
    client=st.session_state.get(CLIENT_KEY)
    if client:
        try: client.auth.sign_out()
        except Exception: pass
    st.session_state.pop(CLIENT_KEY,None)
    # Do not keep previously opened cloud project or sensitive snapshots in session.
    # Privacy: a cloud snapshot loaded into Service must not remain in this browser
    # when another user signs in after logout.
    private_keys = {
        'k4_csv_upload','k4_uploaded_bytes','k4_uploaded_name','k4_saved_edit_csv',
        'k4_active_fingerprint','k4_imported_project','k4_archive_upload',
        'k4_archive_export','k4_archive_export_key','k4_restored_target',
        'k4_restored_name','k4_restored_owner'
    }
    for key in list(st.session_state):
        if key.startswith(('k4_workspace_', 'data_editor_', 'k4_tracking_')) or key in private_keys:
            st.session_state.pop(key,None)


def cloud_notice():
    st.info('Mode tamu tetap tersedia di Service. Untuk penyimpanan cloud, admin perlu '
            'memasang schema SQL dan mengisi Streamlit Secrets sesuai panduan v5.5.')
