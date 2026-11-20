"""ConcreteLab Pro v6.0: analitik profesional dengan gerbang hak akses tamu."""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import hashlib
import math
from datetime import date
from zoneinfo import ZoneInfo
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
from concretelab.professional import ringkasan_eksekutif, tabel_kinerja, interpretasi_per_campuran
from concretelab.visuals_v4 import (grafik_rerata, grafik_histogram, grafik_box, grafik_tren, grafik_pencapaian, grafik_ecdf)
from concretelab.projects import (buat_arsip_proyek, baca_arsip_proyek,
                                   LocalHistoryStore, ProjectArchiveError, report_id_for, sha256)
from concretelab.policy_ui import current_policy
from concretelab.permissions import is_active_profile
from concretelab.tracking import (buat_template_registrasi, validasi_registrasi,
                                  jadwal_pengujian, label_qr_pdf, kalender_ics,
                                  export_registrasi_csv, kode_qr_sampel, TrackingError)

# Lokasi file ini app_pages/service.py; data/ berada satu tingkat di atas app_pages.
BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_FILE = BASE_DIR / "data" / "contoh_18_silinder.csv"
TEMPLATE_FILE = BASE_DIR / "data" / "template_kosong.csv"
PALETTE = ["#387C9E", "#138579", "#DE9952", "#8378B8", "#9B677A", "#65908F"]


# v5.5: jangan menyimpan CSV/hasil proyek pribadi dalam cache global lintas-sesi.
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
st.caption("Analisis kuat tekan beton • Ringkasan profesional • Visual Analytics • PDF otomatis • Arsip proyek")
st.caption("Sesudah mengunggah CSV, pengaturan target mutu dapat dibuka melalui sidebar di sisi kiri.")
st.divider()



# Baca aturan terverifikasi tiap rerun. Admin dapat mengubah izin dalam database;
# pemilik akun pending/suspended tetap mengikuti hak akses tamu.
ACCESS_POLICY, ACCESS_USER, ACCESS_PROFILE = current_policy()
AUTHORIZED_ACCOUNT = bool(ACCESS_USER is not None and is_active_profile(ACCESS_PROFILE))

def permitted(feature: str) -> bool:
    return ACCESS_POLICY.allowed(feature, logged_in=ACCESS_USER is not None,
                                 account_active=AUTHORIZED_ACCOUNT)

def offer_download(*args, **kwargs):
    """Central gate: all Streamlit download widgets use this function."""
    if not permitted('exports'):
        return False
    return st.download_button(*args, **kwargs)

if not permitted('upload_csv'):
    # Remove session-local uploaded data when public access has been revoked.
    for key in ('k4_uploaded_bytes','k4_uploaded_name','k4_saved_edit_csv',
                'k4_imported_project','k4_archive_export','k4_archive_export_key'):
        st.session_state.pop(key,None)
    st.warning('Administrator sedang menonaktifkan akses Analisis Cepat untuk tamu. '
               'Silakan login dengan akun yang telah disetujui.')
    st.stop()
if ACCESS_POLICY.cloud_configured and 'tidak dapat diverifikasi' in ACCESS_POLICY.source:
    st.error('Akses publik sementara ditutup: pengaturan administrator tidak dapat diverifikasi.')
    st.stop()

def simpan_csv_ke_sesi():
    """Simpan salinan bytes CSV di session_state supaya bertahan saat pindah halaman."""
    f = st.session_state.get("k4_csv_upload")
    for k in ("k4_imported_project", "k4_restored_target", "k4_restored_name", "k4_restored_owner"):
        st.session_state.pop(k, None)
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
    for key in ("k4_csv_upload", "k4_uploaded_bytes", "k4_uploaded_name", "k4_saved_edit_csv", "k4_active_fingerprint", "k4_imported_project", "k4_archive_export", "k4_archive_export_key", "k4_restored_target", "k4_restored_name", "k4_restored_owner", "k4_archive_upload"):
        st.session_state.pop(key, None)


def pulihkan_dari_arsip(data: bytes):
    """Periksa arsip sebelum memulihkan data dan nama proyek ke sesi."""
    item = baca_arsip_proyek(data)
    st.session_state["k4_uploaded_bytes"] = item.csv_bytes
    st.session_state["k4_uploaded_name"] = f"arsip_{item.metadata['id_arsip'][:8]}.csv"
    st.session_state["k4_imported_project"] = item.metadata
    st.session_state["k4_restored_target"] = float(item.metadata["target_MPa"])
    st.session_state["k4_restored_name"] = item.metadata["nama_proyek"]
    st.session_state["k4_restored_owner"] = item.metadata["penanggung_jawab"]
    st.session_state.pop("k4_saved_edit_csv", None)
    st.session_state.pop("k4_active_fingerprint", None)


def saat_arsip_diunggah():
    f = st.session_state.get("k4_archive_upload")
    if f is not None:
        try:
            pulihkan_dari_arsip(f.getvalue())
            st.session_state.pop("k4_import_error", None)
        except ProjectArchiveError as exc:
            st.session_state["k4_import_error"] = str(exc)

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

if permitted('archive'):
    with st.expander("📁 Buka arsip proyek K4 sebelumnya (.zip)", expanded=False):
        st.caption("Pilih arsip yang pernah diunduh dari tab Proyek & Riwayat. "
                   "Aplikasi memverifikasi checksum setiap file sebelum memulihkan CSV.")
        st.file_uploader("Unggah arsip proyek K4", type=["zip"],
                         key="k4_archive_upload", on_change=saat_arsip_diunggah)
        if st.session_state.get("k4_import_error"):
            st.error(st.session_state["k4_import_error"])
        if st.session_state.get("k4_imported_project"):
            info = st.session_state["k4_imported_project"]
            st.success(f"Arsip terverifikasi: {info['nama_proyek']} · {info['id_laporan']}")

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
        offer_download(
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
        offer_download(
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
        st.caption("Data diproses dalam sesi. Simpan arsip proyek melalui tab Proyek & Riwayat jika ingin menyimpan versi.")
        target = st.number_input(
            "Mutu rencana f'c (MPa)", min_value=1.0, max_value=150.0,
            value=float(st.session_state.get("k4_restored_target", 30.0)), step=0.5,
            help="Parameter evaluasi, bukan kolom CSV.",
        )
        nama_proyek = st.text_input(
            "Nama proyek", value=st.session_state.get("k4_restored_name", "PjBL K4 - Evaluasi Kuat Tekan Beton"), max_chars=110,
        )
        penanggung = st.text_input(
            "Kelompok / penanggung jawab", value=st.session_state.get("k4_restored_owner", "Kelompok PjBL K4"), max_chars=85,
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
edited_df = editor_initial_df
if permitted('edit_csv'):
    with st.expander("✏️ Tinjau atau edit data sebelum dihitung",expanded=False):
        st.caption("Ubah beban, diameter, campuran, atau tambah/hapus baris. Seluruh hasil di bawah otomatis mengikuti perubahan tabel ini. File asli di laptop tidak akan berubah.")
        edited_df = st.data_editor(editor_initial_df, num_rows="dynamic", hide_index=True, use_container_width=True,
                                   key=f"data_editor_{fingerprint}")
        st.session_state["k4_saved_edit_csv"] = edited_df.to_csv(index=False).encode("utf-8-sig")
        st.caption("Editor bekerja di sesi browser. CSV asli tidak ditimpa; unduh perubahan jika ingin menyimpannya.")
        offer_download("⬇️ Unduh CSV hasil edit", data=edited_df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="data_beton_hasil_edit.csv", mime="text/csv", key="unduh_editor")

# Audit rinci tersedia SEBELUM validasi mesin, sehingga input salah masih bisa diperbaiki.
audit = audit_csv(edited_df)
audit_summary = audit_counts(audit)
if permitted('audit'):
    with st.expander(f"🛡️ Audit input — {audit_summary['error']} error, {audit_summary['peringatan']} peringatan",
                     expanded=bool(audit_summary["error"])):
        if audit.empty:
            st.success("Tidak ditemukan masalah format maupun peringatan skrining data.")
        else:
            st.dataframe(audit, hide_index=True, use_container_width=True, height=270)
            st.caption("Baris CSV mengikuti nomor Excel: baris 1 adalah header. Peringatan bukan otomatis kesalahan data.")
        offer_download(
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
if permitted('summary'):
    metrics = st.columns(5)
    metrics[0].metric("Jumlah silinder",f"{summary['silinder']:,}")
    metrics[1].metric("Campuran",summary["campuran"])
    metrics[2].metric("Hasil pengujian",summary["jumlah_uji"])
    metrics[3].metric("Silinder ≥ target",f"{summary['mencapai_target']} / {summary['silinder']}")
    metrics[4].metric("Indikasi outlier",summary["indikasi_outlier"])

tab_names = ["📊 Executive Summary", "📋 Data & statistik", "🧪 Evaluasi mutu", "📈 Visual Analytics",
             "📥 Unduh laporan", "ℹ️ Metode", "🧮 Skenario beban", "🔍 Bandingkan CSV", "✅ Audit input", "📁 Proyek & Riwayat", "🗓️ Sampel & Jadwal"]
tab_features = ['summary','statistics','quality','visuals','exports','method','simulation',
                'comparison','audit','archive','tracking']
tabs = st.tabs([title if permitted(feature) else '🔒 '+title for title,feature in zip(tab_names,tab_features)])

if permitted('summary'):
    with tabs[0]:
        st.markdown("### Executive Summary")
        st.caption("Ringkasan dihasilkan otomatis dari CSV aktif dan mutu rencana yang dipilih; tidak ada angka contoh tetap.")
        ex = ringkasan_eksekutif(h)
        top1 = st.columns(4)
        top1[0].metric("Jumlah silinder", f"{ex.jumlah_silinder:,}")
        top1[1].metric("Hasil uji", f"{ex.jumlah_uji:,}")
        top1[2].metric("Rerata seluruh silinder", f"{ex.rata_rata_mpa:.2f} MPa")
        top1[3].metric("Silinder mencapai target", f"{ex.persen_silinder_target:.1f}%")
        st.markdown("#### Ikhtisar teknis")
        st.write(ex.deskripsi)
        a, b = st.columns([1.45, 1], gap="large")
        with a:
            st.markdown("**Perbandingan kuat tekan per campuran**")
            st.plotly_chart(grafik_rerata(h), use_container_width=True, key="k4_executive_rerata")
            st.caption("Error bar = satu simpangan baku sampel. Garis putus-putus = target mutu input.")
        with b:
            st.markdown("**Pencapaian target tiap silinder**")
            st.plotly_chart(grafik_pencapaian(h), use_container_width=True, key="k4_executive_pencapaian")
            st.caption("Persentase pada grafik ini bukan status penerimaan mutu menurut SNI.")
        st.markdown("#### Status evaluasi per campuran")
        kinerja=tabel_kinerja(h)
        st.dataframe(kinerja.style.format({
            "rata_rata_MPa":"{:.2f}","simpangan_baku_MPa":"{:.2f}",
            "cv_persen":"{:.2f}%", "pencapaian_target_persen":"{:.1f}%",
            "rasio_rerata_ke_target_persen":"{:.1f}%",
        }, na_rep="—"), hide_index=True, use_container_width=True)
        st.markdown("#### Interpretasi otomatis berdasarkan data")
        for note in interpretasi_per_campuran(h):
            st.write("•", note)
        with st.expander("Catatan metodologis penting", expanded=True):
            for note in ex.catatan:
                st.caption("• " + note)
        offer_download(
            "⬇️ Unduh ringkasan kinerja per campuran (.csv)",
            kinerja.to_csv(index=False).encode("utf-8-sig"),
            file_name="ringkasan_kinerja_campuran.csv", mime="text/csv",
            key="k4_v4_download_performance",
        )

else:
    with tabs[0]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('statistics'):
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
        offer_download(
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
            st.plotly_chart(fig_ci, use_container_width=True, key="k4_statistik_interval_bootstrap")
        else:
            st.info("Pilih minimal satu campuran untuk melihat grafik.")
        st.caption(
            "P10/P90, kuartil, IQR, dan CV bersifat deskriptif. Interval bootstrap 95% "
            "untuk rata-rata hanya ditampilkan saat n ≥ 5; pada sampel kecil estimasi masih "
            "tidak stabil dan bukan kriteria penerimaan mutu beton."
        )

else:
    with tabs[1]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('quality'):
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
        if permitted('simulation'):
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
                st.plotly_chart(kurva, use_container_width=True, key="k4_simulasi_target_persentase")
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
                st.plotly_chart(grafik_campuran, use_container_width=True, key="k4_simulasi_target_jumlah_campuran")
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
            offer_download("⬇️ Unduh seluruh simulasi target (.csv)",
                               sweep_target.to_csv(index=False).encode("utf-8-sig"),
                               file_name="simulasi_target_mutu.csv", mime="text/csv", key="k4_unduh_sensitivitas_target")
            st.caption("Analisis sensitivitas bukan prediksi kuat tekan. Mengubah target simulasi di sini tidak mengubah PDF utama.")

else:
    with tabs[2]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('visuals'):
    with tabs[3]:
        st.markdown("### Visual Analytics")
        st.caption("Warna setiap campuran konsisten; grafik dapat di-zoom, diperbesar, dan dibaca melalui hover.")
        pilihan=st.multiselect(
            "Campuran ditampilkan", options=h.statistik["campuran"].astype(str).tolist(),
            default=h.statistik["campuran"].astype(str).tolist(), key="k4_v4_filter_visual",
        )
        if not pilihan:
            st.info("Pilih setidaknya satu campuran untuk menampilkan grafik.")
        else:
            d=h.input_data[h.input_data['campuran'].astype(str).isin(pilihan)]
            visual_result = h if len(d)==len(h.input_data) else analisis(d, target, sumber=h.sumber_data)
            a,b=st.columns(2, gap="medium")
            with a:
                st.markdown("**Distribusi kuat tekan silinder**")
                st.plotly_chart(grafik_histogram(visual_result), use_container_width=True, key="k4_visual_histogram")
            with b:
                st.markdown("**Sebaran dan variasi antar-campuran**")
                st.plotly_chart(grafik_box(visual_result), use_container_width=True, key="k4_visual_boxplot")
            st.divider()
            c,d=st.columns(2, gap="medium")
            with c:
                st.markdown("**Tren berdasarkan urutan pengujian**")
                st.plotly_chart(grafik_tren(visual_result), use_container_width=True, key="k4_visual_tren")
            with d:
                st.markdown("**Perbandingan rerata ± SD**")
                st.plotly_chart(grafik_rerata(visual_result), use_container_width=True, key="k4_visual_rerata")
            st.divider()
            st.markdown("**Distribusi kumulatif / ECDF**")
            st.plotly_chart(grafik_ecdf(visual_result), use_container_width=True, key="k4_visual_ecdf")
            st.caption("ECDF memperlihatkan proporsi silinder dengan kuat tekan tidak melebihi nilai tertentu; tidak sama dengan peluang penerimaan mutu.")
        st.caption("Filter hanya memengaruhi grafik pada tab ini. PDF dan hasil utama tetap menggunakan seluruh CSV yang tervalidasi.")
        st.caption("Grafik PNG versi cetak tersedia dalam paket hasil ZIP.")

else:
    with tabs[3]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('exports'):
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
            offer_download("📄 Unduh laporan PDF otomatis",data=pdf,file_name="Laporan_Otomatis_K4_Beton.pdf",mime="application/pdf",use_container_width=True,type="primary")
            st.caption("Laporan PDF v4 berisi ringkasan eksekutif, empat grafik, tabel kinerja, evaluasi mutu, data rinci, dan QR.")
        with dl2:
            offer_download("📦 Unduh SEMUA hasil (.zip)",data=bundle,file_name="Paket_Lengkap_Hasil_K4_Beton.zip",mime="application/zip",use_container_width=True,type="primary")
            st.caption("ZIP: CSV input, analisis dan ringkasan profesional, empat grafik, PDF v4, serta metadata dan hash.")
        st.divider()
        colA,colB,colC=st.columns(3)
        colA.download_button("CSV kuat tekan",data=h.benda_uji.to_csv(index=False).encode("utf-8-sig"),file_name="hasil_kuat_tekan.csv",mime="text/csv",use_container_width=True)
        colB.download_button("CSV statistik",data=h.statistik.to_csv(index=False).encode("utf-8-sig"),file_name="statistik_campuran.csv",mime="text/csv",use_container_width=True)
        colC.download_button("CSV evaluasi",data=h.evaluasi.to_csv(index=False).encode("utf-8-sig"),file_name="evaluasi_simulasi.csv",mime="text/csv",use_container_width=True)
        st.success(f"Laporan berhasil diproses. Input hash: {h.hash_sumber[:14]}... | {summary['silinder']} benda uji | {summary['campuran']} campuran")

else:
    with tabs[4]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('method'):
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



else:
    with tabs[5]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('simulation'):
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
        st.plotly_chart(chart, use_container_width=True, key="k4_skenario_beban_sensitivitas")
        offer_download("⬇️ Unduh tabel sensitivitas", sweep.to_csv(index=False).encode("utf-8-sig"),
                           file_name="skenario_sensitivitas_beban.csv", mime="text/csv")
        st.caption("Tiap skenario menghitung ulang statistik dan status simulasi numerik dari nilai beban baru. Gunakan hanya untuk studi sensitivitas.")

else:
    with tabs[6]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('comparison'):
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
                    st.plotly_chart(chart_cmp, use_container_width=True, key="k4_perbandingan_csv_grafik")
                    offer_download("⬇️ Unduh CSV perbandingan", combined.to_csv(index=False).encode("utf-8-sig"),
                                       file_name="perbandingan_dua_dataset.csv", mime="text/csv")
                    st.warning("Selisih dua dataset bersifat deskriptif; belum memperhitungkan kesetaraan sampel, umur, kondisi, atau ketidakpastian statistik.")
            except DataValidationError as exc:
                for err in exc.problems:
                    st.error(err)
            except Exception as exc:
                st.error("CSV pembanding tidak dapat dianalisis. Periksa format file.")
                st.caption(str(exc))

else:
    with tabs[7]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('audit'):
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
        offer_download("⬇️ Unduh laporan audit (.csv)", audit.to_csv(index=False).encode("utf-8-sig"),
                           file_name="audit_kualitas_data.csv",mime="text/csv",key="audit_full_download")
        st.caption("Audit tidak menggantikan pemeriksaan rekaman laboratorium, standar uji, kalibrasi alat, dan otorisasi pemeriksa.")

    st.divider()
    st.caption("K4 ConcreteLab Pro v2.2 • PjBL Teknik Sipil • Simulasi, bukan sertifikat hasil uji laboratorium • Engine Python teruji")


else:
    with tabs[8]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('archive'):
    with tabs[9]:
        st.markdown("### Proyek & Riwayat · ConcreteLab Pro v3.0")
        st.caption("Simpan satu versi analisis sebagai arsip portabel, lalu buka kembali kapan saja. "
                   "Berkas arsip membawa CSV, metadata, checksum dan salinan PDF.")
        st.warning("Penyimpanan Cloud **tidak otomatis permanen**. Unduh arsip proyek ke perangkat. "
                   "Kode QR dan SHA-256 mendeteksi perubahan arsip, tetapi bukan tanda tangan digital atau sertifikat laboratorium.")

        report_id = report_id_for(h, nama_proyek)
        a1, a2, a3 = st.columns(3)
        a1.metric("ID laporan", report_id)
        a2.metric("Target mutu", f"{target:g} MPa")
        a3.metric("Baris data", str(len(h.input_data)))
        catatan = st.text_area("Catatan versi / perubahan", value="Analisis data dari CSV terverifikasi", max_chars=1000,
                               help="Contoh: revisi beban U01, penambahan kelompok pengujian, atau pengecekan ulang.")
        current_data = h.input_data.to_csv(index=False).encode("utf-8")
        snapshot_key = sha256((sha256(current_data) + f"|{target}|{nama_proyek}|{penanggung}|{catatan}").encode("utf-8"))
        if st.button("Buat arsip proyek terverifikasi", type="primary", key="buat_arsip_proyek"):
            try:
                with st.spinner("Menyiapkan PDF dan arsip proyek..."):
                    _, pdf_proyek, _ = cache_berkas_laporan(current_data, float(target), nama_proyek, penanggung, h.sumber_data)
                    st.session_state["k4_archive_export"] = buat_arsip_proyek(
                        h, nama_proyek=nama_proyek, penanggung_jawab=penanggung,
                        catatan=catatan, pdf_bytes=pdf_proyek,
                    )
                    st.session_state["k4_archive_export_key"] = snapshot_key
                st.success("Arsip proyek berhasil dibuat dan checksum sudah dicatat.")
            except (ProjectArchiveError, ValueError) as exc:
                st.error(f"Arsip gagal dibuat: {exc}")
        latest_archive = st.session_state.get("k4_archive_export")
        if latest_archive is not None and st.session_state.get("k4_archive_export_key") == snapshot_key:
            try:
                restored = baca_arsip_proyek(latest_archive)
                offer_download("⬇️ Download arsip proyek (.k4proj.zip)", data=latest_archive,
                                   file_name=f"K4_{report_id}.k4proj.zip", mime="application/zip",
                                   use_container_width=True, key="k4_download_archived_project")
                with st.expander("Lihat metadata dan fingerprint arsip"):
                    st.json(restored.metadata)
                    st.code(sha256(latest_archive), language=None)
            except ProjectArchiveError as exc:
                st.error(f"Integritas arsip tidak valid: {exc}")
        else:
            st.info("Tekan **Buat arsip proyek terverifikasi** setelah selesai mengedit CSV dan target.")

        st.divider()
        st.markdown("#### Riwayat lokal (opsional)")
        if os.environ.get("K4_ENABLE_LOCAL_HISTORY") == "1":
            st.warning("Mode riwayat lokal aktif. Gunakan hanya di komputer/server pribadi dan tepercaya "
                       "karena belum tersedia login, izin per pengguna, atau pemisahan data antarpengguna.")
            dbpath = BASE_DIR / "_local_data" / "history.sqlite3"
            try:
                store = LocalHistoryStore(dbpath)
                if latest_archive is not None and st.session_state.get("k4_archive_export_key") == snapshot_key:
                    if st.button("Simpan versi ini ke SQLite lokal", key="k4_save_sqlite"):
                        store.save(latest_archive)
                        st.success("Versi tersimpan pada SQLite lokal.")
                recents = store.list()
                if recents:
                    recent_by_id = {i["id_arsip"]:i for i in recents}
                    selected = st.selectbox("Riwayat tersimpan", options=list(recent_by_id),
                                            format_func=lambda x: f"{recent_by_id[x]['nama_proyek']} | {recent_by_id[x]['dibuat_utc']} | {x[:8]}")
                    old_bytes = store.load(selected)
                    offer_download("Download arsip dari SQLite", old_bytes,
                                       file_name=f"riwayat_{selected}.k4proj.zip", mime="application/zip")
                    if st.button("Pulihkan versi terpilih ke sesi", key="k4_restore_local"):
                        pulihkan_dari_arsip(old_bytes)
                        st.rerun()
                else:
                    st.caption("Belum ada riwayat lokal tersimpan.")
            except (ProjectArchiveError, OSError, ValueError) as exc:
                st.error(f"Riwayat lokal tidak dapat digunakan: {exc}")
        else:
            st.info("Riwayat SQLite sengaja **nonaktif** pada deployment publik. "
                    "Untuk instalasi **lokal pribadi**, aktifkan variabel lingkungan "
                    "`K4_ENABLE_LOCAL_HISTORY=1`. Arsip portabel tetap bisa disimpan dan dibuka tanpa database.")
        st.caption("Untuk penggunaan laboratorium multiuser yang sebenarnya, diperlukan backend database terkelola, "
                   "autentikasi, pembatasan akses, backup, dan audit keamanan sebelum menyimpan data proyek permanen.")

    # ---------------------------------------------------------------------------
    # v5.0 — Pelacakan benda uji dan jadwal. Tanggal tidak ditebak dari CSV lama.
    # ---------------------------------------------------------------------------
else:
    with tabs[9]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

if permitted('tracking'):
    with tabs[10]:
        st.markdown('### Manajemen Sampel & Jadwal Pengujian')
        st.caption('Alat pencatatan operasional: tanggal pengecoran dan tanggal aktual harus diisi pengguna. '
                   'Tidak mengubah perhitungan kuat tekan maupun simulasi penerimaan SNI.')
        st.info('Data registrasi hanya ada di sesi browser. Untuk menyimpannya, unduh CSV registrasi. '
                'Saat website dibuka kembali, unggah CSV utama dan registrasi hasil unduhan.')

        # Fingerprint mengikuti data utama; pindah tab tidak menghapus registrasi.
        hash_utama = hashlib.sha256(h.input_data.to_csv(index=False).encode('utf-8')).hexdigest()[:16]
        k_base = 'k4_tracker_source'
        k_df = 'k4_tracker_records'
        k_rev = 'k4_tracker_revision'
        ids_utama = h.input_data['id_benda_uji'].astype(str).tolist()
        camp_map = dict(zip(h.input_data['id_benda_uji'].astype(str), h.input_data['campuran'].astype(str)))
        if st.session_state.get(k_base) != hash_utama:
            st.session_state[k_base] = hash_utama
            st.session_state[k_df] = buat_template_registrasi(h.input_data)
            st.session_state[k_rev] = 0
            st.session_state.pop('k4_tracker_import_hash', None)
        st.markdown('#### 1. Isi data registrasi')
        st.caption('Kolom tanggal harus ditulis sebagai **YYYY-MM-DD**. Kosong berarti belum diketahui. '
                   'Tanggal pengecoran tidak diisi otomatis agar tidak menimbulkan data laboratorium fiktif.')
        upload_register = st.file_uploader(
            'Impor CSV registrasi yang pernah disimpan (opsional)',
            type=['csv'], key=f'k4_tracker_import_{hash_utama}',
            help='Gunakan CSV registrasi yang diunduh dari aplikasi ini; ID harus sama dengan CSV utama.'
        )
        if upload_register is not None:
            incoming_bytes = upload_register.getvalue()
            incoming_hash = hashlib.sha256(incoming_bytes).hexdigest()
            if st.session_state.get('k4_tracker_import_hash') != incoming_hash:
                try:
                    if len(incoming_bytes) > 10 * 1024 * 1024:
                        raise TrackingError('CSV registrasi terlalu besar (maksimal 10 MB).')
                    incoming = pd.read_csv(BytesIO(incoming_bytes), dtype=str, keep_default_na=False, encoding='utf-8-sig')
                    incoming = validasi_registrasi(incoming, ids_utama)
                    # Campuran selalu merujuk data utama, bukan CSV registrasi.
                    incoming['campuran'] = incoming['id_benda_uji'].map(camp_map)
                    st.session_state[k_df] = incoming
                    st.session_state[k_rev] += 1
                    st.session_state['k4_tracker_import_hash'] = incoming_hash
                    st.success('Registrasi CSV dipulihkan. Silakan periksa tanggalnya di tabel.')
                except (TrackingError, ValueError, pd.errors.ParserError, UnicodeDecodeError) as err:
                    st.error(f'Impor registrasi gagal: {err}')

        col_batch, col_fill = st.columns([1.6, 1], gap='small')
        with col_batch:
            mass_date = st.date_input('Tanggal pengecoran untuk pengisian massal (opsional)',
                                      value=None, key='k4_tracker_batch_date')
        with col_fill:
            st.write('')
            fill_batch = st.button('Isi tanggal kosong', key='k4_tracker_fill_dates',
                                   help='Hanya mengisi tanggal cetak yang masih kosong; tidak menimpa yang sudah diisi.')
        if fill_batch:
            if mass_date is None:
                st.warning('Pilih tanggal pengecoran terlebih dahulu.')
            else:
                reg = st.session_state[k_df].copy()
                mask=reg['tanggal_cetak'].fillna('').astype(str).str.strip().eq('')
                reg.loc[mask,'tanggal_cetak'] = mass_date.isoformat()
                st.session_state[k_df] = reg
                st.session_state[k_rev] += 1
                st.rerun()

        edit_key=f'k4_tracker_editor_{hash_utama}_{st.session_state[k_rev]}'
        edited_reg = st.data_editor(
            st.session_state[k_df], hide_index=True, num_rows='fixed',
            disabled=['id_benda_uji','campuran'], use_container_width=True,
            key=edit_key,
            column_config={
                'id_benda_uji': st.column_config.TextColumn('ID sampel'),
                'campuran': st.column_config.TextColumn('Campuran'),
                'tanggal_cetak': st.column_config.TextColumn('Tanggal pengecoran (YYYY-MM-DD)'),
                'umur_rencana_hari': st.column_config.NumberColumn('Umur rencana (hari)', min_value=1, max_value=3650, step=1),
                'tanggal_uji_aktual': st.column_config.TextColumn('Tanggal uji aktual (YYYY-MM-DD)'),
            }
        )
        # Tanggal tidak diisi secara implisit; keadaan editor ini hanya ada di sesi.
        st.session_state[k_df] = edited_reg.copy()
        try:
            reg_valid = validasi_registrasi(edited_reg, ids_utama)
            reg_valid['campuran'] = reg_valid['id_benda_uji'].map(camp_map)
        except TrackingError as err:
            st.error(f'Perbaiki registrasi sebelum melihat jadwal: {err}')
            st.stop()

        offer_download('⬇️ Simpan registrasi (.csv)', export_registrasi_csv(reg_valid),
                           file_name='registrasi_sampel_k4.csv', mime='text/csv',
                           key='k4_tracker_download_registration')
        st.divider()
        st.markdown('#### 2. Jadwal dan status')
        # Kalender berdasarkan tanggal Jakarta. Aplikasi cloud dapat berada di zona waktu lain.
        try:
            acuan_default = pd.Timestamp.now(tz='Asia/Jakarta').date()
        except Exception:
            acuan_default = date.today()
        acuan=st.date_input('Tanggal acuan peninjauan', value=acuan_default,
                            key='k4_tracker_asof', help='Ganti tanggal untuk meninjau jadwal pada hari lain.')
        schedule=jadwal_pengujian(reg_valid, tanggal_acuan=acuan)
        status_counts=schedule['status_jadwal'].value_counts().to_dict()
        cells=st.columns(4)
        cells[0].metric('Total sampel',len(schedule))
        cells[1].metric('Terjadwal',status_counts.get('Terjadwal',0))
        cells[2].metric('Jatuh tempo / terlambat',status_counts.get('Jatuh tempo',0)+status_counts.get('Terlambat',0))
        cells[3].metric('Sudah diuji',status_counts.get('Sudah diuji',0)+status_counts.get('Diuji lebih awal',0))
        st.caption('Status ini hanya berdasarkan tanggal, **bukan hasil lulus/tidak lulus mutu**. '
                   'Sampel pada CSV awal belum otomatis dianggap sudah diuji sampai tanggal aktual diisi.')
        pilih_status=st.multiselect('Filter status jadwal', options=sorted(schedule['status_jadwal'].unique()),
                                     default=sorted(schedule['status_jadwal'].unique()),key='k4_tracker_status_filter')
        filtered=schedule[schedule['status_jadwal'].isin(pilih_status)]
        st.dataframe(filtered,hide_index=True,use_container_width=True,
                     column_config={'sisa_hari':st.column_config.NumberColumn('Hari menuju jadwal', format='%d')})
        if status_counts.get('Terlambat',0):
            st.warning(f"Ada {status_counts['Terlambat']} sampel dengan jadwal terlewat berdasarkan tanggal acuan. "
                       'Verifikasi apakah pengujiannya sudah dilakukan sebelum mengambil tindakan.')
        pending=schedule[schedule['status_jadwal'].isin(['Terjadwal', 'Jatuh tempo','Terlambat'])]
        if not pending.empty:
            per_tanggal=pending.groupby(['tanggal_jadwal','campuran'],as_index=False).size().rename(columns={'size':'jumlah'})
            fig_jadwal=px.bar(per_tanggal,x='tanggal_jadwal',y='jumlah',color='campuran',
                              barmode='group',color_discrete_sequence=PALETTE,
                              title='Jumlah sampel per tanggal rencana pengujian',
                              labels={'tanggal_jadwal':'Tanggal pengujian','jumlah':'Jumlah sampel','campuran':'Campuran'})
            fig_jadwal.update_layout(margin=dict(l=10,r=10,t=55,b=10),
                                     plot_bgcolor='#FFFFFF',paper_bgcolor='#FFFFFF')
            st.plotly_chart(fig_jadwal,use_container_width=True,key='k4_tracking_schedule_chart')
        st.divider()
        st.markdown('#### Cari sampel dengan hasil scan QR')
        scan_value=st.text_input('Tempel kode QR dari pemindai atau hasil scan HP',
                                placeholder='K4S1-...',key='k4_tracking_scan_lookup')
        if scan_value.strip():
            lookup = {kode_qr_sampel(nama_proyek, r['id_benda_uji']):r for _,r in schedule.iterrows()}
            item = lookup.get(scan_value.strip().upper())
            if item is None:
                st.warning('Kode tidak ditemukan pada registrasi ini. Pastikan nama proyek dan CSV sama.')
            else:
                st.success(f"Sampel ditemukan: {item['id_benda_uji']} • Campuran {item['campuran']}")
                st.write(f"Status: **{item['status_jadwal']}** • Rencana: {item['tanggal_jadwal'] or 'Belum ada'}")
        st.caption('Pindai QR menggunakan kamera/QR scanner HP, lalu tempel kodenya ke sini. '
                   'Pemindaian langsung di dalam browser dan verifikasi online belum tersedia.')
        st.divider()
        st.markdown('#### 3. Ekspor kalender dan label QR')
        c_ics,c_qr=st.columns(2,gap='medium')
        with c_ics:
            ics_data=kalender_ics(schedule,nama_proyek=nama_proyek)
            offer_download('📆 Unduh jadwal (.ics)',ics_data,
                               file_name='jadwal_uji_beton.ics',mime='text/calendar',
                               use_container_width=True,key='k4_tracker_calendar_download')
            st.caption('Dapat diimpor ke aplikasi kalender. Kalender berisi sampel yang belum ditandai sudah diuji.')
        with c_qr:
            if permitted('exports') and st.button('Siapkan PDF label QR',key='k4_tracker_prepare_labels',use_container_width=True):
                with st.spinner('Membuat label...'):
                    st.session_state['k4_tracker_pdf_label'] = label_qr_pdf(reg_valid, nama_proyek=nama_proyek)
                    st.session_state['k4_tracker_pdf_key'] = (hash_utama,nama_proyek,hashlib.sha256(export_registrasi_csv(reg_valid)).hexdigest())
            expected=(hash_utama,nama_proyek,hashlib.sha256(export_registrasi_csv(reg_valid)).hexdigest())
            if st.session_state.get('k4_tracker_pdf_key') == expected:
                offer_download('⬇️ Download label QR (.pdf)',st.session_state['k4_tracker_pdf_label'],
                                   file_name='label_qr_benda_uji.pdf',mime='application/pdf',
                                   key='k4_tracker_label_download',use_container_width=True)
            st.caption('QR hanya berisi identitas sampel yang di-hash, **belum terhubung ke database atau halaman verifikasi online**.')
        st.caption('Pengingat otomatis ke WhatsApp/email belum tersedia. File kalender hanya dibuat saat pengguna mengunduhnya.')
else:
    with tabs[10]:
        st.info('Fitur ini belum diizinkan untuk pengguna tamu. Masuk dengan akun yang telah disetujui.')

