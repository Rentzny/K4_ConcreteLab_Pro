"""K4 ConcreteLab Pro - antarmuka Streamlit, jalan lokal atau Streamlit Community Cloud."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import hashlib
import math
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from concretelab.engine import read_csv, analisis, evaluasi_tiga_uji, DataValidationError
from concretelab.plots import semua_grafik
from concretelab.reporting import buat_pdf, buat_zip

BASE_DIR = Path(__file__).resolve().parent
DEMO_FILE = BASE_DIR / "data" / "contoh_18_silinder.csv"
TEMPLATE_FILE = BASE_DIR / "data" / "template_kosong.csv"
PALETTE = ["#387C9E", "#138579", "#DE9952", "#8378B8", "#9B677A", "#65908F"]

st.set_page_config(page_title="K4 ConcreteLab Pro | Analisis Beton", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background: #F4F7FA; color: #15324C;}
.block-container {padding-top: 1.7rem; max-width: 1430px;}
section[data-testid="stSidebar"] {background: #F9FBFD; border-right:1px solid #DFE7EC;}
div[data-testid="stMetric"] {background: #FFF; border: 1px solid #E0E8ED; border-radius: 13px; padding: 14px 17px; box-shadow: 0 3px 9px rgba(20,49,71,.045);}
div[data-testid="stMetricLabel"] {color:#617586;}
div[data-testid="stMetricValue"] {color:#15324C;}
div[data-testid="stAlert"] {border-radius: 10px;}
h1, h2, h3 {color:#16354F;}
div[data-testid="stDownloadButton"] button {border:1px solid #9DC2D1; border-radius:10px;}
.k4-hero {padding:24px 30px; border-radius:18px; background:linear-gradient(112deg,#112F49 0%,#18546B 62%,#178477 100%);color:white;margin-bottom:18px;box-shadow:0 9px 18px rgba(15,47,68,.13)}
.k4-hero h1 {font-size:2.1rem; margin:5px 0;color:white;font-weight:740;}
.k4-hero p {margin:0;color:#D7E7EC;}
.k4-eyebrow {font-size:.73rem;letter-spacing:.18em;text-transform:uppercase;color:#96D2C7;font-weight:700;}
.k4-info {border-left:4px solid #178477; border-radius:6px; background:white; padding:12px 17px; color:#526B7E;margin:9px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="k4-hero"><div class="k4-eyebrow">ENGINEERING ANALYTICS / PJBL K4</div><h1>K4 ConcreteLab Pro</h1><p>Dashboard interaktif evaluasi kuat tekan beton • CSV → Analisis → Grafik → PDF otomatis</p></div>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Pengaturan Analisis")
    st.caption("Data pada aplikasi diproses dalam sesi, tanpa disimpan otomatis ke database server.")
    upload = st.file_uploader("Unggah data pengujian (.csv)", type=["csv"], help="Format kolom sesuai file contoh. Batas ukuran 10 MB.")
    if upload is not None:
        raw_bytes = upload.getvalue()
        source_name = upload.name
    else:
        raw_bytes = DEMO_FILE.read_bytes()
        source_name = "Data contoh 18 silinder (ilustratif)"
        st.info("Sedang memakai data contoh. Unggah CSV untuk menganalisis datamu sendiri.")
    if len(raw_bytes) > 10*1024*1024:
        st.error("CSV melebihi batas unggahan 10 MB.")
        st.stop()
    st.download_button("⬇️ Unduh CSV contoh",data=DEMO_FILE.read_bytes(),file_name="contoh_18_silinder.csv",mime="text/csv",use_container_width=True)
    st.download_button("⬇️ Unduh template kolom",data=TEMPLATE_FILE.read_bytes(),file_name="template_input.csv",mime="text/csv",use_container_width=True)
    st.divider()
    target = st.number_input("Mutu rencana f'c (MPa)",min_value=1.0,max_value=150.0,value=30.0,step=0.5,help="Parameter evaluasi, bukan kolom CSV.")
    nama_proyek = st.text_input("Nama proyek",value="PjBL K4 - Evaluasi Kuat Tekan Beton",max_chars=110)
    penanggung = st.text_input("Kelompok / penanggung jawab",value="Kelompok PjBL K4",max_chars=85)
    label_sumber = st.selectbox("Jenis sumber data",["Ilustratif / pembelajaran","Data uji lapangan (perlu verifikasi)"],index=0)
    st.caption("Status data lapangan tidak otomatis menjadikan simulasi ini bukti penerimaan beton.")
    st.divider()
    st.markdown("**Asumsi simulasi SNI**")
    st.caption("Dua silinder Ø150 mm per hasil uji, umur 28 hari, dan tiga hasil uji berurutan. Metode ±2SD hanya skrining outlier.")

try:
    raw_df = read_csv(raw_bytes)
except DataValidationError as exc:
    st.error("Tidak dapat membaca CSV.")
    for problem in exc.problems:
        st.write("•",problem)
    st.stop()

fingerprint = hashlib.md5(raw_bytes).hexdigest()[:10]
with st.expander("✏️ Tinjau atau edit data sebelum dihitung",expanded=False):
    st.caption("Ubah beban, diameter, campuran, atau tambah/hapus baris. Seluruh hasil di bawah otomatis mengikuti perubahan tabel ini. File asli di laptop tidak akan berubah.")
    edited_df = st.data_editor(raw_df, num_rows="dynamic", hide_index=True, use_container_width=True,
                               key=f"data_editor_{fingerprint}")
    st.caption("Untuk menyimpan perubahan, unduh hasil yang sudah divalidasi pada tab 'Unduh laporan'.")

try:
    h = analisis(edited_df,target,sumber=label_sumber+" | "+source_name,
                 raw_bytes=edited_df.to_csv(index=False).encode("utf-8"))
except DataValidationError as exc:
    st.error("⚠️ Perbaiki data sebelum melanjutkan analisis:")
    for p in exc.problems:
        st.markdown("- " + p)
    st.stop()
except Exception as exc:
    st.error("Proses analisis gagal. Periksa data dan jalankan ulang.")
    st.exception(exc)
    st.stop()

summary = h.ringkasan
if h.peringatan:
    with st.expander(f"⚠️ {len(h.peringatan)} catatan validasi / asumsi", expanded=True):
        for warning in h.peringatan:
            st.warning(warning)

# Analisis global tidak berubah saat pengguna sekadar memilih filter untuk tabel.
metrics = st.columns(5)
metrics[0].metric("Jumlah silinder",f"{summary['silinder']:,}")
metrics[1].metric("Campuran",summary["campuran"])
metrics[2].metric("Hasil pengujian",summary["jumlah_uji"])
metrics[3].metric("Silinder ≥ target",f"{summary['mencapai_target']} / {summary['silinder']}")
metrics[4].metric("Indikasi outlier",summary["indikasi_outlier"])

tabs = st.tabs(["📊 Ringkasan","📋 Data & statistik","🧪 Evaluasi mutu","📈 Visualisasi","📥 Unduh laporan","ℹ️ Metode"])

with tabs[0]:
    st.markdown("### Hasil utama pengujian")
    left,right=st.columns([1.3,1])
    with left:
        stat = h.statistik.copy()
        fig=go.Figure()
        fig.add_trace(go.Bar(x=stat["campuran"], y=stat["rata_rata"], name="Rata-rata",marker_color=[PALETTE[i%len(PALETTE)] for i in range(len(stat))],
                             error_y=dict(type="data",array=stat["simpangan_baku"].fillna(0),visible=True)))
        fig.add_hline(y=target, line_dash="dash",line_color="#C45D4A",annotation_text=f"Target {target:g} MPa")
        fig.update_layout(title="Rata-rata dan simpangan baku",xaxis_title="Campuran",yaxis_title="Kuat tekan (MPa)",
                          template="plotly_white",height=380,margin=dict(l=15,r=15,b=35,t=60))
        st.plotly_chart(fig,use_container_width=True)
    with right:
        st.markdown("#### Evaluasi simulasi")
        for _,r in h.evaluasi.iterrows():
            ico="🟢" if r["status"]=="Memenuhi simulasi" else "🔴" if r["status"]=="Belum memenuhi simulasi" else "🟠"
            st.write(f"{ico} **Campuran {r['campuran']}** — {r['status']}")
        st.divider()
        st.markdown("**Interpretasi awal**")
        best=h.statistik.loc[h.statistik["rata_rata"].idxmax()]
        st.write(f"Campuran **{best['campuran']}** memiliki rata-rata tertinggi: **{best['rata_rata']:.2f} MPa**.")
        st.caption("Status simulasi bukan persetujuan/penerimaan mutu beton nyata.")
    st.markdown("<div class='k4-info'>Seluruh angka dan grafik berasal dari CSV yang sedang digunakan. Ganti CSV atau edit tabel untuk melihat hasilnya berubah secara langsung.</div>",unsafe_allow_html=True)

with tabs[1]:
    st.markdown("### Data hasil perhitungan")
    mix_filter=st.multiselect("Filter campuran",options=h.statistik["campuran"].tolist(),default=h.statistik["campuran"].tolist(),key="mix_data")
    filtered=h.benda_uji[h.benda_uji["campuran"].isin(mix_filter)]
    st.dataframe(filtered, hide_index=True,use_container_width=True)
    st.markdown("### Statistik setiap campuran")
    st.dataframe(h.statistik.style.format({"rata_rata":"{:.2f}","simpangan_baku":"{:.2f}","minimum":"{:.2f}","maksimum":"{:.2f}","median":"{:.2f}","cv_persen":"{:.2f}%"}),hide_index=True,use_container_width=True)
    st.markdown("### Rekap pasangan pengujian")
    st.dataframe(h.rekap_uji,hide_index=True,use_container_width=True)
    st.caption("Standar deviasi menggunakan simpangan baku sampel (ddof=1). CV = SD/rata-rata × 100%. Statistik dihitung per SILINDER, bukan per pasangan pengujian.")

with tabs[2]:
    st.markdown("### Pemeriksaan numerik penerimaan - simulasi terbatas")
    st.warning("Hasil simulasi mengasumsikan silinder Ø150 mm, umur 28 hari, dua silinder per hasil uji, dan urutan uji valid. Tidak dapat digunakan sebagai sertifikat atau keputusan penerimaan beton.")
    lo=target-3.5 if target<=35 else 0.90*target
    ca,cb,cc=st.columns(3)
    ca.metric("Target f'c",f"{target:g} MPa")
    cb.metric("Batas hasil uji",f"{lo:.2f} MPa")
    cc.metric("Campuran memenuhi simulasi",str(summary["campuran_memenuhi_simulasi"]))
    st.dataframe(h.evaluasi,hide_index=True,use_container_width=True)
    st.markdown("#### Jendela tiga hasil uji")
    if h.jendela_tiga_uji.empty:
        st.info("Data kurang dari tiga hasil uji per campuran.")
    else:
        st.dataframe(h.jendela_tiga_uji,hide_index=True,use_container_width=True)
    st.markdown("#### Skenario jika target mutu berubah")
    gap=st.slider("Selisih dari target sekarang (MPa)",min_value=1,max_value=25,value=5,step=1)
    targets=sorted(set(round(x,2) for x in [max(1,target-gap),target,min(150,target+gap)]))
    sensitivity=[]
    for t in targets:
        e,_=evaluasi_tiga_uji(h.rekap_uji,t)
        for _,r in e.iterrows():
            sensitivity.append({"Target (MPa)":t,"Campuran":r["campuran"],"Status":r["status"],"Min rata 3 uji (MPa)":r["rata_3_terendah_MPa"]})
    st.dataframe(pd.DataFrame(sensitivity),hide_index=True,use_container_width=True)
    st.caption("Perbandingan skenario tidak mengubah hasil utama atau PDF, kecuali parameter target di sidebar diubah.")

with tabs[3]:
    st.markdown("### Grafik interaktif")
    sub=st.columns(2)
    with sub[0]:
        hist=px.histogram(h.benda_uji,x="kuat_tekan_MPa",color="campuran",nbins=18,
                          color_discrete_sequence=PALETTE,title="Distribusi kuat tekan silinder")
        hist.add_vline(x=target,line_dash="dash",line_color="#C45D4A")
        hist.update_layout(template="plotly_white",xaxis_title="Kuat tekan (MPa)",yaxis_title="Frekuensi",height=380)
        st.plotly_chart(hist,use_container_width=True)
    with sub[1]:
        box=px.box(h.benda_uji,x="campuran",y="kuat_tekan_MPa",points="all",color="campuran",
                    color_discrete_sequence=PALETTE,title="Sebaran kuat tekan per campuran")
        box.add_hline(y=target,line_dash="dash",line_color="#C45D4A")
        box.update_layout(template="plotly_white",xaxis_title="Campuran",yaxis_title="Kuat tekan (MPa)",height=380)
        st.plotly_chart(box,use_container_width=True)
    st.markdown("### Tren hasil uji")
    seq=h.rekap_uji.copy()
    seq["urutan_plot"]=seq.groupby("campuran").cumcount()+1
    line=px.line(seq,x="urutan_plot",y="kuat_tekan_uji_MPa",color="campuran",markers=True,
                  hover_data=["id_pengujian"], color_discrete_sequence=PALETTE,
                  title="Rata-rata per pasangan uji (sesuai urutan)")
    line.add_hline(y=target,line_dash="dash",line_color="#C45D4A")
    line.update_layout(template="plotly_white",xaxis_title="Urutan hasil uji",yaxis_title="Kuat tekan uji (MPa)",height=360)
    st.plotly_chart(line,use_container_width=True)
    st.caption("Gambar PNG keempat grafik tersedia untuk diunduh dalam paket ZIP. Grafik dari data ilustratif tidak boleh diberi label pengamatan nyata.")

with tabs[4]:
    st.markdown("### Ekspor hasil analisis saat ini")
    st.write("Seluruh file di bawah dihasilkan dari tabel yang sedang digunakan, termasuk perubahan lewat editor CSV.")
    with st.spinner("Menyiapkan grafik, PDF dan paket hasil..."):
        graphics=semua_grafik(h)
        pdf=buat_pdf(h,nama_proyek=nama_proyek,penanggung_jawab=penanggung,grafik=graphics)
        bundle=buat_zip(h,pdf,graphics,nama_proyek=nama_proyek)
    dl1,dl2=st.columns(2)
    with dl1:
        st.download_button("📄 Unduh laporan PDF otomatis",data=pdf,file_name="Laporan_Otomatis_K4_Beton.pdf",mime="application/pdf",use_container_width=True,type="primary")
        st.caption("Laporan PDF multi-halaman berisi data terbaru, 2 grafik, rekap statistik, evaluasi mutu dan tabel benda uji.")
    with dl2:
        st.download_button("📦 Unduh SEMUA hasil (.zip)",data=bundle,file_name="Paket_Lengkap_Hasil_K4_Beton.zip",mime="application/zip",use_container_width=True,type="primary")
        st.caption("ZIP: CSV input, CSV hasil, evaluasi, empat PNG, PDF serta metadata dan hash input.")
    st.divider()
    colA,colB,colC=st.columns(3)
    colA.download_button("CSV kuat tekan",data=h.benda_uji.to_csv(index=False).encode("utf-8-sig"),file_name="hasil_kuat_tekan.csv",mime="text/csv",use_container_width=True)
    colB.download_button("CSV statistik",data=h.statistik.to_csv(index=False).encode("utf-8-sig"),file_name="statistik_campuran.csv",mime="text/csv",use_container_width=True)
    colC.download_button("CSV evaluasi",data=h.evaluasi.to_csv(index=False).encode("utf-8-sig"),file_name="evaluasi_simulasi.csv",mime="text/csv",use_container_width=True)
    st.success(f"Laporan berhasil diproses. Input hash: {h.hash_sumber[:14]}... | {summary['silinder']} benda uji | {summary['campuran']} campuran")

with tabs[5]:
    st.markdown("### Cara kerja mesin analisis")
    st.markdown("""
**Rumus dasar**  
Luas penampang silinder: `A = π × d² / 4` dalam mm².  
Kuat tekan: `fc = (P_kN × 1000) / A` dalam MPa.

**Alur data**  
Input CSV → Validasi kolom & nilai → `BendaUji` → Rekap pasangan pengujian → Statistik per campuran → Screening outlier → Simulasi mutu → Grafik & PDF.

**Simulasi kriteria numerik**  
- Setiap jendela tiga hasil uji berurutan mempunyai rata-rata ≥ f'c.
- Untuk f'c ≤ 35 MPa: tidak ada satu hasil uji di bawah f'c − 3,5 MPa.
- Untuk f'c > 35 MPa: tidak ada satu hasil uji di bawah 0,90 × f'c.
- Program hanya memberikan status evaluasi jika konfigurasi data memenuhi asumsi 2 silinder berdiameter 150 mm, umur 28 hari, dan minimal 3 hasil uji per campuran.

**Pemeriksaan outlier**  
Nilai di luar rata-rata ± 2 simpangan baku sampel diberi tanda *indikasi* jika n ≥ 5; data tidak otomatis dihapus.

**Batasan**  
- Semua data contoh adalah ilustratif, bukan data nyata.
- Evaluasi standar bersifat simulasi pembelajaran, **bukan penerimaan mutu beton lapangan**.
- Urutan pengujian sebaiknya dinyatakan dengan kolom opsional `urutan_uji`.
- Tidak ada model machine learning; 18 sampel ilustratif tidak cukup untuk prediksi yang dapat dipercaya.
- Uji laboratorium nyata memerlukan informasi metode, umur, pengambilan sampel, dimensi, kalibrasi, dan kepatuhan standar yang berlaku.
""")
    st.markdown("#### Struktur kolom CSV")
    st.code("id_benda_uji,campuran,umur_hari,diameter_mm,beban_maksimum_kN,id_pengujian,urutan_uji\nU01,A,28,150,500,A01,1",language="csv")
    st.caption("Aplikasi lokal dapat diakses pada localhost. Untuk dipublikasikan, gunakan hosting dengan pengamanan dan kebijakan data yang sesuai.")

st.divider()
st.caption("K4 ConcreteLab Pro • PjBL Teknik Sipil • Data contoh ilustratif • Bukan sertifikat hasil uji laboratorium • Engine Python teruji")
