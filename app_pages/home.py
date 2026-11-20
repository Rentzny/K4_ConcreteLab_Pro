"""Beranda v3.1 — Calm Engineering: statis, responsif, dan tanpa data contoh otomatis."""
import streamlit as st

# Gaya hanya diterapkan di beranda agar halaman Service v3.0 tidak berubah.
st.markdown("""
<style>
.k4h-shell { color:#253B44; }
.k4h-kicker {display:inline-flex;align-items:center;gap:10px;color:#516D75;font-size:.75rem;letter-spacing:.13em;font-weight:700;margin-bottom:24px;}
.k4h-kicker-dot {width:7px;height:7px;background:#648982;border-radius:50%;display:inline-block;}
.k4h-title {font-weight:730;font-size:clamp(2.3rem,4.45vw,4.65rem);letter-spacing:-.065em;line-height:1.085;color:#233842;margin:0 0 22px;}
.k4h-title span {color:#63827E;font-weight:600;}
.k4h-lead {font-size:1.02rem;line-height:1.85;color:#60737B;max-width:580px;margin:0;}
.k4h-toprule {border-top:1px solid #DCE5E7;margin:9px 0 31px;}
.k4h-hero-note {color:#84939A;font-size:.78rem;letter-spacing:.02em;padding-top:13px;}
.k4h-visual {position:relative;isolation:isolate;overflow:hidden;background:#F2F6F5;border:1px solid #DDE7E5;border-radius:19px;padding:26px;min-height:346px;box-shadow:0 16px 30px rgba(41,71,72,.035);}
.k4h-visual:before {content:"";position:absolute;inset:0;background-image:linear-gradient(#DCE6E5 1px,transparent 1px),linear-gradient(90deg,#DCE6E5 1px,transparent 1px);background-size:33px 33px;opacity:.30;z-index:-1;}
.k4h-visual-head {display:flex;justify-content:space-between;align-items:center;font-size:.7rem;font-weight:700;letter-spacing:.1em;color:#667C80;}
.k4h-visual-main {display:flex;align-items:center;justify-content:center;gap:38px;min-height:215px;}
.k4h-specimen {height:142px;width:105px;position:relative;background:linear-gradient(90deg,#C9D8D8 0%,#EDF3F1 55%,#BED0CF 100%);border:1px solid #A6BAB8;border-radius:0 0 50px 50px / 0 0 17px 17px;box-shadow:17px 19px 35px rgba(86,110,112,.10);margin-top:13px;}
.k4h-specimen:before {content:"";position:absolute;top:-15px;left:-1px;width:105px;height:30px;border-radius:50%;background:linear-gradient(110deg,#E7F0EE,#BCCFCD);border:1px solid #A6BAB8;}
.k4h-specimen:after {content:"";position:absolute;bottom:-2px;left:4px;width:95px;height:21px;border-radius:50%;border-bottom:1px solid #95ADAA;opacity:.65;}
.k4h-formula {margin-left:11px;padding:14px 0 10px 16px;border-left:1px solid #BDCFCD;white-space:nowrap;}
.k4h-formula-label {font-size:.68rem;color:#77898B;letter-spacing:.12em;font-weight:700;}
.k4h-formula-value {font-size:1.7rem;color:#365C5B;letter-spacing:-.04em;font-weight:650;padding-top:7px;}
.k4h-formula-note {font-size:.74rem;color:#76898C;margin-top:6px;}
.k4h-flowline {display:flex;align-items:center;gap:10px;border-top:1px solid #D7E2DF;padding-top:17px;flex-wrap:wrap;}
.k4h-step-pill {font-size:.72rem;color:#526E72;border:1px solid #CCDCD8;border-radius:999px;background:rgba(255,255,255,.7);padding:7px 11px;font-weight:650;}
.k4h-flow-arrow {font-size:.83rem;color:#9EAFAD;}
.k4h-section-meta {font-size:.72rem;color:#7B9094;letter-spacing:.11em;font-weight:750;}
.k4h-section-head {font-size:clamp(1.45rem,2.1vw,2rem);letter-spacing:-.035em;line-height:1.3;color:#243D46;font-weight:700;margin:11px 0 7px;}
.k4h-section-sub {color:#73838A;font-size:.94rem;line-height:1.65;margin-bottom:20px;}
.k4h-feature {background:#fff;border:1px solid #E2E9E9;border-radius:14px;padding:23px 22px 20px;min-height:171px;}
.k4h-feature-id {color:#78908D;font-size:.73rem;font-weight:760;letter-spacing:.12em;margin-bottom:23px;}
.k4h-feature-name {color:#263F48;font-size:1.04rem;font-weight:690;letter-spacing:-.016em;margin-bottom:9px;}
.k4h-feature-text {color:#6F8188;font-size:.88rem;line-height:1.7;}
.k4h-bottom {border-top:1px solid #DDE6E8;margin-top:22px;padding:21px 0;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;}
.k4h-bottom span {color:#84939A;font-size:.78rem;}
/* Hanya area homepage; perubahan tidak memengaruhi dashboard Service. */
@media(max-width:900px) {
 .k4h-title {font-size:clamp(2.2rem,6vw,3.3rem);}
 .k4h-visual {min-height:300px;margin-top:12px;}
 .k4h-visual-main {min-height:185px;gap:16px;}
 .k4h-feature {min-height:auto;}
}
@media(max-width:600px) {
 .k4h-kicker {font-size:.68rem;letter-spacing:.095em;margin-bottom:14px;}
 .k4h-title {font-size:2.25rem;}
 .k4h-lead {font-size:.96rem;line-height:1.7;}
 .k4h-visual {padding:19px;min-height:276px;border-radius:13px;}
 .k4h-visual-main {min-height:177px;gap:5px;}
 .k4h-specimen {transform:scale(.77);transform-origin:center center;}
 .k4h-formula {margin-left:0;padding-left:11px;}
 .k4h-formula-value {font-size:1.35rem;}
 .k4h-step-pill {font-size:.64rem;padding:6px 8px;}
 .k4h-flowline {gap:7px;}
 .k4h-section-head {font-size:1.6rem;}
 .k4h-feature {padding:20px;}
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="k4h-shell"><div class="k4h-toprule"></div></div>', unsafe_allow_html=True)
left, right = st.columns([1.12, .88], gap="large", vertical_alignment="center")

with left:
    st.markdown("""
    <div class="k4h-shell">
      <div class="k4h-kicker"><span class="k4h-kicker-dot"></span> K4 CONCRETELAB <span style="opacity:.35">/</span> ENGINEERING TOOLS</div>
      <div class="k4h-title">Data beton,<br><span>lebih mudah dibaca.</span></div>
      <p class="k4h-lead">Dari data pengujian CSV hingga analisis statistik dan laporan PDF. Semua dalam satu alur yang sederhana, terstruktur, dan mudah ditelusuri.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    a, b = st.columns([1.06, .94], gap="small")
    with a:
        if st.button("Mulai analisis  →", type="primary", use_container_width=True, key="k4h_start"):
            st.switch_page("app_pages/service.py")
    with b:
        st.page_link("app_pages/about.py", label="Tentang aplikasi", icon="ℹ️", use_container_width=True)
    st.markdown('<div class="k4h-hero-note">Tidak ada data ditampilkan sebelum kamu mengunggah CSV.</div>', unsafe_allow_html=True)

with right:
    st.markdown("""
    <div class="k4h-visual" role="img" aria-label="Ilustrasi silinder beton dan alur pengolahan CSV menjadi PDF, bukan hasil uji nyata">
      <div class="k4h-visual-head"><span>SKEMA PENGUJIAN</span><span>FIG. 01 / K4</span></div>
      <div class="k4h-visual-main">
        <div class="k4h-specimen"></div>
        <div class="k4h-formula"><div class="k4h-formula-label">DASAR PERHITUNGAN</div><div class="k4h-formula-value">f′c = P / A</div><div class="k4h-formula-note">Beban / luas penampang</div></div>
      </div>
      <div class="k4h-flowline"><span class="k4h-step-pill">CSV</span><span class="k4h-flow-arrow">→</span><span class="k4h-step-pill">Analisis</span><span class="k4h-flow-arrow">→</span><span class="k4h-step-pill">PDF</span></div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.write("")
st.markdown("""
<div class="k4h-shell">
  <div class="k4h-section-meta">APA YANG DAPAT DILAKUKAN?</div>
  <div class="k4h-section-head">Satu alur kerja. Hasil yang lebih tertata.</div>
  <div class="k4h-section-sub">Dirancang untuk membantu pengolahan dan peninjauan data kuat tekan beton.</div>
</div>
""", unsafe_allow_html=True)

features = [
    ("01 / INPUT", "Validasi data", "Unggah dan periksa file CSV, termasuk data kosong atau nilai yang tidak sesuai."),
    ("02 / ANALISIS", "Statistik & evaluasi", "Tinjau hasil kuat tekan, perbandingan campuran, grafik, dan simulasi mutu."),
    ("03 / OUTPUT", "Laporan otomatis", "Unduh PDF, data hasil, serta arsip proyek yang dapat dibuka kembali."),
]
for col, (num, name, desc) in zip(st.columns(3, gap="medium"), features):
    with col:
        st.markdown(
            '<div class="k4h-feature"><div class="k4h-feature-id">'
            + num + '</div><div class="k4h-feature-name">' + name
            + '</div><div class="k4h-feature-text">' + desc + '</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("""
<div class="k4h-bottom">
  <span>K4 ConcreteLab Pro · PjBL Teknik Sipil · Universitas Janabadra</span>
  <span>Analisis edukatif — bukan sertifikasi laboratorium</span>
</div>
""", unsafe_allow_html=True)
