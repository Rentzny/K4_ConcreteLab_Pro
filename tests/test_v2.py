"""Uji fitur v2: audit, pembanding, skenario, dan ketahanan input."""
from pathlib import Path
import sys
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from concretelab.engine import read_csv, analisis, DataValidationError
from concretelab.quality import audit_csv, audit_counts
from concretelab.scenarios import simulasi_beban, tabel_skenario, bandingkan_dua_analisis

CSV = Path(__file__).resolve().parents[1] / 'data' / 'contoh_18_silinder.csv'


def input_data():
    return read_csv(CSV)


def test_audit_demo_tidak_error():
    a = audit_csv(input_data())
    assert audit_counts(a)['error'] == 0
    assert audit_counts(a)['peringatan'] == 0  # Data contoh sudah punya urutan_uji


def test_audit_peringatan_tanpa_urutan_uji():
    d = input_data().drop(columns=['urutan_uji'])
    assert audit_counts(audit_csv(d))['peringatan'] >= 1

def test_audit_duplikat_dengan_nomor_baris():
    d = input_data(); d.loc[1,'id_benda_uji'] = d.loc[0,'id_benda_uji']
    a = audit_csv(d)
    assert audit_counts(a)['error'] >= 2
    assert set(a[a.kolom == 'id_benda_uji']['baris_csv']) == {2,3}


def test_audit_missing_numeric_dan_nol():
    d = input_data(); d.loc[2,'diameter_mm'] = 0; d.loc[3,'beban_maksimum_kN'] = None
    a = audit_csv(d)
    assert set(a[a.tingkat=='Error'].baris_csv) >= {4,5}


def test_audit_kolom_hilang_dan_kosong():
    d = input_data().drop(columns=['campuran'])
    assert 'campuran' in set(audit_csv(d).kolom)
    assert audit_counts(audit_csv(pd.DataFrame()))['error'] == 1


def test_audit_kelompok_jumlah_tidak_dua():
    d = input_data().query("id_benda_uji != 'U02'")
    a = audit_csv(d)
    assert ((a.tingkat == 'Peringatan') & a.masalah.str.contains('berisi 1 silinder')).any()


def test_skenario_tidak_mengubah_data_asli():
    base = analisis(input_data())
    old = base.input_data.copy(deep=True)
    s = simulasi_beban(base, 10)
    pd.testing.assert_frame_equal(base.input_data, old)
    assert s.benda_uji.iloc[0]['kuat_tekan_MPa'] == pytest.approx(base.benda_uji.iloc[0]['kuat_tekan_MPa'] * 1.10)
    assert s.ringkasan['silinder'] == base.ringkasan['silinder']


def test_skenario_0_setara_utama():
    base = analisis(input_data())
    s = simulasi_beban(base,0)
    pd.testing.assert_frame_equal(base.statistik,s.statistik)


@pytest.mark.parametrize('change',[-100,301,float('nan')])
def test_skenario_diluar_batas_ditolak(change):
    with pytest.raises(DataValidationError):
        simulasi_beban(analisis(input_data()),change)


def test_sensitivitas_tiga_titik_tiga_campuran():
    t = tabel_skenario(analisis(input_data()), [-10,0,10])
    assert len(t) == 9
    assert set(t['perubahan_beban_persen']) == {-10.0,0.0,10.0}


def test_perbandingan_dua_csv_perubahan_terdeteksi():
    baseline = analisis(input_data())
    changed = input_data().copy(); changed.loc[changed.id_benda_uji=='U01','beban_maksimum_kN'] = 550
    actual = analisis(changed)
    compare = bandingkan_dua_analisis(baseline,actual).set_index('campuran')
    assert compare.loc['A','selisih_B_minus_A_MPa'] > 0
    assert compare.loc['B','selisih_B_minus_A_MPa'] == pytest.approx(0)


def test_perbandingan_campuran_tidak_sama():
    a = analisis(input_data().query("campuran != 'C'"))
    b = analisis(input_data().query("campuran != 'A'"))
    cmp = bandingkan_dua_analisis(a,b)
    assert len(cmp) == 3
    assert pd.isna(cmp.loc[cmp.campuran=='A','rata_B_MPa'].iloc[0])


def test_zip_menyimpan_audit_dan_versi():
    from io import BytesIO
    from zipfile import ZipFile
    import json
    from concretelab.plots import semua_grafik
    from concretelab.reporting import buat_pdf, buat_zip
    result = analisis(input_data())
    graphics = semua_grafik(result)
    bundle = buat_zip(result, buat_pdf(result, grafik=graphics),graphics)
    with ZipFile(BytesIO(bundle)) as z:
        assert "hasil/audit_input.csv" in z.namelist()
        meta=json.loads(z.read("ringkasan_metadata.json"))
        assert meta["versi_aplikasi"]=="2.0"
        assert meta["audit_input"]["error"] == 0
