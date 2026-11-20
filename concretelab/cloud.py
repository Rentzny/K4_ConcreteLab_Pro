"""K4 Cloud Workspace (v5.5) — Supabase Auth + per-user RLS.

IMPORTANT: use the public/publishable key ONLY; never use service_role.
Every Streamlit session owns a separate Supabase client; do not cache it globally.
The database enforces authorization through schema_v55.sql, not UI roles alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any
from urllib.parse import urlencode
from urllib.parse import urlsplit
import secrets as pysecrets
import hashlib
import json
import base64
import binascii

from .engine import read_csv, analisis

MAX_CSV_BYTES = 10 * 1024 * 1024


class CloudConfigError(ValueError):
    pass


def validate_config(url: str, key: str) -> tuple[str, str]:
    url = url.strip().rstrip('/')
    key = key.strip()
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise CloudConfigError('URL Supabase harus HTTPS yang valid.')
    if parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise CloudConfigError('Gunakan Project URL saja, tanpa /rest/v1, /auth/v1, query, atau path lainnya.')
    if len(key) < 24:
        raise CloudConfigError('Supabase publishable/anon key belum diatur dengan benar.')
    if key.startswith('sb_secret_') or key.startswith('sb_service_'):
        raise CloudConfigError('JANGAN gunakan secret/service_role key pada aplikasi.')
    # Reject legacy Supabase service_role JWTs as well (not just new sb_secret_ keys).
    try:
        payload=key.split('.')[1]
        decoded=json.loads(base64.urlsafe_b64decode(payload + '='*(-len(payload)%4)))
        if decoded.get('role')=='service_role':
            raise CloudConfigError('JANGAN gunakan service_role JWT; hanya anon/publishable key.')
    except (IndexError,json.JSONDecodeError,binascii.Error,UnicodeDecodeError,TypeError,KeyError):
        pass
    return url, key


def new_client(url: str, publishable_key: str):
    """Create a PRIVATE client for one user session, never shared by cache_resource."""
    from supabase import create_client
    url, key = validate_config(url, publishable_key)
    return create_client(url, key)


def get_supabase_settings(secrets: Any) -> tuple[str, str] | None:
    """Read Streamlit Secrets; safe for empty/unconfigured deployments."""
    try:
        config = secrets.get('supabase')
        if not config:
            return None
        url = str(config.get('url', '')).strip()
        key = str(config.get('publishable_key', '')).strip()
        if not url or not key:
            return None
        return validate_config(url, key)
    except (FileNotFoundError, KeyError):
        return None


def sign_in(client, email: str, password: str):
    email = email.strip().lower()
    if '@' not in email or len(email) > 254 or not password:
        raise ValueError('Masukkan email dan password yang valid.')
    return client.auth.sign_in_with_password({'email': email, 'password': password})


def sign_up(client, email: str, password: str):
    email = email.strip().lower()
    if '@' not in email or len(email) > 254 or len(password) < 8:
        raise ValueError('Gunakan email valid dan password minimal 8 karakter.')
    return client.auth.sign_up({'email': email, 'password': password})


def authenticated_user(client):
    """Verify token against Supabase Auth; fails closed on missing/invalid session."""
    if client is None:
        return None
    try:
        session = client.auth.get_session()
        if session is None or not session.access_token:
            return None
        verified = client.auth.get_user(session.access_token)
        return verified.user
    except Exception:
        return None


def to_clean_csv(csv_bytes: bytes, target: float) -> tuple[str, int]:
    if not isinstance(csv_bytes, bytes) or not 0 < len(csv_bytes) <= MAX_CSV_BYTES:
        raise ValueError('CSV kosong atau melebihi 10 MB.')
    df = read_csv(csv_bytes)
    result = analisis(df, float(target))
    text = result.input_data.to_csv(index=False)
    if len(text.encode('utf-8')) > MAX_CSV_BYTES:
        raise ValueError('CSV hasil normalisasi melebihi 10 MB.')
    return text, len(result.input_data)


def read_cloud_snapshot(csv_text: str, target: float):
    if not isinstance(csv_text, str) or len(csv_text.encode('utf-8')) > MAX_CSV_BYTES:
        raise ValueError('Snapshot cloud tidak valid.')
    d = read_csv(csv_text.encode('utf-8'))
    return analisis(d, float(target))


def verify_url(base_url: str, token: str) -> str:
    """QR verification link, holding an opaque random token, not user data."""
    p = urlsplit(base_url.strip())
    if p.scheme != 'https' or not p.hostname or p.query or p.fragment:
        raise ValueError('Base URL verifikasi harus HTTPS dan tanpa query/fragment.')
    if len(token) != 48 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Token verifikasi tidak valid.')
    return base_url.rstrip('/')+'/?'+urlencode({'verify':token})


def print_verification_label(url: str, report_id: str, fingerprint: str) -> bytes:
    """Small QR certificate, not a digital signature or lab accreditation."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    f = BytesIO()
    c = canvas.Canvas(f, pagesize=A4)
    w,h = A4
    c.setTitle('ConcreteLab Pro - Verifikasi Laporan')
    c.setFont('Helvetica-Bold',16)
    c.drawString(45,h-60,'CONCRETELAB PRO / VERIFIKASI LAPORAN')
    c.setFont('Helvetica',11)
    c.drawString(45,h-93,'Nomor laporan: '+report_id[:70])
    c.setFont('Helvetica',9)
    c.drawString(45,h-115,'SHA-256 data: '+fingerprint[:64])
    qr = QrCodeWidget(url)
    x0,y0,x1,y1=qr.getBounds()
    box=Drawing(175,175,transform=[175/(x1-x0),0,0,175/(y1-y0),0,0])
    box.add(qr)
    renderPDF.draw(box,c,45,h-320)
    c.setFont('Helvetica',10)
    c.drawString(45,h-345,'Scan QR untuk memeriksa status metadata laporan di website.')
    c.drawString(45,h-364,'QR ini bukan sertifikat laboratorium atau tanda tangan digital.')
    c.save()
    return f.getvalue()


def list_projects(client):
    return client.table('k4_projects').select('id,name,code,description,owner_id,created_at').order('created_at',desc=True).execute().data or []


def create_project(client, user_id: str, name: str, code: str='', desc: str=''):
    name,code,desc=name.strip(),code.strip(),desc.strip()
    if not 2<=len(name)<=120 or len(code)>45 or len(desc)>1500:
        raise ValueError('Nama proyek 2–120 karakter; kode maksimal 45 karakter.')
    # Identity is verified in Auth, and RLS separately checks owner_id = auth.uid().
    return client.table('k4_projects').insert({'owner_id':str(user_id),'name':name,'code':code,'description':desc}).execute().data


def list_snapshots(client,project_id: str):
    return (client.table('k4_snapshots').select('id,project_id,author_id,target_mpa,csv_sha256,note,created_at')
            .eq('project_id',project_id).order('created_at',desc=True).execute().data or [])


def load_snapshot(client, snapshot_id: str):
    data = client.table('k4_snapshots').select('*').eq('id',snapshot_id).limit(1).execute().data or []
    return data[0] if data else None


def save_snapshot(client,project_id: str,user_id: str,csv_bytes:bytes,target:float,note:str=''):
    if len(note)>500: raise ValueError('Catatan maksimal 500 karakter.')
    text,count = to_clean_csv(csv_bytes,target)
    rows=client.table('k4_snapshots').insert({'project_id':project_id,'author_id':str(user_id),
        'csv_text':text,'target_mpa':float(target),'note':note}).execute().data
    return (rows or []),count


def list_reports(client,project_id:str):
    return (client.table('k4_reports').select('*').eq('project_id',project_id)
        .order('revision',desc=True).execute().data or [])


def new_report(client,project_id:str,snapshot_id:str):
    return client.rpc('k4_create_report',{'p_project':project_id,'p_snapshot':snapshot_id}).execute().data


def submit_report(client,report_id:str):
    return client.rpc('k4_submit_report',{'p_report':report_id}).execute().data


def review_report(client,report_id:str,decision:str,note:str):
    if decision not in ('approved','rejected','needs_revision'):
        raise ValueError('Keputusan tidak valid.')
    return client.rpc('k4_review_report',{'p_report':report_id,'p_decision':decision,'p_note':note}).execute().data


def verify_report(client,token:str):
    if not isinstance(token,str) or len(token)!=48 or any(c not in '0123456789abcdef' for c in token):
        return None
    data=client.rpc('k4_verify_report',{'p_token':token}).execute().data or []
    return data[0] if data else None


def get_profile(client,user_id:str):
    rows=client.table('k4_profiles').select('user_id,email,display_name,global_role,account_status').eq('user_id',str(user_id)).execute().data or []
    return rows[0] if rows else None


def member_list(client,project_id:str):
    return client.table('k4_project_members').select('project_id,user_id,project_role').eq('project_id',project_id).execute().data or []


def add_member(client,project_id:str,user_id:str,role:str):
    if role not in ('viewer','technician','supervisor'): raise ValueError('Peran proyek tidak valid.')
    return client.table('k4_project_members').upsert({'project_id':project_id,'user_id':user_id,'project_role':role},
        on_conflict='project_id,user_id').execute().data


def delete_member(client,project_id:str,user_id:str):
    return client.table('k4_project_members').delete().eq('project_id',project_id).eq('user_id',user_id).execute().data


def invite_account_by_email(client, settings: tuple[str, str], email: str):
    """Optional invite through authenticated Supabase Edge Function, no service key here.

    Inviting is disabled until owner deploys k4-admin-invite Edge Function.
    Admin is verified in Edge Function on EVERY call, not by Streamlit UI.
    """
    import httpx
    email=email.strip().lower()
    if '@' not in email or len(email)>254 or len(email)<5 or any(c.isspace() for c in email):
        raise ValueError('Email undangan tidak valid')
    url, public_key=validate_config(*settings)
    session=client.auth.get_session()
    if session is None or not session.access_token:
        raise ValueError('Login administrator diperlukan')
    response=httpx.post(url+'/functions/v1/k4-admin-invite',json={'email':email},headers={
        'Authorization':'Bearer '+session.access_token,
        'apikey':public_key,'Content-Type':'application/json',
    },timeout=15.0)
    if response.status_code!=200:
        raise ValueError('Undangan gagal. Periksa deployment Edge Function dan hak admin.')
    return True
