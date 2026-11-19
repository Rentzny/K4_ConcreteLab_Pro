"""Audit CSV yang ramah pengguna: baris, kolom, tingkat masalah, dan solusi.

Fungsi ini tidak mengubah CSV dan bukan pengganti validasi mesin analisis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import REQUIRED_COLUMNS, NUMERIC_COLUMNS

AUDIT_COLUMNS = ["baris_csv", "kolom", "tingkat", "masalah", "saran_perbaikan"]
MAX_ISSUES = 2500


def audit_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Kembalikan temuan validasi dengan nomor baris CSV (header = baris 1)."""
    findings: list[dict] = []

    def add(row: int, col: str, level: str, msg: str, fix: str) -> None:
        if len(findings) < MAX_ISSUES:
            findings.append(dict(baris_csv=row, kolom=col, tingkat=level,
                                 masalah=msg, saran_perbaikan=fix))

    if df is None or df.empty:
        add(0, "(berkas)", "Error", "CSV tidak berisi benda uji.", "Tambahkan baris data sesuai template.")
        return pd.DataFrame(findings, columns=AUDIT_COLUMNS)
    d = df.copy()
    d.columns = [str(c).strip().replace("\ufeff", "") for c in d.columns]
    duplicated_names = pd.Index(d.columns)[pd.Index(d.columns).duplicated()].unique()
    for col in duplicated_names:
        add(1, col, "Error", "Nama kolom duplikat.", "Hapus atau ubah nama kolom yang berulang.")
    if len(duplicated_names):
        return pd.DataFrame(findings, columns=AUDIT_COLUMNS)
    for col in REQUIRED_COLUMNS:
        if col not in d.columns:
            add(1, col, "Error", "Kolom wajib tidak ditemukan.", "Tambahkan kolom sesuai template CSV.")
    if len(d) > 10000:
        add(0, "(berkas)", "Error", "Lebih dari 10.000 baris.", "Bagi data menjadi beberapa CSV.")

    for col in ("id_benda_uji", "campuran", "id_pengujian"):
        if col not in d:
            continue
        s = d[col].astype("string").str.strip()
        missing = s.isna() | s.eq("")
        for i in np.flatnonzero(missing.fillna(True).to_numpy()):
            add(int(i)+2, col, "Error", "Identitas kosong.", "Isi identitas yang sesuai.")
        if col == "id_benda_uji":
            duplicated = s.duplicated(keep=False) & ~missing
            for i in np.flatnonzero(duplicated.fillna(False).to_numpy()):
                add(int(i)+2, col, "Error", "ID benda uji duplikat.", "Gunakan ID unik per silinder.")

    for col in NUMERIC_COLUMNS:
        if col not in d:
            continue
        n = pd.to_numeric(d[col], errors="coerce")
        numeric = n.to_numpy(dtype=float, na_value=np.nan)
        invalid = ~np.isfinite(numeric)
        for i in np.flatnonzero(invalid):
            add(int(i)+2, col, "Error", "Nilai bukan angka yang valid.", "Isi angka dengan satuan yang benar.")
        for i in np.flatnonzero(np.isfinite(numeric) & (numeric <= 0)):
            add(int(i)+2, col, "Error", "Nilai harus lebih besar dari nol.", "Ganti dengan data pengujian positif.")
        if col == "umur_hari":
            for i in np.flatnonzero(np.isfinite(numeric) & (numeric > 0) & (numeric != 28)):
                add(int(i)+2, col, "Peringatan", "Umur bukan 28 hari.", "Periksa asumsi evaluasi SNI; perhitungan fc tetap dapat dilakukan.")
        if col == "diameter_mm":
            for i in np.flatnonzero(np.isfinite(numeric) & (numeric > 0) & ~np.isclose(numeric, 150, atol=.1)):
                add(int(i)+2, col, "Peringatan", "Diameter berbeda dari 150 mm.", "Tinjau asumsi pasangan silinder dan dimensi sampel.")

    if "urutan_uji" not in d.columns:
        add(0, "urutan_uji", "Peringatan", "Urutan pengujian belum dicantumkan.",
            "Tambahkan urutan_uji untuk evaluasi tiga hasil uji berurutan yang lebih jelas.")
    else:
        order = pd.to_numeric(d["urutan_uji"], errors="coerce")
        order_array = order.to_numpy(dtype=float, na_value=np.nan)
        invalid = (~np.isfinite(order_array)) | (order_array <= 0) | (order_array % 1 != 0)
        for i in np.flatnonzero(invalid):
            add(int(i)+2, "urutan_uji", "Error", "Urutan uji tidak sah.", "Gunakan bilangan bulat positif.")
        if not invalid.any() and all(c in d for c in ["campuran", "id_pengujian"]):
            t = d.assign(urutan_uji=order.astype(int))
            for (mix, test), group in t.groupby(["campuran", "id_pengujian"], dropna=False):
                if group["urutan_uji"].nunique() != 1:
                    for i in group.index:
                        add(int(i)+2, "urutan_uji", "Error", "Satu ID pengujian memiliki urutan berbeda.", "Samakan urutan untuk kedua silinder dalam satu pengujian.")
            for (mix, order_no), group in t.groupby(["campuran", "urutan_uji"], dropna=False):
                if group["id_pengujian"].nunique() != 1:
                    for i in group.index:
                        add(int(i)+2, "urutan_uji", "Error", "Satu urutan digunakan oleh ID pengujian berbeda.", "Bedakan urutan pengujian.")

    if "campuran" in d and "id_pengujian" in d:
        for (mix, test), group in d.groupby(["campuran", "id_pengujian"], dropna=False):
            if len(group) != 2:
                add(int(group.index[0])+2, "id_pengujian", "Peringatan",
                    f"Pengujian {test!s} (campuran {mix!s}) berisi {len(group)} silinder.",
                    "Simulasi penerimaan mengasumsikan dua silinder per hasil uji.")

    if all(c in d for c in ["diameter_mm", "beban_maksimum_kN"]):
        diameter = pd.to_numeric(d["diameter_mm"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        load = pd.to_numeric(d["beban_maksimum_kN"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            fc = load * 1000 / (np.pi * diameter**2 / 4)
        for i in np.flatnonzero(np.isfinite(fc) & ((fc < 5) | (fc > 120))):
            add(int(i)+2, "kuat_tekan_MPa", "Peringatan",
                f"Kuat tekan terhitung {fc[i]:.2f} MPa berada di luar rentang skrining 5–120 MPa.",
                "Cek ulang beban, diameter, dan satuan; rentang ini bukan batas standar.")
    if len(findings) >= MAX_ISSUES:
        findings.append(dict(baris_csv=0, kolom="(berkas)", tingkat="Peringatan",
                             masalah="Daftar temuan dibatasi 2.500 baris agar dashboard responsif.",
                             saran_perbaikan="Perbaiki temuan pertama lalu unggah ulang."))
    return pd.DataFrame(findings, columns=AUDIT_COLUMNS)


def audit_counts(audit: pd.DataFrame) -> dict[str, int]:
    """Hitung error dan peringatan; tidak menafsirkan jumlah temuan sebagai jumlah baris."""
    return {"error": int((audit.tingkat == "Error").sum()),
            "peringatan": int((audit.tingkat == "Peringatan").sum())}
