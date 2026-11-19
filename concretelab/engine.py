"""Mesin hitung K4 ConcreteLab Pro. Tidak bergantung pada Streamlit.

Semua satuan eksplisit: diameter mm, beban kN, luas mm2, kuat tekan MPa.
Evaluasi SNI di sini SIMULASI terbatas pada asumsi spesimen proyek K4:
2 silinder diameter 150 mm/hasil uji, umur 28 hari, urutan uji diketahui.
Bukan keputusan penerimaan beton lapangan.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import hashlib
import math
from typing import BinaryIO

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "id_benda_uji", "campuran", "umur_hari", "diameter_mm",
    "beban_maksimum_kN", "id_pengujian",
]
OPTIONAL_COLUMNS = ["urutan_uji"]
NUMERIC_COLUMNS = ["umur_hari", "diameter_mm", "beban_maksimum_kN"]


class DataValidationError(ValueError):
    """Kesalahan input yang dapat ditampilkan ke pengguna secara aman."""
    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class BendaUji:
    kode: str
    campuran: str
    diameter_mm: float
    beban_kN: float

    def hitung_luas(self) -> float:
        """Luas penampang beton silinder (mm²)."""
        if not math.isfinite(self.diameter_mm) or self.diameter_mm <= 0:
            raise ValueError("Diameter harus positif dan terhingga.")
        return math.pi * self.diameter_mm ** 2 / 4

    def hitung_kuat_tekan(self) -> float:
        """Kuat tekan beton (MPa = N/mm²)."""
        if not math.isfinite(self.beban_kN) or self.beban_kN <= 0:
            raise ValueError("Beban harus positif dan terhingga.")
        return self.beban_kN * 1000 / self.hitung_luas()


@dataclass
class HasilAnalisis:
    input_data: pd.DataFrame
    benda_uji: pd.DataFrame
    statistik: pd.DataFrame
    rekap_uji: pd.DataFrame
    evaluasi: pd.DataFrame
    jendela_tiga_uji: pd.DataFrame
    peringatan: list[str]
    mutu_rencana: float
    sumber_data: str
    hash_sumber: str

    @property
    def ringkasan(self) -> dict:
        d = self.benda_uji
        status = self.evaluasi["status"].value_counts().to_dict()
        return {
            "silinder": int(len(d)),
            "campuran": int(d["campuran"].nunique()),
            "jumlah_uji": int(len(self.rekap_uji)),
            "mencapai_target": int((d["kuat_tekan_MPa"] >= self.mutu_rencana).sum()),
            "di_bawah_target": int((d["kuat_tekan_MPa"] < self.mutu_rencana).sum()),
            "indikasi_outlier": int((d["status_outlier"] == "Indikasi outlier").sum()),
            "campuran_memenuhi_simulasi": int(status.get("Memenuhi simulasi", 0)),
            "campuran_tidak_memenuhi": int(status.get("Belum memenuhi simulasi", 0)),
            "campuran_belum_dapat_dinilai": int(status.get("Tidak dapat dievaluasi", 0)),
        }


def read_csv(source: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    """Membaca CSV UTF-8 (termasuk BOM). Batas unggahan diatur di UI."""
    try:
        if isinstance(source, bytes):
            return pd.read_csv(BytesIO(source), encoding="utf-8-sig")
        return pd.read_csv(source, encoding="utf-8-sig")
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataValidationError([f"CSV tidak dapat dibaca: {exc}"]) from exc
    except FileNotFoundError as exc:
        raise DataValidationError([f"File CSV tidak ditemukan: {exc.filename}"]) from exc


def validasi_input(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Validasi keras pada data utama, peringatan untuk asumsi uji mutu."""
    masalah, peringatan = [], []
    if df is None or df.empty:
        raise DataValidationError(["CSV kosong; tambahkan minimal satu baris data."])

    cleaned = df.copy()
    cleaned.columns = [str(x).strip().replace("\ufeff", "") for x in cleaned.columns]
    duplicate_cols = pd.Index(cleaned.columns).duplicated()
    if duplicate_cols.any():
        masalah.append("Nama kolom duplikat: " + ", ".join(pd.Index(cleaned.columns)[duplicate_cols]))
    missing = [c for c in REQUIRED_COLUMNS if c not in cleaned.columns]
    if missing:
        masalah.append("Kolom wajib belum ada: " + ", ".join(missing))
    if masalah:
        raise DataValidationError(masalah)
    if len(cleaned) > 10000:
        raise DataValidationError(["Maksimal 10.000 baris per analisis untuk menjaga kinerja."])

    for col in ("id_benda_uji", "campuran", "id_pengujian"):
        raw = cleaned[col]
        missing_mask = raw.isna() | raw.astype(str).str.strip().isin(["", "nan", "None"])
        if missing_mask.any():
            masalah.append(f"Kolom '{col}' kosong pada baris data: {', '.join(str(i+2) for i in cleaned.index[missing_mask][:8])}.")
        cleaned[col] = raw.astype(str).str.strip()

    if cleaned["id_benda_uji"].duplicated().any():
        duplicates = cleaned.loc[cleaned["id_benda_uji"].duplicated(keep=False), "id_benda_uji"].unique().tolist()
        masalah.append("ID benda uji harus unik; duplikat: " + ", ".join(duplicates[:8]))

    for col in NUMERIC_COLUMNS:
        values = pd.to_numeric(cleaned[col], errors="coerce")
        invalid = values.isna() | ~np.isfinite(values)
        if invalid.any():
            masalah.append(f"Kolom '{col}' memiliki angka tidak valid pada baris data: {', '.join(str(i+2) for i in cleaned.index[invalid][:8])}.")
        bad_positive = values.notna() & np.isfinite(values) & (values <= 0)
        if bad_positive.any():
            masalah.append(f"Kolom '{col}' harus > 0 pada baris data: {', '.join(str(i+2) for i in cleaned.index[bad_positive][:8])}.")
        cleaned[col] = values

    if "urutan_uji" in cleaned.columns:
        order = pd.to_numeric(cleaned["urutan_uji"], errors="coerce")
        if order.isna().any() or not np.isfinite(order).all() or (order <= 0).any() or (order % 1 != 0).any():
            masalah.append("'urutan_uji' opsional harus berisi bilangan bulat positif untuk setiap baris jika digunakan.")
        else:
            cleaned["urutan_uji"] = order.astype(int)
            conflicted = cleaned.groupby(["campuran", "id_pengujian"])["urutan_uji"].nunique()
            if (conflicted > 1).any():
                masalah.append("Dalam satu campuran dan id_pengujian, 'urutan_uji' harus sama untuk seluruh silinder.")
            distinct_order = cleaned.groupby(["campuran", "urutan_uji"])["id_pengujian"].nunique()
            if (distinct_order > 1).any():
                masalah.append("Dalam satu campuran, setiap 'urutan_uji' harus merujuk ke satu id_pengujian.")

    if masalah:
        raise DataValidationError(masalah)

    if not (cleaned["umur_hari"] == 28).all():
        peringatan.append("Ada umur pengujian bukan 28 hari; evaluasi penerimaan simulasi hanya dilakukan untuk campuran yang seluruh datanya berumur 28 hari.")
    if not np.isclose(cleaned["diameter_mm"], 150.0, atol=0.1).all():
        peringatan.append("Ada diameter bukan 150 mm; evaluasi simulasi dua silinder/hasil uji dibatasi pada spesimen diameter 150 mm.")
    if "urutan_uji" not in cleaned.columns:
        peringatan.append("Kolom 'urutan_uji' belum ada: urutan tiga hasil uji diasumsikan dari pengurutan ID pengujian; konfirmasi sebelum penggunaan lapangan.")
    counts = cleaned.groupby(["campuran", "id_pengujian"]).size()
    if (counts != 2).any():
        peringatan.append("Beberapa ID pengujian tidak memiliki tepat dua silinder; campuran terkait akan ditandai tidak dapat dievaluasi untuk simulasi SNI.")
    if cleaned["campuran"].nunique() > 25:
        peringatan.append("Jumlah campuran >25; visualisasi bisa menjadi padat.")
    if (cleaned["beban_maksimum_kN"] > 15000).any():
        peringatan.append("Ada beban >15.000 kN. Pastikan satuan masukan benar.")
    return cleaned.reset_index(drop=True), peringatan


def olah_data_beton(df: pd.DataFrame) -> pd.DataFrame:
    """Menambahkan luas (mm²) dan kuat tekan (MPa) dengan class BendaUji."""
    rows = df.copy()
    specimen = [BendaUji(str(r.id_benda_uji), str(r.campuran), float(r.diameter_mm), float(r.beban_maksimum_kN)) for r in rows.itertuples(index=False)]
    rows["luas_mm2"] = [x.hitung_luas() for x in specimen]
    rows["kuat_tekan_MPa"] = [x.hitung_kuat_tekan() for x in specimen]
    return rows


def statistik_campuran(df: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan statistik setiap campuran untuk SILINDER individual."""
    stat = df.groupby("campuran", sort=True)["kuat_tekan_MPa"].agg(
        jumlah="count", rata_rata="mean", simpangan_baku="std", minimum="min", maksimum="max", median="median"
    ).reset_index()
    stat["cv_persen"] = np.where(stat["rata_rata"] > 0, stat["simpangan_baku"] / stat["rata_rata"] * 100, np.nan)
    return stat


def periksa_outlier(df: pd.DataFrame) -> pd.DataFrame:
    """Screening ±2 SD per campuran jika n>=5; bukan bukti data invalid."""
    data = df.copy()
    data["status_outlier"] = "Normal"
    for campuran, idx in data.groupby("campuran").groups.items():
        nilai = data.loc[idx, "kuat_tekan_MPa"]
        if len(nilai) < 5:
            data.loc[idx, "status_outlier"] = "Data belum cukup"
            continue
        sd = nilai.std(ddof=1)
        if not np.isfinite(sd) or sd == 0:
            continue
        mask = abs(nilai - nilai.mean()) > 2 * sd
        data.loc[nilai.index[mask], "status_outlier"] = "Indikasi outlier"
    return data


def rekap_hasil_uji(df: pd.DataFrame) -> pd.DataFrame:
    """Satu hasil uji = rerata dua silinder satu pasangan pengujian."""
    agg = {
        "jumlah_silinder": ("id_benda_uji", "count"),
        "kuat_tekan_uji_MPa": ("kuat_tekan_MPa", "mean"),
        "umur_min": ("umur_hari", "min"),
        "umur_max": ("umur_hari", "max"),
        "diameter_min": ("diameter_mm", "min"),
        "diameter_max": ("diameter_mm", "max"),
    }
    if "urutan_uji" in df.columns:
        agg["urutan_uji"] = ("urutan_uji", "min")
    tests = df.groupby(["campuran", "id_pengujian"], as_index=False).agg(**agg)
    sort_columns = ["campuran", "urutan_uji"] if "urutan_uji" in tests.columns else ["campuran", "id_pengujian"]
    return tests.sort_values(sort_columns, kind="stable").reset_index(drop=True)


def evaluasi_tiga_uji(tests: pd.DataFrame, fc_target: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulasi dua kriteria numerik penerimaan; menolak asumsi uji tidak valid."""
    lower_limit = fc_target - 3.5 if fc_target <= 35 else 0.90 * fc_target
    eval_rows, window_rows = [], []
    for mix, t in tests.groupby("campuran", sort=True):
        t = t.sort_values("urutan_uji" if "urutan_uji" in t.columns else "id_pengujian", kind="stable")
        reasons = []
        if len(t) < 3:
            reasons.append("Kurang dari tiga hasil uji")
        if (t["jumlah_silinder"] != 2).any():
            reasons.append("Ada hasil uji dengan jumlah silinder bukan 2")
        if not ((t["umur_min"] == 28) & (t["umur_max"] == 28)).all():
            reasons.append("Ada silinder yang bukan umur 28 hari")
        if not (np.isclose(t["diameter_min"], 150, atol=0.1) & np.isclose(t["diameter_max"], 150, atol=0.1)).all():
            reasons.append("Ada silinder yang diameternya bukan 150 mm")
        val = t["kuat_tekan_uji_MPa"].astype(float)
        rolling = val.rolling(3).mean()
        for i in range(2, len(t)):
            item = t.iloc[i-2:i+1]
            avg = float(rolling.iloc[i])
            window_rows.append({
                "campuran": mix,
                "rentang_uji": " - ".join(item["id_pengujian"].astype(str)),
                "rata_3_uji_MPa": avg,
                "target_MPa": fc_target,
                "memenuhi_rata": avg >= fc_target,
            })
        lowest_avg = float(rolling.dropna().min()) if len(t) >= 3 else float("nan")
        lowest_val = float(val.min())
        if reasons:
            status = "Tidak dapat dievaluasi"
        else:
            status = "Memenuhi simulasi" if (lowest_avg >= fc_target and lowest_val >= lower_limit) else "Belum memenuhi simulasi"
        eval_rows.append({
            "campuran": mix,
            "jumlah_uji": len(t),
            "rata_3_terendah_MPa": lowest_avg,
            "uji_terendah_MPa": lowest_val,
            "batas_uji_MPa": lower_limit,
            "jumlah_jendela_3_uji": max(len(t)-2, 0),
            "status": status,
            "catatan": "; ".join(reasons) if reasons else ("Semua jendela dinilai" if "urutan_uji" in t.columns else "Urutan diasumsikan dari ID pengujian"),
        })
    return pd.DataFrame(eval_rows), pd.DataFrame(window_rows, columns=["campuran", "rentang_uji", "rata_3_uji_MPa", "target_MPa", "memenuhi_rata"])


def analisis(df: pd.DataFrame, fc_target: float = 30.0, sumber: str = "Data ilustratif", raw_bytes: bytes | None = None) -> HasilAnalisis:
    """Satu pintu pengolahan untuk UI, CLI, ekspor, dan laporan PDF."""
    if not isinstance(fc_target, (int, float)) or not math.isfinite(fc_target) or fc_target <= 0 or fc_target > 150:
        raise DataValidationError(["Target kuat tekan harus >0 dan <=150 MPa."])
    clean, peringatan = validasi_input(df)
    result = periksa_outlier(olah_data_beton(clean))
    result["status_target"] = np.where(result["kuat_tekan_MPa"] >= fc_target, "Mencapai target", "Di bawah target")
    stats = statistik_campuran(result)
    tests = rekap_hasil_uji(result)
    evals, windows = evaluasi_tiga_uji(tests, fc_target)
    math_expected = clean["beban_maksimum_kN"] * 1000 / (math.pi * clean["diameter_mm"] ** 2 / 4)
    if not np.allclose(result["kuat_tekan_MPa"].to_numpy(), math_expected.to_numpy(), atol=1e-10, rtol=1e-12):
        raise RuntimeError("Validasi rumus internal gagal.")
    if int(tests["jumlah_silinder"].sum()) != len(clean):
        raise RuntimeError("Jumlah rekap tidak konsisten.")
    if raw_bytes is None:
        raw_bytes = clean.to_csv(index=False).encode("utf-8")
    return HasilAnalisis(clean, result, stats, tests, evals, windows, peringatan, float(fc_target), sumber, hashlib.sha256(raw_bytes).hexdigest())
