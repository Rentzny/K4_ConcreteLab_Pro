"""Executive summary dinamis untuk ConcreteLab Pro v4.

Hasil diambil dari HasilAnalisis; tidak ada angka demonstrasi hard-coded.
Label pencapaian TARGET silinder bukan keputusan penerimaan beton.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from .engine import HasilAnalisis

@dataclass(frozen=True)
class ExecutiveSummary:
    judul: str
    deskripsi: str
    jumlah_silinder: int
    jumlah_uji: int
    jumlah_campuran: int
    target_mpa: float
    rata_rata_mpa: float
    sd_mpa: float | None
    persen_silinder_target: float
    campuran_rata_tertinggi: str
    rerata_tertinggi_mpa: float
    campuran_memenuhi: int
    campuran_belum_memenuhi: int
    campuran_tidak_dapat_dinilai: int
    catatan: tuple[str,...]


def ringkasan_eksekutif(h: HasilAnalisis) -> ExecutiveSummary:
    """Ikhtisar statistik dan status simulasi yang dipisahkan secara eksplisit."""
    d = h.benda_uji
    s = h.statistik
    k = h.ringkasan
    if d.empty or s.empty:
        raise ValueError("Analisis memerlukan setidaknya satu benda uji.")
    nilai = d["kuat_tekan_MPa"]
    mean = float(nilai.mean())
    sd = float(nilai.std(ddof=1)) if len(nilai) > 1 else None
    top = s.loc[s["rata_rata"].idxmax()]
    ratio = 100.0 * k["mencapai_target"] / len(d)
    if ratio == 100:
        assessment = "Seluruh hasil silinder mencapai target numerik yang dipilih."
    elif ratio == 0:
        assessment = "Belum ada hasil silinder yang mencapai target numerik yang dipilih."
    else:
        assessment = f"{k['mencapai_target']} dari {len(d)} hasil silinder mencapai target numerik yang dipilih."
    description = (
        f"Analisis mencakup {len(d)} silinder dari {k['campuran']} campuran "
        f"dan {k['jumlah_uji']} kelompok hasil uji. {assessment} "
        f"Campuran {top['campuran']} memiliki rata-rata silinder tertinggi "
        f"({float(top['rata_rata']):.2f} MPa)."
    )
    notes = [
        "Pencapaian target pada satu silinder tidak sama dengan penerimaan mutu menurut standar.",
        "Evaluasi numerik SNI hanya simulasi dengan persyaratan dan asumsi pada tab Metode.",
    ]
    if k['campuran_belum_dapat_dinilai']:
        notes.append(f"{k['campuran_belum_dapat_dinilai']} campuran tidak dapat dievaluasi secara numerik karena asumsi data belum lengkap.")
    if k['indikasi_outlier']:
        notes.append(f"Ada {k['indikasi_outlier']} indikasi outlier yang harus ditinjau; tidak dihapus otomatis.")
    notes.extend(h.peringatan[:4])
    return ExecutiveSummary(
        judul="Ringkasan eksekutif analisis kuat tekan beton",
        deskripsi=description,
        jumlah_silinder=len(d), jumlah_uji=k['jumlah_uji'], jumlah_campuran=k['campuran'],
        target_mpa=float(h.mutu_rencana), rata_rata_mpa=mean, sd_mpa=sd,
        persen_silinder_target=ratio,
        campuran_rata_tertinggi=str(top['campuran']), rerata_tertinggi_mpa=float(top['rata_rata']),
        campuran_memenuhi=k['campuran_memenuhi_simulasi'],
        campuran_belum_memenuhi=k['campuran_tidak_memenuhi'],
        campuran_tidak_dapat_dinilai=k['campuran_belum_dapat_dinilai'],
        catatan=tuple(dict.fromkeys(notes)),
    )


def tabel_kinerja(h: HasilAnalisis) -> pd.DataFrame:
    """Tabel status per campuran; status SNI berbeda dari persentase silinder >= target."""
    e = h.evaluasi.set_index('campuran')
    rows = []
    for r in h.statistik.itertuples(index=False):
        mix = str(r.campuran)
        v = h.benda_uji.loc[h.benda_uji['campuran']==mix,'kuat_tekan_MPa']
        rows.append({
            'campuran': mix,
            'jumlah_silinder': int(r.jumlah),
            'rata_rata_MPa': float(r.rata_rata),
            'simpangan_baku_MPa': float(r.simpangan_baku) if math.isfinite(r.simpangan_baku) else float('nan'),
            'cv_persen': float(r.cv_persen) if math.isfinite(r.cv_persen) else float('nan'),
            'pencapaian_target_persen': float(v.ge(h.mutu_rencana).mean()*100),
            'rasio_rerata_ke_target_persen': float(r.rata_rata/h.mutu_rencana*100),
            'status_simulasi': str(e.loc[mix,'status']),
        })
    return pd.DataFrame(rows)


def interpretasi_per_campuran(h: HasilAnalisis) -> list[str]:
    """Interpretasi konservatif yang tidak mengklaim akar penyebab atau rekomendasi campuran nyata."""
    result=[]
    for r in tabel_kinerja(h).itertuples(index=False):
        beda = r.rata_rata_MPa-h.mutu_rencana
        rel = "di atas" if beda >= 0 else "di bawah"
        status=str(r.status_simulasi).lower()
        msg=(f"Campuran {r.campuran}: rerata silinder {r.rata_rata_MPa:.2f} MPa "
             f"({abs(beda):.2f} MPa {rel} target). "
             f"{r.pencapaian_target_persen:.1f}% silinder mencapai target; "
             f"status evaluasi numerik: {status}.")
        if status == 'tidak dapat dievaluasi':
            msg += " Perlu melengkapi kecukupan dan konfigurasi hasil uji sebelum menafsirkan penerimaan."
        elif status == 'belum memenuhi simulasi':
            msg += " Perlu peninjauan data, metode pengujian, dan penyebab teknis sebelum menentukan tindak lanjut."
        result.append(msg)
    return result
