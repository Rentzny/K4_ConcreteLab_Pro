"""Regresi modul pelacakan beton v5.0, tanpa bergantung pada Streamlit."""
from datetime import date
from io import BytesIO
import pandas as pd
import pytest
from pypdf import PdfReader

from concretelab.tracking import (
    TrackingError, buat_template_registrasi, validasi_registrasi,
    jadwal_pengujian, kode_qr_sampel, label_qr_pdf, kalender_ics,
    export_registrasi_csv,
)

@pytest.fixture
def source():
    return pd.DataFrame([
        {'id_benda_uji':'A01','campuran':'A','umur_hari':7},
        {'id_benda_uji':'A02','campuran':'A','umur_hari':14},
        {'id_benda_uji':'A03','campuran':'A','umur_hari':28},
        {'id_benda_uji':'A04','campuran':'A','umur_hari':28},
        {'id_benda_uji':'A05','campuran':'A','umur_hari':28},
    ])

@pytest.fixture
def valid(source):
    df=buat_template_registrasi(source)
    df['tanggal_cetak']='2026-11-10'
    df.loc[0,'tanggal_uji_aktual']='2026-11-17'
    df.loc[1,'tanggal_uji_aktual']='2026-11-18'
    df.loc[4,'tanggal_cetak']=''
    return validasi_registrasi(df,source.id_benda_uji.tolist())

def test_template_has_empty_dates_and_preserves_age(source):
    t=buat_template_registrasi(source)
    assert len(t)==5 and t['tanggal_cetak'].eq('').all()
    assert t['umur_rencana_hari'].tolist()==[7,14,28,28,28]

def test_schedule_statuses_and_early_testing(valid):
    d=jadwal_pengujian(valid,tanggal_acuan=date(2026,12,9))
    assert d['status_jadwal'].tolist()==['Sudah diuji','Diuji lebih awal','Terlambat','Terlambat','Belum dijadwalkan']
    assert d.loc[0,'tanggal_jadwal']=='2026-11-17'
    assert d.loc[1,'umur_saat_uji_hari']==8

def test_schedule_today_future_and_overdue(source):
    t=buat_template_registrasi(source)
    t['tanggal_cetak']='2026-11-13'
    t=validasi_registrasi(t,source.id_benda_uji.tolist())
    result=jadwal_pengujian(t,tanggal_acuan=date(2026,11,20))
    assert result.loc[0,'status_jadwal']=='Jatuh tempo'
    assert result.loc[1,'status_jadwal']=='Terjadwal'
    old=jadwal_pengujian(t,tanggal_acuan=date(2026,11,21))
    assert old.loc[0,'status_jadwal']=='Terlambat'

@pytest.mark.parametrize('age',[-1,0,2.5,3651,'abc'])
def test_invalid_age_rejected(source,age):
    df=buat_template_registrasi(source)
    df.loc[0,'umur_rencana_hari']=age
    with pytest.raises(TrackingError):validasi_registrasi(df,source.id_benda_uji.tolist())

def test_duplicate_and_mismatched_ids_rejected(source):
    df=buat_template_registrasi(source)
    df.loc[1,'id_benda_uji']='A01'
    with pytest.raises(TrackingError):validasi_registrasi(df,source.id_benda_uji.tolist())
    df=buat_template_registrasi(source)
    df.loc[1,'id_benda_uji']='Z01'
    with pytest.raises(TrackingError):validasi_registrasi(df,source.id_benda_uji.tolist())

@pytest.mark.parametrize('date_value',['2026-02-31','20/11/2026','2026-13-01'])
def test_malformed_cast_date(source,date_value):
    df=buat_template_registrasi(source)
    df.loc[0,'tanggal_cetak']=date_value
    with pytest.raises(TrackingError):validasi_registrasi(df,source.id_benda_uji.tolist())

def test_actual_test_must_have_cast_date(source):
    df=buat_template_registrasi(source)
    df.loc[0,'tanggal_uji_aktual']='2026-11-20'
    with pytest.raises(TrackingError):validasi_registrasi(df,source.id_benda_uji.tolist())

def test_actual_test_cannot_precede_cast_date(source):
    df=buat_template_registrasi(source)
    df.loc[0,'tanggal_cetak']='2026-11-21'
    df.loc[0,'tanggal_uji_aktual']='2026-11-20'
    with pytest.raises(TrackingError):validasi_registrasi(df,source.id_benda_uji.tolist())

def test_qr_stable_and_project_specific(valid):
    assert kode_qr_sampel('A','A01')==kode_qr_sampel('A','A01')
    assert kode_qr_sampel('A','A01')!=kode_qr_sampel('B','A01')
    assert kode_qr_sampel('A','A01')!=kode_qr_sampel('A','A02')

def test_label_pdf_two_pages_for_twelve(valid):
    twelve=pd.concat([valid]*3,ignore_index=True).iloc[:12].copy()
    twelve['id_benda_uji']=[f'X{i:02}' for i in range(len(twelve))]
    pdf=label_qr_pdf(twelve,nama_proyek='PjBL K4')
    assert pdf.startswith(b'%PDF-')
    assert len(PdfReader(BytesIO(pdf)).pages)==2

def test_ics_contains_upcoming_no_tested(valid):
    schedule=jadwal_pengujian(valid,tanggal_acuan=date(2026,11,20))
    ics=kalender_ics(schedule,nama_proyek='PjBL K4').decode()
    assert 'BEGIN:VCALENDAR' in ics
    assert ics.count('BEGIN:VEVENT')==2
    assert 'Uji beton A03' in ics and 'Uji beton A01' not in ics

def test_export_csv_formula_sanitized():
    reg=pd.DataFrame({'id_benda_uji':['=2+2'], 'campuran':['@SUM()'], 'tanggal_cetak':[''], 'umur_rencana_hari':[28], 'tanggal_uji_aktual':['']})
    b=export_registrasi_csv(reg)
    assert b"'=2+2" in b and b"'@SUM()" in b
