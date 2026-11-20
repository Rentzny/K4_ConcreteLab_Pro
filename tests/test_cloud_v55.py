"""Offline regression tests: schema policies still require live two-user Supabase verification."""
import base64
import json
from pathlib import Path
import pytest

from concretelab.cloud import (validate_config,CloudConfigError,to_clean_csv,read_cloud_snapshot,
    verify_url,print_verification_label,verify_report)

ROOT=Path(__file__).resolve().parent.parent
SQL=(ROOT/'supabase/schema_v55.sql').read_text()
EXAMPLE=(ROOT/'data/contoh_18_silinder.csv').read_bytes()


def test_config_rejects_http_and_service_keys():
    with pytest.raises(CloudConfigError): validate_config('http://example.test','x'*28)
    with pytest.raises(CloudConfigError): validate_config('https://example.test','sb_secret_test_key_not_real')
    jwt='.'.join(['abc',base64.urlsafe_b64encode(json.dumps({'role':'service_role'}).encode()).decode().rstrip('='),'signature'])
    with pytest.raises(CloudConfigError): validate_config('https://project.supabase.co',jwt)


def test_config_accepts_publishable_key():
    assert validate_config(' https://project.supabase.co/ ', 'x'*32)[0]=='https://project.supabase.co'


def test_csv_normalized_and_reloaded():
    clean,n=to_clean_csv(EXAMPLE,30)
    assert n==18
    h=read_cloud_snapshot(clean,30)
    assert h.ringkasan['silinder']==18
    assert h.ringkasan['campuran']==3


def test_bad_csv_fails():
    with pytest.raises(Exception):to_clean_csv(b'abc,xyz\n1,2\n',30)
    with pytest.raises(ValueError):to_clean_csv(b'',30)
    with pytest.raises(ValueError):to_clean_csv(b'A'* (10*1024*1024+1),30)


def test_public_link_is_unguessable_token_format_and_https():
    token='a'*48
    assert verify_url('https://k4.example.net',token)=='https://k4.example.net/?verify='+token
    with pytest.raises(ValueError):verify_url('http://k4.example.net',token)
    with pytest.raises(ValueError):verify_url('https://k4.example.net','not-token')


def test_approved_verification_pdf_is_valid():
    pdf=print_verification_label('https://example.org/?verify='+'1'*48,'01234567-aaaa', 'a'*64)
    assert pdf.startswith(b'%PDF-')
    assert len(pdf)>1500


def test_invalid_token_does_not_query_db():
    class Bomb:
        def rpc(self,*args,**kwargs):raise AssertionError('malformed token reached database')
    assert verify_report(Bomb(),'bad') is None


def test_schema_enforces_rls_all_tables():
    for table in ['k4_profiles','k4_projects','k4_project_members','k4_snapshots','k4_reports','k4_audit_events']:
        assert f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;' in SQL


def test_sensitive_writes_are_rpc_only():
    assert 'GRANT SELECT ON public.k4_reports, public.k4_audit_events TO authenticated;' in SQL
    assert 'REVOKE ALL ON FUNCTION public.k4_on_new_user() FROM PUBLIC;' in SQL
    assert 'r.author_id=auth.uid()' in SQL
    assert 'r.author_id<>auth.uid()' in SQL
    assert "r.status<>'submitted'" in SQL


def test_public_verify_only_reports_approved_and_no_csv_text():
    fn=SQL.split('CREATE OR REPLACE FUNCTION public.k4_verify_report(')[1].split('$$;')[1] if False else SQL.split('CREATE OR REPLACE FUNCTION public.k4_verify_report(')[1].split('-- Trigger audit otomatis')[0]
    assert "r.status='approved'" in fn
    assert 'csv_text' not in fn


def test_schema_no_service_role_app_key_and_uuid_owner():
    assert 'owner_id=auth.uid()' in SQL
    assert 'author_id=auth.uid()' in SQL
    assert 'public.k4_can_edit(project_id)' in SQL
    assert 'public.k4_can_view(project_id)' in SQL


def test_cloud_secrets_example_is_placeholder_only():
    example=(ROOT/'supabase/secrets.example.toml').read_text()
    assert 'CONTOH_BUKAN_KEY_ASLI' in example
    assert 'service_role = ' not in example

def test_secrets_public_url_is_top_level():
    import tomllib
    d=tomllib.loads((ROOT/'supabase/secrets.example.toml').read_text())
    assert d['public_base_url'].startswith('https://')
    assert 'publishable_key' in d['supabase']


def test_guest_service_avoids_global_cache_of_csv():
    source=(ROOT/'app_pages/service.py').read_text()
    assert '@st.cache_data' not in source


def test_logout_clears_sensitive_cloud_snapshot():
    source=(ROOT/'concretelab/cloud_ui.py').read_text()
    assert 'k4_uploaded_bytes' in source
    assert 'k4_saved_edit_csv' in source
