"""ConcreteLab Pro v5.5 — analisis tamu + workspace berbasis Supabase RLS."""
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(
    page_title="ConcreteLab Pro | Analisis Kuat Tekan Beton",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Desain minimal: tidak memakai animasi, efek neon, parallax, atau overlay kustom.
st.markdown("""
<style>
.stApp {background-color:#F8FAFB;color:#243845;}
.block-container {max-width:1180px;padding-top:1.6rem;padding-bottom:3rem;}
h1, h2, h3 {color:#243845;font-weight:620;letter-spacing:-.025em;}
section[data-testid="stSidebar"] {background:#FFFFFF;border-right:1px solid #E7ECEF;}
div[data-testid="stMetric"] {background:#FFFFFF;border:1px solid #E5EBEF;border-radius:9px;padding:13px;}
div[data-testid="stAlert"] {border-radius:9px;}
.stButton > button[kind="primary"] {background:#355C68;border-color:#355C68;}
.stButton > button {border-radius:8px;}
[data-testid="stDownloadButton"] button {border-radius:8px;}
.k4-tag {color:#667A84;font-size:.79rem;font-weight:650;letter-spacing:.09em;}
.k4-note {color:#5D707A;font-size:.94rem;line-height:1.75;max-width:690px;}
.k4-card {padding:20px;background:#FFFFFF;border:1px solid #E5EBEF;border-radius:11px;min-height:150px;}
.k4-card .top {font-size:.79rem;color:#657C86;margin-bottom:15px;}
.k4-card h4 {margin:0 0 8px;color:#223D48;font-size:1.05rem;font-weight:650;}
.k4-card p {margin:0;color:#5D707A;font-size:.91rem;line-height:1.6;}
@media (max-width: 640px) {
  .block-container {padding:1rem .9rem 2rem;}
  h1 {font-size:1.8rem !important;}
  .k4-card {padding:16px;min-height:auto;}
}
</style>
""", unsafe_allow_html=True)

# QR publik: hanya metadata status yang disetujui, bukan data pribadi / dokumen asli.
raw_token = st.query_params.get('verify')
if raw_token:
    from concretelab.cloud import get_supabase_settings, new_client, verify_report
    st.title('Verifikasi Laporan')
    st.caption('Pemeriksaan metadata laporan ConcreteLab Pro yang berstatus disetujui.')
    try:
        settings=get_supabase_settings(st.secrets)
        if settings is None:
            st.warning('Layanan verifikasi belum dikonfigurasi.')
        else:
            # Public query uses anon key with narrow SECURITY DEFINER SQL RPC.
            info=verify_report(new_client(*settings),raw_token)
            if info:
                st.success('Metadata laporan ditemukan dan berstatus disetujui.')
                st.write('**ID laporan:**',info['report_id'])
                st.write('**Revisi:**',info['report_revision'])
                st.write('**Kode proyek:**',info['project_code'] or '—')
                st.write('**Waktu persetujuan:**',info['approved_at'])
                st.code(info['csv_fingerprint'],language=None)
                st.caption('Hash SHA-256 merujuk pada snapshot CSV; tidak membuktikan keaslian hasil laboratorium.')
            else:
                st.warning('Kode tidak ditemukan, belum disetujui, atau tidak berlaku.')
    except Exception:
        st.error('Layanan verifikasi belum tersedia. Periksa koneksi Supabase.')
    st.info('Verifikasi ini bukan tanda tangan digital, sertifikat uji, atau persetujuan teknis resmi.')
    st.stop()

# Tiga menu utama tetap ada; Akun dan Proyek Saya menjadi fitur tambahan.
home = st.Page("app_pages/home.py", title="Beranda", icon="🏠", url_path="", default=True)
service = st.Page("app_pages/service.py", title="Service", icon="🧪", url_path="service")
about = st.Page("app_pages/about.py", title="About", icon="ℹ️", url_path="about")
workspace = st.Page("app_pages/workspace.py", title="Proyek Saya", icon="📁", url_path="projects")
account = st.Page("app_pages/account.py", title="Akun", icon="👤", url_path="account")
nav = st.navigation([home, service, about, workspace, account], position="top")
nav.run()
