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
from concretelab.quality import audit_csv, audit_counts
from concretelab.scenarios import simulasi_beban, tabel_skenario, bandingkan_dua_analisis
from concretelab.advanced import statistik_lanjutan, sensitivitas_target, rekap_sensitivitas_target
from concretelab.reporting import buat_pdf, buat_zip

# Lokasi file ini app_pages/service.py; data/ berada satu tingkat di atas app_pages.
BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_FILE = BASE_DIR / "data" / "contoh_18_silinder.csv"
TEMPLATE_FILE = BASE_DIR / "data" / "template_kosong.csv"
PALETTE = ["#387C9E", "#138579", "#DE9952", "#8378B8", "#9B677A", "#65908F"]


@st.cache_data(show_spinner=False, max_entries=10)
def cache_berkas_laporan(csv_bytes: bytes, target: float, nama: str, penanggung: str, sumber: str):
    """Menghasilkan berkas dari CSV dan parameter; tidak memakai data hard-coded."""
    d = read_csv(csv_bytes)
    hasil = analisis(d, target, sumber=sumber, raw_bytes=csv_bytes)
    gambar = semua_grafik(hasil)
    pdf = buat_pdf(hasil, nama_proyek=nama, penanggung_jawab=penanggung, grafik=gambar)
    zip_bytes = buat_zip(hasil, pdf, gambar, nama_proyek=nama)
    return gambar, pdf, zip_bytes

# Halaman Service - fitur inti K4 ConcreteLab Pro v2 tetap dipertahankan.
st.title("Service")
st.caption("Analisis kuat tekan beton dari CSV • Validasi data • Grafik • Laporan PDF")
st.caption("Sesudah mengunggah CSV, pengaturan target mutu dapat dibuka melalui sidebar di sisi kiri.")
st.divider()


def simpan_csv_ke_sesi():
    """Simpan salinan bytes CSV di session_state supaya bertahan saat pindah halaman."""
    f = st.session_state.get("k4_csv_upload")
    if f is None:
        for key in ("k4_uploaded_bytes", "k4_uploaded_name", "k4_saved_edit_csv", "k4_active_fingerprint"):
            st.session_state.pop(key, None)
    else:
        st.session_state["k4_uploaded_bytes"] = f.getvalue()
        st.session_state["k4_uploaded_name"] = f.name
        st.session_state.pop("k4_saved_edit_csv", None)
        st.session_state.pop("k4_active_fingerprint", None)


def hapus_csv_sesi():
    """Reset data aktif; tidak menghapus file di komputer pengguna."""
    for key in ("k4_csv_upload", "k4_uploaded_bytes", "k4_uploaded_name", "k4_saved_edit_csv", "k4_active_fingerprint"):
        st.session_state.pop(key, None)

# Tempat upload dibuat sebagai dropzone asli Streamlit di area utama.
# Pada HP area ini otomatis mengikuti lebar layar; tidak memakai animasi atau HTML upload palsu.
st.markdown("""
<style>
[data-testid="stFileUploaderDropzone"] {
    background: #F7FAFB !important;
    border: 2px dashed #AFC3CC !important;
    border-radius: 14px !important;
    min-height: 152px !important;
    padding: 24px !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background-color: #355C68 !important;
    border-color: #355C68 !important;
    color: white !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background-color: #294955 !important;
    border-color: #294955 !important;
}
@media (max-width: 640px) {
    [data-testid="stFileUploaderDropzone"] {
        min-height: 130px !important;
        padding: 14px !important;
    }
}
</style>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("### Unggah CSV untuk mulai analisis")
    st.caption(
        "Tarik dan letakkan file CSV pada area di bawah, atau tekan Browse files. "
        "Format .csv, maksimal 10 MB."
    )
    upload = st.file_uploader(
        "Data pengujian beton (.csv)",
        type=["csv"],
        help="CSV harus menggunakan kolom sesuai template. Maksimum 10 MB.",
        key="k4_csv_upload",
        on_change=simpan_csv_ke_sesi,
        label_visibility="collapsed",
    )
    if st.session_state.get("k4_uploaded_bytes") is None:
        st.caption("Belum ada data yang dimasukkan. Grafik, statistik, dan PDF belum ditampilkan.")
    else:
        active_name = st.session_state.get("k4_uploaded_name", "data.csv")
        size_kb = len(st.session_state["k4_uploaded_bytes"]) / 1024
        st.success(f"File diterima: {active_name} ({size_kb:,.1f} KB). Data sedang diperiksa.")
        st.button("Hapus file dan mulai lagi", on_click=hapus_csv_sesi,
                  key="k4_clear", use_container_width=False)

st.markdown("#### Belum punya file CSV?")
c1, c2 = st.columns(2, gap="small")
with c1:
    if DEMO_FILE.is_file():
        st.download_button(
            "⬇️ Unduh CSV contoh 18 silinder",
            data=DEMO_FILE.read_bytes(),
            file_name="contoh_18_silinder.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.warning("CSV contoh tidak ditemukan pada folder data/ di server.")
with c2:
    if TEMPLATE_FILE.is_file():
        st.download_button(
            "⬇️ Unduh template CSV kosong",
            data=TEMPLATE_FILE.read_bytes(),
            file_name="template_input.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.warning("Template CSV belum tersedia di folder data/ di server.")
with st.expander("Lihat panduan format CSV"):
    st.markdown(
        "Kolom wajib: `id_benda_uji`, `campuran`, `umur_hari`, "
        "`diameter_mm`, `beban_maksimum_kN`, dan `id_pengujian`. "
        "Gunakan satu baris untuk setiap silinder, dengan diameter dalam mm dan beban dalam kN."
    )
    st.caption("Unduh file contoh di atas untuk melihat susunan datanya.")

with st.sidebar:
    # Pengaturan analisis tetap tersedia saat kembali dari Beranda / About.
    if st.session_state.get("k4_uploaded_bytes") is not None:
        st.divider()
        st.markdown("### ⚙️ Pengaturan Analisis")
        st.caption("Data diproses dalam sesi. Aplikasi tidak menyimpannya otomatis ke database.")
        target = st.number_input(
            "Mutu rencana f'c (MPa)", min_value=1.0, max_value=150.0,
            value=30.0, step=0.5,
            help="Parameter evaluasi, bukan kolom CSV.",
        )
        nama_proyek = st.text_input(
            "Nama proyek", value="PjBL K4 - Evaluasi Kuat Tekan Beton", max_chars=110,
        )
        penanggung = st.text_input(
            "Kelompok / penanggung jawab", value="Kelompok PjBL K4", max_chars=85,
        )
        label_sumber = st.selectbox(
            "Jenis sumber data",
            ["Ilustratif / pembelajaran", "Data uji lapangan (perlu verifikasi)"],
            index=0,
        )
        st.caption("Status data lapangan tidak otomatis membuktikan penerimaan beton.")
        st.divider()
        st.markdown("**Asumsi simulasi SNI**")
        st.caption("Dua silinder Ø150 mm per hasil uji, umur 28 hari, tiga hasil uji berurutan. ±2SD hanya skrining outlier.")

# Halaman awal sengaja tidak melakukan perhitungan otomatis dari CSV contoh.
# Ketika uploader masih kosong, hentikan eksekusi SEBELUM analisis, tabel dan grafik.
if st.session_state.get("k4_uploaded_bytes") is None:
    st.info("**Belum ada data aktif.** Unggah CSV melalui kotak di atas untuk melihat hasil analisis.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**01 · Siapkan data**")
        st.caption("Gunakan template kolom atau file CSV milikmu.")
    with c2:
        st.markdown("**02 · Unggah CSV**")
        st.caption("Periksa dan perbaiki data di editor.")
    with c3:
        st.markdown("**03 · Unduh laporan**")
        st.caption("Dapatkan analisis, grafik, PDF dan ZIP.")
    st.stop()

raw_bytes = st.session_state["k4_uploaded_bytes"]
source_name = st.session_state["k4_uploaded_name"]
if len(raw_bytes) > 10 * 1024 * 1024:
    st.error("CSV melebihi batas unggahan 10 MB.")
    st.stop()

try:
    raw_df = read_csv(raw_bytes)
except DataValidationError as exc:
    st.error("Tidak dapat membaca CSV.")
    for problem in exc.problems:
        st.write("•",problem)
    st.stop()

fingerprint = hashlib.md5(raw_bytes).hexdigest()[:10]
if st.session_state.get("k4_active_fingerprint") != fingerprint:
    st.session_state["k4_active_fingerprint"] = fingerprint
    st.session_state["k4_saved_edit_csv"] = None
editor_initial_df = raw_df
if st.session_state.get("k4_saved_edit_csv") is not None:
    try:
        editor_initial_df = pd.read_csv(BytesIO(st.session_state["k4_saved_edit_csv"]))
    except Exception:
        editor_initial_df = raw_df
with st.expander("✏️ Tinjau atau edit data sebelum dihitung",expanded=False):
    st.caption("Ubah beban, diameter, campuran, atau tambah/hapus baris. Seluruh hasil di bawah otomatis mengikuti perubahan tabel ini. File asli di laptop tidak akan berubah.")
    edited_df = st.data_editor(editor_initial_df, num_rows="dynamic", hide_index=True, use_container_width=True,
                               key=f"data_editor_{fingerprint}")
    st.session_state["k4_saved_edit_csv"] = edited_df.to_csv(index=False).encode("utf-8-sig")
    st.caption("Editor bekerja di sesi browser. CSV asli tidak ditimpa; unduh perubahan jika ingin menyimpannya.")
    st.download_button("⬇️ Unduh CSV hasil edit", data=edited_df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="data_beton_hasil_edit.csv", mime="text/csv", key="unduh_editor")

# Audit rinci tersedia SEBELUM validasi mesin, sehingga input salah masih bisa diperbaiki.
audit = audit_csv(edited_df)
audit_summary = audit_counts(audit)
with st.expander(f"🛡️ Audit input — {audit_summary['error']} error, {audit_summary['peringatan']} peringatan",
                 expanded=bool(audit_summary["error"])):
    if audit.empty:
        st.success("Tidak ditemukan masalah format maupun peringatan skrining data.")
    else:
        st.dataframe(audit, hide_index=True, use_container_width=True, height=270)
        st.caption("Baris CSV mengikuti nomor Excel: baris 1 adalah header. Peringatan bukan otomatis kesalahan data.")
    st.download_button(
        "Unduh hasil audit (.csv)",
        data=audit.to_csv(index=False).encode("utf-8-sig"),
        file_name="audit_input_k4.csv", mime="text/csv", use_container_width=True,
        key="download_audit_awal",
    )
if audit_summary["error"]:
    st.error("Perbaiki error di tabel editor atau CSV sebelum hasil, grafik, dan PDF dapat dibuat.")
    st.stop()

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

tabs = st.tabs(["📊 Ringkasan", "📋 Data & statistik", "🧪 Evaluasi mutu", "📈 Visualisasi",
                "📥 Unduh laporan", "ℹ️ Metode", "🧮 Skenario beban", "🔍 Bandingkan CSV", "✅ Audit input"])

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
    st.caption("Seluruh angka dan grafik berasal dari CSV aktif. Edit tabel atau unggah CSV lain untuk memperbarui hasil.")

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

    st.divider()
    st.markdown("### Statistik lanjutan · distribusi dan ketidakpastian")
    jenis_stat = st.radio(
        "Satuan analisis deskriptif",
        ["silinder", "hasil_uji"],
        format_func=lambda v: "Per silinder" if v == "silinder" else "Per hasil uji (rata-rata pasangan)",
        horizontal=True,
        key="k4_tingkat_statistik",
    )
    lanjut = statistik_lanjutan(h, tingkat=jenis_stat)
    angka_stat = [c for c in lanjut.columns if c.endswith("_MPa") or c.endswith("_persen")]
    st.dataframe(
        lanjut.style.format({c: "{:.2f}" for c in angka_stat}, na_rep="—"),
        hide_index=True, use_container_width=True,
    )
    st.download_button(
        "⬇️ Unduh statistik lanjutan (.csv)",
        data=lanjut.to_csv(index=False).encode("utf-8-sig"),
        file_name="statistik_lanjutan_k4.csv", mime="text/csv",
        key="k4_unduh_stat_lanjut",
    )
    pilihan_grafik_stat = st.multiselect(
        "Campuran pada grafik ketidakpastian",
        options=lanjut["campuran"].tolist(),
        default=lanjut["campuran"].tolist(), key="k4_grafik_interval_campuran",
    )
    graf_data = lanjut[lanjut["campuran"].isin(pilihan_grafik_stat)]
    if not graf_data.empty:
        fig_ci = go.Figure()
        for i, row in enumerate(graf_data.itertuples(index=False)):
            value = float(row.mean_MPa)
            lo, hi = float(row.ci95_rerata_bawah_MPa), float(row.ci95_rerata_atas_MPa)
            has_ci = bool(np.isfinite(lo) and np.isfinite(hi))
            fig_ci.add_trace(go.Scatter(
                x=[str(row.campuran)], y=[value], mode="markers",
                name=str(row.campuran), marker=dict(size=12, color=PALETTE[i % len(PALETTE)]),
                error_y=dict(type="data", symmetric=False,
                             array=[max(0, hi-value)] if has_ci else [0],
                             arrayminus=[max(0, value-lo)] if has_ci else [0], visible=has_ci),
                hovertemplate=("Campuran %{x}<br>Rerata %{y:.2f} MPa<extra></extra>"),
            ))
        fig_ci.add_hline(y=target, line_dash="dash", line_color="#C45D4A")
        fig_ci.update_layout(
            title="Rerata dan interval bootstrap 95% (jika n ≥ 5)",
            xaxis_title="Campuran", yaxis_title="Kuat tekan (MPa)",
            template="plotly_white", height=350, showlegend=False,
        )
        st.plotly_chart(fig_ci, use_container_width=True)
    else:
        st.info("Pilih minimal satu campuran untuk melihat grafik.")
    st.caption(
        "P10/P90, kuartil, IQR, dan CV bersifat deskriptif. Interval bootstrap 95% "
        "untuk rata-rata hanya ditampilkan saat n ≥ 5; pada sampel kecil estimasi masih "
        "tidak stabil dan bukan kriteria penerimaan mutu beton."
    )

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

    st.divider()
    st.markdown("### Simulasi interaktif perubahan target mutu")
    st.caption(
        "Geser rentang target untuk melihat bagaimana jumlah silinder yang mencapai target "
        "dan status numerik setiap campuran berubah. Nilai beban dan CSV tidak diubah."
    )
    batas_bawah = max(1.0, round((target - 12) * 2) / 2)
    batas_atas = min(150.0, round((target + 12) * 2) / 2)
    if batas_bawah >= batas_atas:
        batas_bawah, batas_atas = max(1.0, target-5.0), min(150.0, target+5.0)
    low, high = st.slider(
        "Rentang target yang disimulasikan (MPa)",
        min_value=1.0, max_value=150.0,
        value=(float(batas_bawah), float(batas_atas)),
        step=0.5, key="k4_target_range",
    )
    # Maksimum 101 titik agar perubahan slider tetap responsif.
    t_grid = np.linspace(low, high, 51) if high > low else np.array([low])
    t_grid = sorted({round(float(v), 3) for v in t_grid} | {float(target)})
    sweep_target = sensitivitas_target(h, t_grid)
    ringkas_target = rekap_sensitivitas_target(sweep_target)
    mix_pick = st.multiselect(
        "Campuran untuk kurva persentase silinder mencapai target",
        options=h.statistik["campuran"].tolist(),
        default=h.statistik["campuran"].tolist(),
        key="k4_target_mix_filter",
    )
    filtered_target = sweep_target[sweep_target["campuran"].isin(mix_pick)]
    if filtered_target.empty:
        st.info("Pilih minimal satu campuran untuk melihat kurva.")
    else:
        kurva = px.line(
            filtered_target, x="target_MPa", y="persen_silinder_capai_target",
            color="campuran", markers=False, color_discrete_sequence=PALETTE,
            labels={"target_MPa":"Target simulasi (MPa)",
                    "persen_silinder_capai_target":"Silinder ≥ target (%)", "campuran":"Campuran"},
            title="Sensitivitas persentase silinder yang mencapai target",
        )
        kurva.add_vline(x=target, line_dash="dash", line_color="#C45D4A")
        kurva.update_layout(template="plotly_white", height=370,
                            yaxis=dict(range=[0, 105], ticksuffix="%"))
        st.plotly_chart(kurva, use_container_width=True)
    cx, cy = st.columns([1.3, 1])
    with cx:
        grafik_campuran = px.line(
            ringkas_target, x="target_MPa", y="memenuhi_simulasi",
            markers=False, title="Jumlah campuran memenuhi simulasi",
            labels={"target_MPa":"Target f'c (MPa)", "memenuhi_simulasi":"Jumlah campuran"},
        )
        grafik_campuran.add_vline(x=target, line_dash="dash", line_color="#C45D4A")
        grafik_campuran.update_layout(template="plotly_white", height=300,
                                      yaxis=dict(dtick=1, rangemode="tozero"))
        st.plotly_chart(grafik_campuran, use_container_width=True)
    with cy:
        st.markdown("#### Ringkasan kondisi sekarang")
        cur = ringkas_target[np.isclose(ringkas_target["target_MPa"], target)]
        if not cur.empty:
            r = cur.iloc[0]
            st.metric("Campuran memenuhi simulasi", f"{int(r['memenuhi_simulasi'])} dari {int(r['jumlah_campuran'])}")
            st.metric("Silinder ≥ target", f"{float(r['persen_silinder_capai_target']):.1f}%")
            if int(r["tidak_dapat_dievaluasi"]) > 0:
                st.warning(f"{int(r['tidak_dapat_dievaluasi'])} campuran tidak dapat dievaluasi; bukan dianggap gagal.")
    with st.expander("Tabel simulasi numerik dan cara membacanya"):
        preview = sweep_target[np.isclose(sweep_target["target_MPa"], target)]
        st.dataframe(preview, hide_index=True, use_container_width=True)
        st.caption("Status tiga hasil uji memakai aturan dan asumsi simulasi yang sama dengan hasil utama.")
    st.download_button("⬇️ Unduh seluruh simulasi target (.csv)",
                       sweep_target.to_csv(index=False).encode("utf-8-sig"),
                       file_name="simulasi_target_mutu.csv", mime="text/csv", key="k4_unduh_sensitivitas_target")
    st.caption("Analisis sensitivitas bukan prediksi kuat tekan. Mengubah target simulasi di sini tidak mengubah PDF utama.")

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

    st.divider()
    st.markdown("### Distribusi kumulatif (ECDF)")
    st.caption("Grafik ini menunjukkan proporsi silinder dengan kuat tekan ≤ nilai pada sumbu X; "
               "pengguna dapat memperbesar area dan memeriksa titik dengan mouse.")
    pilih_ecdf = st.multiselect(
        "Campuran pada grafik ECDF",
        options=h.statistik["campuran"].tolist(),
        default=h.statistik["campuran"].tolist(), key="k4_ecdf_filter",
    )
    bahan_ecdf = h.benda_uji[h.benda_uji["campuran"].isin(pilih_ecdf)]
    if bahan_ecdf.empty:
        st.info("Pilih minimal satu campuran untuk melihat distribusi kumulatif.")
    else:
        ecdf = px.ecdf(
            bahan_ecdf, x="kuat_tekan_MPa", color="campuran",
            ecdfnorm="percent", color_discrete_sequence=PALETTE,
            title="Persentase kumulatif hasil kuat tekan per campuran",
        )
        ecdf.add_vline(x=target, line_dash="dash", line_color="#C45D4A")
        ecdf.update_layout(template="plotly_white", xaxis_title="Kuat tekan silinder (MPa)",
                           yaxis_title="Proporsi kumulatif (%)", height=390)
        st.plotly_chart(ecdf, use_container_width=True)
    st.caption("Statistik lanjutan dan kurva sensitivitas target dapat diunduh dari tab Data & Statistik dan Evaluasi Mutu.")

with tabs[4]:
    st.markdown("### Ekspor hasil analisis saat ini")
    st.write("Seluruh file di bawah dihasilkan dari tabel yang sedang digunakan, termasuk perubahan lewat editor CSV.")
    st.caption("Skenario beban dan dataset pembanding tidak mengubah PDF utama. PDF utama selalu memakai CSV utama yang sudah diedit dan target di sidebar.")
    # Cache hasil ekspor dengan kunci CSV + parameter agar filter/tombol lain
    # tidak membuat PDF ulang ketika datanya tidak berubah.
    with st.spinner("Menyiapkan grafik, PDF dan paket hasil..."):
        current_csv = h.input_data.to_csv(index=False).encode("utf-8")
        graphics, pdf, bundle = cache_berkas_laporan(
            current_csv, float(target), nama_proyek, penanggung, h.sumber_data
        )
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



with tabs[6]:
    st.markdown("### Laboratorium simulasi beban (What-if)")
    st.info("Mode eksplorasi: beban maksimum setiap silinder dikalikan faktor yang sama. Ini **bukan** prediksi kekuatan beton, **bukan** data hasil uji baru, dan tidak mengubah CSV/PDF utama.")
    delta_p = st.slider("Skenario perubahan semua beban (%)", -50, 100, 10, 1, key="simulasi_beban")
    alt = simulasi_beban(h, delta_p)
    base_stat = h.statistik.set_index("campuran")
    scenario_stat = alt.statistik.set_index("campuran")
    rows = []
    for mix in base_stat.index:
        b=float(base_stat.loc[mix, "rata_rata"])
        a=float(scenario_stat.loc[mix, "rata_rata"])
        rows.append({"campuran": mix, "awal_MPa": b, "skenario_MPa": a,
                     "perubahan_MPa": a-b,
                     "status_skenario": alt.evaluasi.set_index("campuran").loc[mix,"status"]})
    comp = pd.DataFrame(rows)
    st.dataframe(comp.style.format({"awal_MPa":"{:.2f}", "skenario_MPa":"{:.2f}", "perubahan_MPa":"{:+.2f}"}),
                 hide_index=True, use_container_width=True)
    sweep = tabel_skenario(h, [-20, -10, 0, 10, 20])
    chart = px.line(sweep, x="perubahan_beban_persen", y="rata_rata_MPa", color="campuran", markers=True,
                    title="Sensitivitas rata-rata kuat tekan terhadap perubahan beban", color_discrete_sequence=PALETTE)
    chart.add_hline(y=target, line_dash="dash", line_color="#C45D4A")
    chart.update_layout(template="plotly_white", xaxis_title="Perubahan beban (%)", yaxis_title="Rata-rata kuat tekan (MPa)")
    st.plotly_chart(chart, use_container_width=True)
    st.download_button("⬇️ Unduh tabel sensitivitas", sweep.to_csv(index=False).encode("utf-8-sig"),
                       file_name="skenario_sensitivitas_beban.csv", mime="text/csv")
    st.caption("Tiap skenario menghitung ulang statistik dan status simulasi numerik dari nilai beban baru. Gunakan hanya untuk studi sensitivitas.")

with tabs[7]:
    st.markdown("### Bandingkan CSV kedua dengan data utama")
    st.caption("Analisis pembanding tidak mencampur sampel dan tidak menyimpan CSV ke database. Perbandingan memakai nama campuran yang sama jika tersedia.")
    second = st.file_uploader("Unggah CSV pembanding (opsional)", type=["csv"], key="compare_csv")
    if second is None:
        st.info("Unggah CSV kedua untuk membandingkan jumlah silinder, rata-rata, CV, dan selisih kuat tekan antar-dataset.")
    else:
        try:
            if len(second.getvalue()) > 10*1024*1024:
                raise DataValidationError(["CSV pembanding melebihi 10 MB."])
            second_df = read_csv(second.getvalue())
            second_audit = audit_csv(second_df)
            if audit_counts(second_audit)["error"]:
                st.error("CSV pembanding mempunyai data tidak valid.")
                st.dataframe(second_audit[second_audit.tingkat=="Error"], hide_index=True, use_container_width=True)
            else:
                second_result = analisis(second_df, target,
                    sumber="Data pembanding (tidak digabung): " + second.name,
                    raw_bytes=second.getvalue())
                combined = bandingkan_dua_analisis(h, second_result)
                ca, cb = st.columns(2)
                ca.metric("CSV utama — silinder", h.ringkasan["silinder"])
                cb.metric("CSV pembanding — silinder", second_result.ringkasan["silinder"])
                st.dataframe(combined.style.format({
                    "rata_A_MPa":"{:.2f}", "rata_B_MPa":"{:.2f}",
                    "cv_A_persen":"{:.2f}", "cv_B_persen":"{:.2f}",
                    "selisih_B_minus_A_MPa":"{:+.2f}"}, na_rep="—"),
                    hide_index=True, use_container_width=True)
                graphdata = pd.concat([
                    h.statistik[["campuran","rata_rata"]].assign(dataset="CSV utama"),
                    second_result.statistik[["campuran","rata_rata"]].assign(dataset="CSV pembanding")
                ], ignore_index=True)
                chart_cmp = px.bar(graphdata, x="campuran", y="rata_rata", color="dataset", barmode="group",
                    title="Perbandingan rata-rata antar-CSV", labels={"campuran":"Campuran", "rata_rata":"Kuat tekan (MPa)"})
                chart_cmp.add_hline(y=target, line_dash="dash", line_color="#C45D4A")
                chart_cmp.update_layout(template="plotly_white")
                st.plotly_chart(chart_cmp, use_container_width=True)
                st.download_button("⬇️ Unduh CSV perbandingan", combined.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="perbandingan_dua_dataset.csv", mime="text/csv")
                st.warning("Selisih dua dataset bersifat deskriptif; belum memperhitungkan kesetaraan sampel, umur, kondisi, atau ketidakpastian statistik.")
        except DataValidationError as exc:
            for err in exc.problems:
                st.error(err)
        except Exception as exc:
            st.error("CSV pembanding tidak dapat dianalisis. Periksa format file.")
            st.caption(str(exc))

with tabs[8]:
    st.markdown("### Hasil audit kualitas input")
    c1, c2, c3 = st.columns(3)
    c1.metric("Jumlah silinder",len(edited_df))
    c2.metric("Error input",audit_summary["error"])
    c3.metric("Catatan/peringatan",audit_summary["peringatan"] + len(h.peringatan))
    if audit.empty:
        st.success("Tidak ada temuan audit awal.")
    else:
        options = st.multiselect("Tingkat temuan", ["Error", "Peringatan"], default=["Error", "Peringatan"])
        st.dataframe(audit[audit["tingkat"].isin(options)], hide_index=True,use_container_width=True)
    st.markdown("#### Catatan validasi mesin")
    if h.peringatan:
        for msg in h.peringatan:
            st.warning(msg)
    else:
        st.success("Tidak ada catatan validasi tambahan.")
    st.download_button("⬇️ Unduh laporan audit (.csv)", audit.to_csv(index=False).encode("utf-8-sig"),
                       file_name="audit_kualitas_data.csv",mime="text/csv",key="audit_full_download")
    st.caption("Audit tidak menggantikan pemeriksaan rekaman laboratorium, standar uji, kalibrasi alat, dan otorisasi pemeriksa.")

st.divider()
st.caption("K4 ConcreteLab Pro v2.2 • PjBL Teknik Sipil • Simulasi, bukan sertifikat hasil uji laboratorium • Engine Python teruji")
