"""Eksperimen skenario numerik terpisah dari data utama, tanpa mengubah data pengguna."""
from __future__ import annotations

import math
import pandas as pd

from .engine import HasilAnalisis, analisis, DataValidationError


def simulasi_beban(hasil: HasilAnalisis, persen: float) -> HasilAnalisis:
    """Skenario perubahan seragam beban maksimum (persen), hanya untuk studi sensitivitas."""
    if not isinstance(persen, (int, float)) or not math.isfinite(persen) or persen <= -100 or persen > 300:
        raise DataValidationError(["Perubahan beban harus lebih besar -100% dan maksimal +300%."])
    altered = hasil.input_data.copy(deep=True)
    altered["beban_maksimum_kN"] = altered["beban_maksimum_kN"] * (1 + persen / 100)
    return analisis(altered, hasil.mutu_rencana,
                    sumber=f"SIMULASI BEBAN {persen:+g}% — bukan hasil laboratorium", 
                    raw_bytes=altered.to_csv(index=False).encode("utf-8"))


def tabel_skenario(hasil: HasilAnalisis, persen: list[float]) -> pd.DataFrame:
    """Ringkasan sensitivitas tiap campuran ketika seluruh beban diskalakan."""
    rows = []
    for p in persen:
        v = simulasi_beban(hasil, p)
        e = v.evaluasi.set_index("campuran")
        for _,r in v.statistik.iterrows():
            rows.append({"perubahan_beban_persen": float(p), "campuran": r["campuran"],
                         "rata_rata_MPa": float(r["rata_rata"]),
                         "cv_persen": float(r["cv_persen"]) if pd.notna(r["cv_persen"]) else float("nan"),
                         "status_simulasi": e.loc[r["campuran"], "status"]})
    return pd.DataFrame(rows)


def bandingkan_dua_analisis(utama: HasilAnalisis, kedua: HasilAnalisis) -> pd.DataFrame:
    """Perbandingan ringkas berdasarkan nama campuran; tidak menggabungkan sampel."""
    a = utama.statistik[["campuran", "jumlah", "rata_rata", "cv_persen"]].rename(columns={
        "jumlah":"n_A", "rata_rata":"rata_A_MPa", "cv_persen":"cv_A_persen"})
    b = kedua.statistik[["campuran", "jumlah", "rata_rata", "cv_persen"]].rename(columns={
        "jumlah":"n_B", "rata_rata":"rata_B_MPa", "cv_persen":"cv_B_persen"})
    df = a.merge(b, on="campuran", how="outer", validate="one_to_one").sort_values("campuran").reset_index(drop=True)
    df["selisih_B_minus_A_MPa"] = df["rata_B_MPa"] - df["rata_A_MPa"]
    return df
