"""Halaman informasi proyek, tanpa klaim hasil pengujian nyata."""
import streamlit as st

st.markdown('<div class="k4-tag">ABOUT CONCRETELAB</div>', unsafe_allow_html=True)
st.title("Tentang ConcreteLab Pro")
st.markdown("""
ConcreteLab Pro merupakan aplikasi pengolahan hasil uji kuat tekan beton yang
berawal dari proyek **Project-Based Learning (PjBL) Bahasa Pemrograman**, Program
Studi S1 Teknik Sipil, Universitas Janabadra.

Aplikasi memanfaatkan Python untuk menghitung kuat tekan beton silinder,
mengelompokkan hasil pengujian, memeriksa kualitas input, menyajikan statistik
serta grafik, dan membuat laporan PDF dari data CSV.
""")
st.write("")
st.divider()
st.subheader("Teknologi")
st.write("Python · Streamlit · Supabase Auth · PostgreSQL · pandas · NumPy · Matplotlib · Plotly · ReportLab")
st.subheader("Versi 7.0")
st.write("Dashboard Administrator untuk akses tamu dan persetujuan akun, My Projects dengan Supabase, QR benda uji dan jadwal, serta laporan PDF profesional. Mode Ingat Saya bersifat opsional.")
st.subheader("Tujuan pengembangan")
st.write("Membantu pembelajaran pengolahan data teknik sipil yang terstruktur, dapat diperiksa, dan mudah dipresentasikan.")
st.subheader("Catatan penting")
st.info("Hasil evaluasi mutu bersifat simulasi numerik. Aplikasi tidak menerbitkan sertifikat laboratorium maupun keputusan penerimaan mutu beton di lapangan.")
st.caption("Data CSV tidak otomatis disimpan dalam database publik. Gunakan arsip proyek .k4proj.zip untuk menyimpan dan membuka kembali versi analisis. Riwayat SQLite hanya opsional untuk penggunaan lokal tepercaya.")
st.divider()
st.page_link("app_pages/service.py", label="Buka Service untuk mulai analisis", icon="🧪")
