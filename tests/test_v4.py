"""Regresi fitur Professional Visual Analytics & Reporting v4.0."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import json
import numpy as np
import pandas as pd
import pytest
from pypdf import PdfReader

from concretelab.engine import read_csv,analisis
from concretelab.professional import ringkasan_eksekutif, tabel_kinerja, interpretasi_per_campuran
from concretelab.visuals_v4 import grafik_histogram,grafik_box,grafik_tren,grafik_rerata,grafik_pencapaian,grafik_ecdf
from concretelab.reporting import buat_pdf, buat_zip
from concretelab.projects import buat_arsip_proyek, baca_arsip_proyek

DATA = Path(__file__).parents[1] / 'data' / 'contoh_18_silinder.csv'

@pytest.fixture
def result():
    return analisis(read_csv(DATA),30.0,sumber='Data ilustratif')

def test_executive_numbers_exactly_follow_engine(result):
    ex=ringkasan_eksekutif(result)
    assert ex.jumlah_silinder==18
    assert ex.jumlah_campuran==3
    assert ex.jumlah_uji==9
    assert ex.rata_rata_mpa==pytest.approx(result.benda_uji.kuat_tekan_MPa.mean())
    assert ex.persen_silinder_target==pytest.approx(100*result.ringkasan['mencapai_target']/18)

def test_kinerja_computation_and_status_separated(result):
    k=tabel_kinerja(result)
    assert len(k)==3
    assert (k.pencapaian_target_persen.between(0,100)).all()
    assert set(k.status_simulasi)==set(result.evaluasi.status)
    assert set(k.columns)>={'rasio_rerata_ke_target_persen','status_simulasi'}

def test_interpretations_never_claim_actual_acceptance(result):
    texts=interpretasi_per_campuran(result)
    assert len(texts)==3
    assert all('simulasi' in s.lower() for s in texts)

def test_csv_change_recalculates_all_summary_fields(result):
    df=result.input_data.copy()
    old=ringkasan_eksekutif(result)
    df.loc[0,'beban_maksimum_kN']+=100
    new=ringkasan_eksekutif(analisis(df,30.0))
    assert new.rata_rata_mpa>old.rata_rata_mpa
    assert new.jumlah_silinder==old.jumlah_silinder

def test_target_change_updates_kpi_without_mutating_source(result):
    df=result.input_data.copy(deep=True)
    low=ringkasan_eksekutif(analisis(df,20.0))
    high=ringkasan_eksekutif(analisis(df,40.0))
    assert low.persen_silinder_target>=high.persen_silinder_target
    pd.testing.assert_frame_equal(result.input_data,df)

def test_more_or_fewer_rows_dynamic(result):
    df=result.input_data.copy()
    for num in range(5):
        r=df.iloc[0].copy()
        r['id_benda_uji']=f'X{num}'
        r['id_pengujian']=f'A{num+20}'
        if 'urutan_uji' in df.columns: r['urutan_uji']=num+20
        df=pd.concat([df,pd.DataFrame([r])],ignore_index=True)
    ex=ringkasan_eksekutif(analisis(df,30))
    assert ex.jumlah_silinder==23

def test_all_six_figures_are_valid_plotly(result):
    for fn in [grafik_histogram,grafik_box,grafik_tren,grafik_rerata,grafik_pencapaian,grafik_ecdf]:
        fig=fn(result)
        assert fig.data
        assert len(fig.to_json())>100

def test_single_record_figures_and_summary():
    df=read_csv(DATA).iloc[[0]].copy()
    result=analisis(df,30)
    k=ringkasan_eksekutif(result)
    assert k.sd_mpa is None
    for fn in [grafik_histogram,grafik_box,grafik_tren,grafik_rerata,grafik_pencapaian,grafik_ecdf]:
        assert fn(result).data

def test_pdf_and_zip_v4_export(result):
    blob=buat_pdf(result, nama_proyek='Uji Profesional v4')
    reader=PdfReader(BytesIO(blob))
    assert len(reader.pages)==6
    texts='\n'.join(p.extract_text() for p in reader.pages)
    assert 'Ringkasan eksekutif' in texts
    assert 'Analisis visual' in texts
    with ZipFile(BytesIO(buat_zip(result,blob,{}))) as z:
        names=set(z.namelist())
        assert 'hasil/ringkasan_kinerja_profesional.csv' in names
        assert 'hasil/Ringkasan_Eksekutif.txt' in names
        assert json.loads(z.read('ringkasan_metadata.json'))['versi_aplikasi']=='4.0'

def test_archives_remain_portable_in_v4(result):
    blob=buat_arsip_proyek(result,nama_proyek='Uji Versi 4',penanggung_jawab='Tim',pdf_bytes=buat_pdf(result))
    item=baca_arsip_proyek(blob)
    assert item.metadata['app_version']=='4.0'
    assert len(PdfReader(BytesIO(item.pdf_bytes)).pages)==6

def test_no_hardcoded_first_dataset_in_summary(result):
    d=result.input_data[result.input_data.campuran=='A'].copy()
    ex=ringkasan_eksekutif(analisis(d,30))
    assert ex.jumlah_campuran==1 and ex.jumlah_silinder==len(d)
    assert 'Campuran B' not in ex.deskripsi
