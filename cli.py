"""Penggunaan tanpa browser, termasuk VS Code terminal dan Colab.
Contoh: python cli.py --input data/contoh_18_silinder.csv --target 30 --output hasil
"""
from __future__ import annotations
import argparse
from pathlib import Path
from concretelab.engine import read_csv,analisis,DataValidationError
from concretelab.plots import semua_grafik
from concretelab.reporting import buat_pdf,buat_zip
from concretelab.quality import audit_csv


def main():
    p=argparse.ArgumentParser(description="Analisis K4 dan ekspor PDF otomatis")
    p.add_argument("--input",required=True,help="Lokasi CSV")
    p.add_argument("--target",type=float,default=30.0,help="f'c rencana (MPa), default 30")
    p.add_argument("--output",default="hasil",help="Folder keluaran")
    p.add_argument("--nama",default="PjBL K4 - Evaluasi Kuat Tekan Beton",help="Nama proyek pada PDF")
    p.add_argument("--penanggung",default="Kelompok PjBL K4",help="Penanggung jawab PDF")
    a=p.parse_args()
    path=Path(a.input)
    try:
        data=read_csv(path)
        hasil=analisis(data,a.target,sumber=f"CSV: {path.name}",raw_bytes=path.read_bytes())
    except (DataValidationError,FileNotFoundError) as exc:
        p.error(str(exc))
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    figs=semua_grafik(hasil)
    pdf=buat_pdf(hasil,a.nama,a.penanggung,figs)
    for filename,figure in figs.items():
        (out/filename).write_bytes(figure)
    files={"audit_input.csv":audit_csv(hasil.input_data),
           "hasil_kuat_tekan.csv":hasil.benda_uji,"statistik_campuran.csv":hasil.statistik,
           "rekap_pengujian.csv":hasil.rekap_uji,"evaluasi_simulasi.csv":hasil.evaluasi,
           "jendela_tiga_uji.csv":hasil.jendela_tiga_uji}
    for filename,df in files.items():
        df.to_csv(out/filename,index=False,encoding="utf-8-sig")
    (out/"Laporan_Otomatis_K4_Beton.pdf").write_bytes(pdf)
    (out/"Paket_Lengkap_Hasil_K4_Beton.zip").write_bytes(buat_zip(hasil,pdf,figs,a.nama))
    print("PROSES BERHASIL")
    print(f"Silinder {hasil.ringkasan['silinder']} | Campuran {hasil.ringkasan['campuran']} | Hasil uji {hasil.ringkasan['jumlah_uji']}")
    print(hasil.evaluasi[["campuran","status"]].to_string(index=False))
    for w in hasil.peringatan:
        print("CATATAN:",w)
    print(f"PDF: {(out/'Laporan_Otomatis_K4_Beton.pdf').resolve()}")


if __name__=="__main__":
    main()
