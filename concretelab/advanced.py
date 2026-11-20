"""Statistik deskriptif lanjutan dan sensitivitas target untuk ConcreteLab Pro.

Modul ini bebas Streamlit sehingga dapat diuji terpisah. Seluruh analisis
menggunakan data aktif; tidak mengubah objek hasil atau CSV pengguna.

Catatan: bootstrap adalah ilustrasi ketidakpastian rata-rata sampel, bukan
interval penerimaan mutu beton maupun hasil validasi laboratorium.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
import numpy as np
import pandas as pd

from .engine import HasilAnalisis, DataValidationError, evaluasi_tiga_uji


def statistik_lanjutan(
    hasil: HasilAnalisis,
    tingkat: str = "silinder",
    *,
    bootstrap_iterasi: int = 2500,
    seed: int = 2026,
) -> pd.DataFrame:
    """Menyajikan distribusi, kuartil, CV dan CI bootstrap mean 95% tiap campuran.

    tingkat: 'silinder' = setiap benda uji; 'hasil_uji' = mean pasangan silinder.
    CI hanya dihitung apabila n >= 5. Dengan sampel kecil, CI bersifat
    ilustratif; n < 5 diberi NaN (bukan nol) agar tidak memberi kesan presisi.
    """
    if tingkat not in {"silinder", "hasil_uji"}:
        raise ValueError("tingkat harus 'silinder' atau 'hasil_uji'.")
    if not isinstance(bootstrap_iterasi, int) or not 200 <= bootstrap_iterasi <= 20_000:
        raise ValueError("bootstrap_iterasi harus integer antara 200 dan 20000.")
    df, key = ((hasil.benda_uji, "kuat_tekan_MPa") if tingkat == "silinder"
               else (hasil.rekap_uji, "kuat_tekan_uji_MPa"))
    rows: list[dict] = []
    for campuran, group in df.groupby("campuran", sort=True):
        v = group[key].to_numpy(dtype=float, copy=True)
        v = v[np.isfinite(v)]
        if len(v) == 0:
            continue
        n = len(v)
        mean = float(np.mean(v))
        sd = float(np.std(v, ddof=1)) if n > 1 else float("nan")
        q10, q25, median, q75, q90 = np.percentile(v, [10, 25, 50, 75, 90])
        ci_lo, ci_hi = float("nan"), float("nan")
        if n >= 5:
            # Seed stabil per campuran, sehingga hasil tidak berubah saat
            # urutan campuran berubah atau pengguna pindah tab.
            mix_seed = sum((i + 1) * ord(c) for i, c in enumerate(str(campuran)))
            rng = np.random.default_rng((seed + mix_seed) % (2**32 - 1))
            # Bootstrap batch: memori O(iterasi * n), dibatasi baris CSV <=10k.
            # Untuk n besar, batch agar tidak mengalokasikan >~10 MB sekaligus.
            means = []
            remaining = bootstrap_iterasi
            chunk = max(1, min(2000, 100_000 // n))
            while remaining:
                take = min(chunk, remaining)
                means.append(v[rng.integers(0, n, size=(take, n))].mean(axis=1))
                remaining -= take
            ci_lo, ci_hi = map(float, np.percentile(np.concatenate(means), [2.5, 97.5]))
        rows.append({
            "campuran": str(campuran),
            "unit": "silinder" if tingkat == "silinder" else "hasil uji (rerata pasangan)",
            "n": n,
            "mean_MPa": mean,
            "sd_MPa": sd,
            "cv_persen": (sd / mean * 100) if math.isfinite(sd) and mean > 0 else float("nan"),
            "minimum_MPa": float(np.min(v)),
            "p10_MPa": float(q10),
            "q1_MPa": float(q25),
            "median_MPa": float(median),
            "q3_MPa": float(q75),
            "p90_MPa": float(q90),
            "maksimum_MPa": float(np.max(v)),
            "iqr_MPa": float(q75 - q25),
            "ci95_rerata_bawah_MPa": ci_lo,
            "ci95_rerata_atas_MPa": ci_hi,
            "persen_sampel_capai_target": float(np.mean(v >= hasil.mutu_rencana) * 100),
        })
    return pd.DataFrame(rows)


def sensitivitas_target(hasil: HasilAnalisis, target_values: Iterable[float]) -> pd.DataFrame:
    """Simulasikan target f'c berbeda tanpa mengubah hasil utama atau beban CSV.

    Status per campuran memakai evaluasi_tiga_uji yang sama dengan engine.
    Persentase memenuhi target dihitung dari nilai SILINDER, bukan dari status SNI.
    """
    try:
        targets = sorted({float(value) for value in target_values})
    except (TypeError, ValueError, OverflowError) as exc:
        raise DataValidationError(["Nilai target simulasi harus numerik."]) from exc
    if not targets or any(not math.isfinite(x) or x <= 0 or x > 150 for x in targets):
        raise DataValidationError(["Target simulasi harus dalam rentang >0 sampai 150 MPa."])
    # Hindari ribuan evaluasi berulang akibat input tidak terkendali.
    if len(targets) > 301:
        raise DataValidationError(["Jumlah target simulasi dibatasi maksimal 301 nilai."])
    df = hasil.benda_uji
    rows: list[dict] = []
    for target in targets:
        per_mix, _ = evaluasi_tiga_uji(hasil.rekap_uji, target)
        statuses = per_mix.set_index("campuran")["status"]
        for mix, group in df.groupby("campuran", sort=True):
            strength = group["kuat_tekan_MPa"].to_numpy(dtype=float)
            passed = int(np.sum(strength >= target))
            rows.append({
                "target_MPa": float(target),
                "campuran": str(mix),
                "jumlah_silinder": int(len(strength)),
                "silinder_capai_target": passed,
                "persen_silinder_capai_target": passed / len(strength) * 100,
                "rata_rata_MPa": float(np.mean(strength)),
                "status_simulasi": str(statuses.loc[mix]),
            })
    return pd.DataFrame(rows)


def rekap_sensitivitas_target(tabel: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan tiap target; data 'tidak dapat dievaluasi' tetap dibedakan."""
    cols = ["target_MPa", "jumlah_campuran", "memenuhi_simulasi",
            "belum_memenuhi_simulasi", "tidak_dapat_dievaluasi",
            "persen_silinder_capai_target"]
    if tabel.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for target, g in tabel.groupby("target_MPa", sort=True):
        rows.append({
            "target_MPa": float(target),
            "jumlah_campuran": len(g),
            "memenuhi_simulasi": int(g["status_simulasi"].eq("Memenuhi simulasi").sum()),
            "belum_memenuhi_simulasi": int(g["status_simulasi"].eq("Belum memenuhi simulasi").sum()),
            "tidak_dapat_dievaluasi": int(g["status_simulasi"].eq("Tidak dapat dievaluasi").sum()),
            "persen_silinder_capai_target": float(g["silinder_capai_target"].sum() / g["jumlah_silinder"].sum() * 100),
        })
    return pd.DataFrame(rows, columns=cols)
