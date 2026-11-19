"""Pengujian otomatis data proyek dan input yang tidak valid."""
from pathlib import Path
from io import BytesIO
import math
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from concretelab.engine import (read_csv,validasi_input, analisis,DataValidationError,BendaUji)
from concretelab.reporting import buat_pdf,buat_zip
from concretelab.plots import semua_grafik

EXAMPLE=Path(__file__).resolve().parents[1]/"data"/"contoh_18_silinder.csv"


def demo():
    return read_csv(EXAMPLE)


def test_kuat_tekan_manual():
    a=BendaUji("U01","A",150,500)
    assert a.hitung_luas() == pytest.approx(math.pi*150**2/4)
    assert a.hitung_kuat_tekan() == pytest.approx(28.29421210522584)


def test_demo_18_3_9():
    r=analisis(demo(),30,raw_bytes=EXAMPLE.read_bytes())
    assert r.ringkasan["silinder"]==18
    assert r.ringkasan["campuran"]==3
    assert r.ringkasan["jumlah_uji"]==9
    assert r.ringkasan["mencapai_target"]==7
    assert r.ringkasan["indikasi_outlier"]==0
    assert r.statistik.set_index("campuran").loc["A","rata_rata"]==pytest.approx(29.143,abs=.001)
    assert r.statistik.set_index("campuran").loc["B","rata_rata"]==pytest.approx(33.104,abs=.001)
    assert r.statistik.set_index("campuran").loc["C","rata_rata"]==pytest.approx(27.775,abs=.001)
    assert dict(zip(r.evaluasi.campuran,r.evaluasi.status))=={
        "A":"Belum memenuhi simulasi","B":"Memenuhi simulasi","C":"Belum memenuhi simulasi"
    }


def test_csv_diubah_perhitungan_dan_status_ikut_berubah():
    x=demo()
    baseline=analisis(x)
    x.loc[x.id_benda_uji=="U01","beban_maksimum_kN"]=550
    res=analisis(x)
    a0=baseline.statistik.set_index("campuran").loc["A","rata_rata"]
    a1=res.statistik.set_index("campuran").loc["A","rata_rata"]
    assert a1>a0
    fc=res.benda_uji.set_index("id_benda_uji").loc["U01","kuat_tekan_MPa"]
    assert fc==pytest.approx(31.123633,abs=1e-5)
    assert res.ringkasan["mencapai_target"]==8


def test_tambah_silinder_19_tidak_memaksa_18():
    data=demo()
    additional=data.iloc[[0]].copy(); additional.loc[:,"id_benda_uji"]="U19";additional.loc[:,"id_pengujian"]="A04";additional.loc[:,"urutan_uji"]=4
    out=analisis(pd.concat([data,additional],ignore_index=True))
    assert len(out.benda_uji)==19
    assert out.evaluasi.set_index("campuran").loc["A","status"]=="Tidak dapat dievaluasi"


def test_kelompok_satu_silinder_tidak_dinyatakan_lulus():
    data=demo().query("id_benda_uji != 'U02'")
    res=analisis(data)
    assert res.evaluasi.set_index("campuran").loc["A","status"]=="Tidak dapat dievaluasi"


def test_tidak_ada_tiga_uji():
    data=demo().query("id_pengujian != 'A03'")
    res=analisis(data)
    assert res.evaluasi.set_index("campuran").loc["A","status"]=="Tidak dapat dievaluasi"


def test_umur_bukan_28_belum_dapat_dinilai():
    data=demo(); data.loc[data.campuran=="A","umur_hari"]=7
    res=analisis(data)
    assert res.evaluasi.set_index("campuran").loc["A","status"]=="Tidak dapat dievaluasi"


def test_duplikasi_id_ditolak():
    data=demo();data.loc[1,"id_benda_uji"]=data.loc[0,"id_benda_uji"]
    with pytest.raises(DataValidationError,match="duplikat"):
        analisis(data)


@pytest.mark.parametrize("column,value",[("diameter_mm",0),("beban_maksimum_kN",-3),("umur_hari","invalid"),("diameter_mm",np.inf)])
def test_nilai_tidak_valid_ditolak(column,value):
    data=demo();data.loc[0,column]=value
    with pytest.raises(DataValidationError):
        analisis(data)


def test_kolom_hilang_ditolak():
    with pytest.raises(DataValidationError,match="Kolom wajib"):
        analisis(demo().drop(columns=["id_pengujian"]))


def test_urutan_uji_ambigu_ditolak():
    data=demo();data.loc[0,"urutan_uji"]=99
    with pytest.raises(DataValidationError,match="urutan_uji"):
        analisis(data)


def test_perubahan_target_diatas_35():
    res=analisis(demo(),40)
    assert res.evaluasi.batas_uji_MPa.iloc[0]==pytest.approx(36.0)
    assert (res.evaluasi.status=="Belum memenuhi simulasi").all()


def test_outlier_n_kecil_ditandai_belum_cukup():
    small=demo().query("campuran=='A'").iloc[:4].copy()
    res=analisis(small)
    assert (res.benda_uji.status_outlier=="Data belum cukup").all()


def test_pdf_zip_follow_current_data():
    a=analisis(demo())
    b=demo();b.loc[b.id_benda_uji=="U01","beban_maksimum_kN"]=550
    mod=analisis(b)
    for res in (a,mod):
        images=semua_grafik(res)
        assert len(images)==4
        pdf=buat_pdf(res,grafik=images)
        assert pdf.startswith(b"%PDF")
        with zipfile.ZipFile(BytesIO(buat_zip(res,pdf,images))) as z:
            assert "hasil/Laporan_Otomatis_K4_Beton.pdf" in z.namelist()
            out=pd.read_csv(BytesIO(z.read("hasil/hasil_kuat_tekan.csv")))
            assert len(out)==18
            assert out.loc[out.id_benda_uji=="U01","beban_maksimum_kN"].iloc[0]==res.input_data.loc[res.input_data.id_benda_uji=="U01","beban_maksimum_kN"].iloc[0]
