"""Beranda minimal untuk ConcreteLab Pro."""
import streamlit as st

st.markdown('<div class="k4-tag">CONCRETE TESTING & ANALYTICS</div>', unsafe_allow_html=True)
st.write("")
st.title("Analisis kuat tekan beton, lebih sederhana.")
st.markdown(
    '<p class="k4-note">Unggah data pengujian, periksa hasil perhitungan, '
    'lihat analisis statistik, dan buat laporan PDF otomatis dalam satu tempat. '
    'Dirancang untuk pembelajaran dan eksplorasi data teknik sipil.</p>',
    unsafe_allow_html=True,
)
st.write("")
left, right = st.columns([1.05, 2.2], gap="small")
with left:
    if st.button("Mulai Analisis", type="primary", use_container_width=True):
        st.switch_page("app_pages/service.py")
with right:
    st.page_link("app_pages/about.py", label="Tentang aplikasi", icon="ℹ️")
st.write("")
st.divider()
st.write("")

features = [
    ("01", "Validasi CSV", "Periksa kelengkapan kolom dan indikasi data bermasalah sebelum analisis."),
    ("02", "Analisis statistik", "Hitung kuat tekan, ringkasan campuran, evaluasi simulasi, dan grafik."),
    ("03", "Laporan & arsip", "Unduh PDF, ZIP hasil serta arsip proyek yang dapat dibuka kembali."),
]
cols = st.columns(3, gap="medium")
for col, (no, title, description) in zip(cols, features):
    with col:
        st.markdown(
            f'<div class="k4-card"><div class="top">{no} / FITUR</div>'
            f'<h4>{title}</h4><p>{description}</p></div>',
            unsafe_allow_html=True,
        )

st.write("")
st.write("")
st.subheader("Cara menggunakan")
st.markdown("**Siapkan CSV → Buka Service → Unggah data → Periksa hasil → Unduh laporan.**")
st.caption("Tidak ada data contoh yang dianalisis otomatis saat homepage dibuka.")
st.divider()
st.caption("K4 ConcreteLab Pro · Proyek PjBL Teknik Sipil · Hasil simulasi tidak menggantikan pemeriksaan laboratorium.")
