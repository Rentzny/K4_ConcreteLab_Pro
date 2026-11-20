"""Entrypoint ConcreteLab Pro v4.0 — navigasi minimalis tiga halaman."""
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

# Navigasi bawaan Streamlit: horizontal di desktop, responsif di layar kecil.
# Hindari hamburger HTML palsu yang tidak bisa mengubah halaman.
home = st.Page("app_pages/home.py", title="Beranda", icon="🏠", url_path="", default=True)
service = st.Page("app_pages/service.py", title="Service", icon="🧪", url_path="service")
about = st.Page("app_pages/about.py", title="About", icon="ℹ️", url_path="about")
nav = st.navigation([home, service, about], position="top")
nav.run()
