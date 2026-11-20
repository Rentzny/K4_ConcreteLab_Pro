"""Pelacakan sampel dan jadwal uji beton (v5.0).

Fitur operasional untuk perencanaan/pencatatan saja. Bukan verifikasi
laboratorium atau penerimaan SNI. Tidak menyimpan data di cloud.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from hashlib import sha256
from typing import Any
import math
import re
import unicodedata

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.pdfgen.canvas import Canvas

ID_COL = 'id_benda_uji'
TRACKING_COLS = ['id_benda_uji', 'campuran', 'tanggal_cetak', 'umur_rencana_hari', 'tanggal_uji_aktual']

class TrackingError(ValueError):
    """Kesalahan registrasi/tanggal sampel yang perlu dibetulkan pengguna."""


def _date_or_none(value: Any, label: str) -> date | None:
    if value is None or pd.isna(value) or str(value).strip() == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    val = str(value).strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', val):
        raise TrackingError(f'{label} harus format YYYY-MM-DD, contoh 2026-11-20.')
    try:
        return date.fromisoformat(val)
    except ValueError as err:
        raise TrackingError(f'{label} bukan tanggal kalender yang valid: {val}.') from err


def _id(value: Any) -> str:
    if pd.isna(value):
        raise TrackingError('ID benda uji tidak boleh kosong.')
    s = str(value).strip()
    if not s or len(s)>120 or any(ord(c)<32 for c in s):
        raise TrackingError('ID benda uji harus 1–120 karakter dan tidak boleh mengandung karakter kontrol.')
    return s


def _umur(value: Any, *, label: str) -> int:
    if value is None or pd.isna(value) or str(value).strip()=='':
        raise TrackingError(f'Umur rencana harus diisi pada {label}.')
    try:
        n = float(value)
    except (TypeError, ValueError) as err:
        raise TrackingError(f'Umur rencana tidak numerik pada {label}.') from err
    if not math.isfinite(n) or not n.is_integer() or not 1 <= n <= 3650:
        raise TrackingError(f'Umur rencana pada {label} harus bilangan bulat 1–3650 hari.')
    return int(n)


def buat_template_registrasi(df_beton: pd.DataFrame) -> pd.DataFrame:
    """Buat data awal berdasarkan ID/umur asli. Tanggal sengaja kosong."""
    cols = ['id_benda_uji', 'campuran', 'umur_hari']
    if not set(cols).issubset(df_beton.columns):
        raise TrackingError('Data beton membutuhkan kolom id_benda_uji, campuran, umur_hari.')
    if df_beton[ID_COL].duplicated().any():
        raise TrackingError('ID benda uji duplikat dalam data beton.')
    out = df_beton[cols].copy()
    out['tanggal_cetak'] = ''
    out['umur_rencana_hari'] = out['umur_hari']
    out['tanggal_uji_aktual'] = ''
    return out[TRACKING_COLS].reset_index(drop=True)


def validasi_registrasi(df: pd.DataFrame, daftar_id: list[str]) -> pd.DataFrame:
    """Validasi register seluruh benda uji; tidak menganggap umur_hari adalah tanggal."""
    if not isinstance(df, pd.DataFrame) or not set(TRACKING_COLS).issubset(df.columns):
        raise TrackingError('Kolom registrasi belum lengkap: '+', '.join(TRACKING_COLS))
    if len(df)>10000:
        raise TrackingError('Maksimal 10.000 baris registrasi.')
    ids = [_id(s) for s in df[ID_COL]]
    if len(ids) != len(set(ids)):
        raise TrackingError('ID benda uji duplikat di registrasi.')
    if len(daftar_id) != len(set(daftar_id)):
        raise TrackingError('Data uji utama memiliki ID duplikat.')
    if set(ids) != set(map(str, daftar_id)):
        raise TrackingError('ID registrasi harus sama persis dengan ID data CSV yang sedang dianalisis.')
    out = df.copy()
    out[ID_COL] = ids
    out['campuran'] = out['campuran'].fillna('').astype(str).str.strip()
    clean_umur=[]
    clean_cast=[]
    clean_test=[]
    for _, row in out.iterrows():
        label = str(row[ID_COL])
        umur = _umur(row['umur_rencana_hari'], label=label)
        cast = _date_or_none(row['tanggal_cetak'], f'Tanggal cetak {label}')
        actual = _date_or_none(row['tanggal_uji_aktual'], f'Tanggal uji aktual {label}')
        if actual is not None and cast is None:
            raise TrackingError(f'Tanggal cetak {label} wajib diisi jika sudah ada tanggal uji aktual.')
        if actual is not None and actual < cast:
            raise TrackingError(f'Tanggal uji aktual {label} tidak boleh sebelum tanggal cetak.')
        if cast is not None:
            try:
                _ = cast + timedelta(days=umur)
            except OverflowError as err:
                raise TrackingError(f'Jadwal {label} melebihi batas kalender.') from err
        clean_umur.append(umur)
        clean_cast.append(cast.isoformat() if cast else '')
        clean_test.append(actual.isoformat() if actual else '')
    out['umur_rencana_hari']=clean_umur
    out['tanggal_cetak']=clean_cast
    out['tanggal_uji_aktual']=clean_test
    return out[TRACKING_COLS].reset_index(drop=True)


def jadwal_pengujian(registrasi: pd.DataFrame, *, tanggal_acuan: date) -> pd.DataFrame:
    """Klasifikasikan jadwal (bukan status penerimaan hasil uji)."""
    if not isinstance(tanggal_acuan, date):
        raise TrackingError('Tanggal acuan tidak valid.')
    out = registrasi.copy()
    due_dates=[]; statuses=[]; days=[]; test_age=[]
    for _, r in out.iterrows():
        cast = _date_or_none(r['tanggal_cetak'], 'Tanggal cetak')
        actual = _date_or_none(r['tanggal_uji_aktual'], 'Tanggal uji')
        age = _umur(r['umur_rencana_hari'], label=str(r[ID_COL]))
        if cast is None:
            due_dates.append(''); statuses.append('Belum dijadwalkan'); days.append(None); test_age.append(None)
            continue
        due = cast + timedelta(days=age)
        due_dates.append(due.isoformat())
        days.append((due-tanggal_acuan).days)
        if actual is not None:
            actual_age = (actual-cast).days
            test_age.append(actual_age)
            statuses.append('Sudah diuji' if actual_age>=age else 'Diuji lebih awal')
        elif due < tanggal_acuan:
            test_age.append(None); statuses.append('Terlambat')
        elif due == tanggal_acuan:
            test_age.append(None); statuses.append('Jatuh tempo')
        else:
            test_age.append(None); statuses.append('Terjadwal')
    out['tanggal_jadwal']=due_dates
    out['status_jadwal']=statuses
    out['sisa_hari']=pd.Series(days, index=out.index, dtype='Int64')
    out['umur_saat_uji_hari']=pd.Series(test_age, index=out.index, dtype='Int64')
    return out


def kode_qr_sampel(nama_proyek: str, id_benda_uji: str) -> str:
    """Kode unik deterministik; BUKAN URL verifikasi atau tanda tangan digital."""
    payload = f'{str(nama_proyek).strip()}\x1f{_id(id_benda_uji)}'.encode('utf-8')
    return 'K4S1-' + sha256(payload).hexdigest()[:20].upper()


def _ascii_file_stem(value: str) -> str:
    s = unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode('ascii')
    return re.sub(r'[^a-zA-Z0-9_-]+','_',s).strip('_')[:45] or 'sampel'


def label_qr_pdf(registrasi: pd.DataFrame, *, nama_proyek: str) -> bytes:
    """Buat label QR 2 kolom x 5 baris per halaman A4; isi QR hanya kode sampeI."""
    if registrasi.empty:
        raise TrackingError('Belum ada registrasi untuk dicetak.')
    if len(registrasi)>1000:
        raise TrackingError('Cetak label maksimal 1.000 sampel tiap unduhan.')
    buff=BytesIO()
    pdf=Canvas(buff,pagesize=A4)
    W,H=A4
    left=32; top=48; bottom=38; gap_x=12; gap_y=9
    cell_w=(W-2*left-gap_x)/2
    cell_h=(H-top-bottom-4*gap_y)/5
    qr_size=74
    for i, (_,row) in enumerate(registrasi.iterrows()):
        if i>0 and i%10==0:
            pdf.showPage()
        pos=i%10
        col=pos%2; line=pos//2
        x=left+col*(cell_w+gap_x)
        y=H-top-(line+1)*cell_h-line*gap_y
        pdf.setStrokeColor(colors.HexColor('#D5E0E4'))
        pdf.setFillColor(colors.white)
        pdf.roundRect(x,y,cell_w,cell_h,6,stroke=1,fill=1)
        txt=str(row[ID_COL]); cast=str(row.get('tanggal_cetak',''))
        key=kode_qr_sampel(nama_proyek,txt)
        qr=QrCodeWidget(key, barWidth=2, barHeight=2)
        bounds=qr.getBounds(); width=bounds[2]-bounds[0]
        scale=qr_size/width
        d=Drawing(qr_size,qr_size,transform=[scale,0,0,scale,0,0]);d.add(qr)
        renderPDF.draw(d,pdf,x+10,y+24)
        text_x=x+94
        pdf.setFillColor(colors.HexColor('#163747'))
        pdf.setFont('Helvetica-Bold',10)
        for j,t in enumerate(simpleSplit(txt, 'Helvetica-Bold',10,cell_w-102)[:2]):
            pdf.drawString(text_x,y+cell_h-24-13*j,t)
        pdf.setFont('Helvetica',8)
        pdf.setFillColor(colors.HexColor('#536977'))
        for j,t in enumerate(simpleSplit(str(row.get('campuran','')), 'Helvetica',8,cell_w-104)[:2]):
            pdf.drawString(text_x,y+cell_h-58-10*j,'Campuran: '+t if j==0 else t)
        pdf.drawString(text_x,y+cell_h-79,'Umur: '+str(row.get('umur_rencana_hari',''))+' hari')
        if cast:
            pdf.drawString(text_x,y+cell_h-92,'Cetak: '+cast[:10])
        pdf.setFont('Helvetica',6.5)
        pdf.drawString(x+9,y+9,key)
    pdf.save()
    return buff.getvalue()


def _ics_escape(s: str) -> str:
    return str(s).replace('\\','\\\\').replace('\r',' ').replace('\n','\\n').replace(',','\\,').replace(';','\\;')[:170]


def kalender_ics(jadwal: pd.DataFrame, *, nama_proyek: str) -> bytes:
    """Ekspor acara sehari penuh; hanya sampel yang belum ditandai diuji."""
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ConcreteLab Pro//K4 Tracking v5//ID','CALSCALE:GREGORIAN','METHOD:PUBLISH']
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for _,row in jadwal.iterrows():
        if str(row.get('status_jadwal')) not in ('Terjadwal','Jatuh tempo','Terlambat'):
            continue
        d = _date_or_none(row.get('tanggal_jadwal'), 'Tanggal jadwal')
        if d is None:
            continue
        uid=kode_qr_sampel(nama_proyek,str(row[ID_COL]))+'@concretelab.local'
        lines.extend(['BEGIN:VEVENT',f'UID:{uid}',f'DTSTAMP:{stamp}',f'DTSTART;VALUE=DATE:{d:%Y%m%d}',
                      f'DTEND;VALUE=DATE:{d+timedelta(days=1):%Y%m%d}',
                      'SUMMARY:'+_ics_escape(f'Uji beton {row[ID_COL]} ({row["campuran"]})'),
                      'DESCRIPTION:'+_ics_escape('Rencana uji beton. Periksa kondisi benda uji dan prosedur laboratorium.'),
                      'END:VEVENT'])
    lines.append('END:VCALENDAR')
    return ('\r\n'.join(lines)+'\r\n').encode('utf-8')


def export_registrasi_csv(df: pd.DataFrame) -> bytes:
    """CSV untuk diunduh (escaping untuk sel teks dengan awalan formula spreadsheet)."""
    out=df.copy()
    for c in ['id_benda_uji','campuran']:
        if c in out:
            out[c]=out[c].fillna('').astype(str).map(lambda s: "'"+s if s.lstrip().startswith(('=','+','-','@')) else s)
    return out.to_csv(index=False).encode('utf-8-sig')
