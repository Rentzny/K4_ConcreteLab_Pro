"""v8 front door: responsive desktop/mobile auth or continue-as-guest."""
import streamlit as st
from concretelab.auth_views import render_auth_forms
from concretelab.cloud_ui import cloud_client
from concretelab.permissions import load_access_policy
from concretelab.cloud import get_supabase_settings

st.markdown('''
<style>
.k4v8-kicker {font-size:.72rem;letter-spacing:.14em;color:#4D7976;font-weight:750;margin-bottom:1.2rem;}
.k4v8-headline {font-size:clamp(2.45rem,4.8vw,4.5rem);line-height:1.09;letter-spacing:-.055em;font-weight:750;color:#253B44;}
.k4v8-headline span {color:#508279;}
.k4v8-subtitle {font-size:1rem;color:#607780;line-height:1.8;max-width:490px;margin-top:1.1rem;}
.k4v8-feature {border-left:2px solid #84A7A2;padding-left:15px;color:#506971;font-size:.88rem;line-height:1.65;margin-top:1.7rem;}
.st-key-k4_v8_auth_card {background-color:#FFFFFF;border-radius:18px;border:1px solid #DDE8E8;box-shadow:0 12px 40px rgba(24,63,70,.055);}
.st-key-k4_v8_auth_card [data-testid="stForm"] {border:0;padding:0;}
@media(max-width:680px){
  .k4v8-headline {font-size:2rem;}
  .k4v8-subtitle {font-size:.92rem;line-height:1.65;margin-top:.5rem;}
  .k4v8-feature {display:none;}
  .st-key-k4_v8_auth_card {box-shadow:none;}
  div[data-testid="stHorizontalBlock"] {gap:1rem;}
}
</style>
''',unsafe_allow_html=True)

left,right=st.columns([1.02,.98],gap='large',vertical_alignment='center')
with left:
    st.markdown('<div class="k4v8-kicker">K4 CONCRETELAB PRO / v8.0</div>',unsafe_allow_html=True)
    st.markdown('<div class="k4v8-headline">Satu tempat untuk<br><span>data mutu beton.</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="k4v8-subtitle">Masuk untuk mengelola proyek dan laporan. Daftar akun baru secara mandiri, atau langsung lanjutkan analisis tanpa akun.</div>',unsafe_allow_html=True)
    st.markdown('<div class="k4v8-feature"><strong>Analisis CSV</strong> · Grafik interaktif · Pelacakan sampel · Laporan PDF</div>',unsafe_allow_html=True)
with right:
    try:
        client=cloud_client()
        configured=get_supabase_settings(st.secrets) is not None
        policy=load_access_policy(client,cloud_configured=configured)
    except Exception:
        client=None
        policy=load_access_policy(None,cloud_configured=True)
    render_auth_forms(client,registration_enabled=policy.registration_enabled,gateway=True)

st.divider()
st.caption('ConcreteLab Pro · PjBL Teknik Sipil · Analisis edukatif, bukan sertifikat laboratorium.')
