"""OPTIONAL live RLS test. Run with TWO isolated test accounts, not real users.

Required env: K4_TEST_SUPABASE_URL, K4_TEST_PUBLISHABLE_KEY,
K4_TEST_EMAIL_A, K4_TEST_PASSWORD_A, K4_TEST_EMAIL_B, K4_TEST_PASSWORD_B.
Tests skip when credentials are missing. Does not use a service_role key.
"""
import os
import uuid
import pytest
from concretelab.cloud import new_client, sign_in,create_project,list_projects,save_snapshot
from pathlib import Path

KEYS=['K4_TEST_SUPABASE_URL','K4_TEST_PUBLISHABLE_KEY',
      'K4_TEST_EMAIL_A','K4_TEST_PASSWORD_A','K4_TEST_EMAIL_B','K4_TEST_PASSWORD_B']

@pytest.mark.integration
def test_live_rls_isolation_two_users():
    if any(not os.environ.get(k) for k in KEYS):
        pytest.skip('Butuh dua akun Supabase dummy serta variabel lingkungan test; belum diuji online.')
    a=new_client(os.environ['K4_TEST_SUPABASE_URL'],os.environ['K4_TEST_PUBLISHABLE_KEY'])
    b=new_client(os.environ['K4_TEST_SUPABASE_URL'],os.environ['K4_TEST_PUBLISHABLE_KEY'])
    ua=sign_in(a,os.environ['K4_TEST_EMAIL_A'],os.environ['K4_TEST_PASSWORD_A']).user
    ub=sign_in(b,os.environ['K4_TEST_EMAIL_B'],os.environ['K4_TEST_PASSWORD_B']).user
    assert str(ua.id)!=str(ub.id)
    name='RLS-TEST-'+uuid.uuid4().hex[:12]
    created=create_project(a,str(ua.id),name,'TEST','Proyek untuk audit RLS; hapus otomatis.')
    assert created
    pid=created[0]['id']
    try:
        assert pid in {p['id'] for p in list_projects(a)}
        assert pid not in {p['id'] for p in list_projects(b)}
        csv=(Path(__file__).resolve().parent.parent/'data/contoh_18_silinder.csv').read_bytes()
        snapshot,_=save_snapshot(a,pid,str(ua.id),csv,30)
        assert snapshot
        # Foreign account must see no row even when it knows the snapshot UUID.
        snap_id=snapshot[0]['id']
        response=b.table('k4_snapshots').select('id,csv_text').eq('id',snap_id).execute()
        assert not response.data
        with pytest.raises(Exception):
            save_snapshot(b,pid,str(ub.id),csv,30)
    finally:
        a.table('k4_projects').delete().eq('id',pid).execute()
