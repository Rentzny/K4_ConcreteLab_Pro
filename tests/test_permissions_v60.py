"""Access policy unit tests; live RLS test in staging Supabase is separately required."""
import ast
from pathlib import Path
from types import SimpleNamespace
import pytest

from concretelab.permissions import (
    AccessPolicy, GUEST_FEATURES, DEFAULT_GUEST, CLOSED_GUEST,
    decode_policy_rows, load_access_policy, set_guest_flag, set_guest_preset,
    update_guest_features, update_account_status, is_active_profile,
)


class FakeClient:
    def __init__(self, rows=None, raise_on_select=False):
        self.rows=rows or []
        self.raise_on_select=raise_on_select
        self.calls=[]
    def table(self, name):
        self.calls.append(('table',name))
        return self
    def select(self, columns):
        self.calls.append(('select',columns))
        return self
    def execute(self):
        if self.raise_on_select:
            raise ConnectionError('offline')
        return SimpleNamespace(data=self.rows)
    def rpc(self, name, arguments):
        self.calls.append(('rpc',name,arguments))
        return self


def _rows(enabled=True):
    return ([{'feature_key': k, 'enabled': enabled} for k in GUEST_FEATURES] +
            [{'feature_key':'registration_enabled','enabled':True}])


def test_guest_policy_fully_populated():
    d, signups=decode_policy_rows(_rows())
    assert set(d)==set(GUEST_FEATURES) and signups
    assert all(d.values())

@pytest.mark.parametrize('bad', [
    _rows()[:-1],
    _rows()+[{'feature_key':'summary','enabled':True}],
    _rows()[:-1]+[{'feature_key':'registration_enabled','enabled':'true'}],
])
def test_incomplete_duplicate_wrong_type_rejected(bad):
    with pytest.raises(ValueError):decode_policy_rows(bad)


def test_unknown_values_not_privileges():
    rows=_rows()+[{'feature_key':'admin','enabled':True}]
    d,_=decode_policy_rows(rows)
    assert 'admin' not in d


def test_local_demo_compatibility():
    p=load_access_policy(None,cloud_configured=False)
    assert p.source.startswith('mode lokal')
    assert p.allowed('summary')


def test_remote_error_closes_guest_access():
    p=load_access_policy(FakeClient(raise_on_select=True),cloud_configured=True)
    assert p.cloud_configured
    assert not any(p.guest.values())
    assert not p.registration_enabled


def test_remote_missing_migration_closes_access():
    p=load_access_policy(FakeClient(rows=[{'feature_key':'summary','enabled':True}]),cloud_configured=True)
    assert not p.allowed('summary')


def test_admin_config_is_read_each_call_no_global_cache():
    client=FakeClient(_rows())
    a=load_access_policy(client,cloud_configured=True)
    client.rows=_rows(False)
    b=load_access_policy(client,cloud_configured=True)
    assert a.allowed('summary') and not b.allowed('summary')


def test_only_active_signed_in_get_all_analytics():
    policy=AccessPolicy(dict(CLOSED_GUEST),True,'test',False)
    assert policy.allowed('visuals',logged_in=True,account_active=True)
    assert not policy.allowed('visuals',logged_in=True,account_active=False)
    assert not policy.allowed('visuals',logged_in=False,account_active=True)


def test_admin_and_unauthorized_special_features_not_guest_features():
    p=AccessPolicy(dict(DEFAULT_GUEST),True,'test')
    for privileged in ['admin', 'cloud_projects', 'report_approve', 'users', 'secrets']:
        with pytest.raises(ValueError):p.allowed(privileged)


def test_single_flag_rpc_whitelist():
    c=FakeClient()
    set_guest_flag(c,feature='visuals',enabled=False)
    assert ('rpc','k4_admin_set_public_setting',{'p_feature':'visuals','p_enabled':False}) in c.calls
    with pytest.raises(ValueError):set_guest_flag(c,feature='admin',enabled=True)
    with pytest.raises(ValueError):set_guest_flag(c,feature='reports',enabled='true')


def test_registration_toggled_by_same_admin_rpc():
    c=FakeClient()
    set_guest_flag(c,feature='registration_enabled',enabled=False)
    assert ('rpc','k4_admin_set_public_setting',{'p_feature':'registration_enabled','p_enabled':False}) in c.calls


def test_atomic_bulk_whole_feature_set_required():
    c=FakeClient(); flags=dict(DEFAULT_GUEST); flags['visuals']=False
    update_guest_features(c,flags)
    assert ('rpc','k4_admin_set_guest_features',{'p_values':flags}) in c.calls
    with pytest.raises(ValueError):update_guest_features(c,{'summary':True})
    with pytest.raises(ValueError):update_guest_features(c,dict(DEFAULT_GUEST,admin=True))


def test_presets_server_transactions():
    c=FakeClient()
    for p in ('all_analytics','basic_only','closed'):
        set_guest_preset(c,preset=p)
    with pytest.raises(ValueError):set_guest_preset(c,preset='unlimited_admin')
    assert len([call for call in c.calls if call[1]=='k4_admin_guest_preset'])==3


def test_status_changes_restricted():
    c=FakeClient()
    update_account_status(c,'11111111-1111-1111-1111-111111111111','active')
    with pytest.raises(ValueError):update_account_status(c,'x','root')
    assert is_active_profile({'account_status':'active'})
    assert not is_active_profile({'account_status':'pending'})
    assert not is_active_profile(None)


def test_sql_security_invariants():
    root=Path(__file__).resolve().parents[1]
    v6=(root/'supabase/schema_v60.sql').read_text()
    for phrase in ['ENABLE ROW LEVEL SECURITY', 'k4_account_active()',
        'SECURITY DEFINER', 'public.k4_is_admin()',
        'account_status=\'active\'', 'k4_admin_guest_preset',
        'REVOKE ALL ON FUNCTION public.k4_admin_guest_preset',
        'k4_admin_set_guest_features', 'auth.uid()',
        'UPDATE public.k4_profiles SET account_status=\'active\'',
        'WHERE feature_key <> \'registration_enabled\'']:
        assert phrase in v6
    assert 'GRANT INSERT ON public.k4_public_settings TO anon' not in v6


def test_app_cloud_nav_hardcoded_verification():
    root=Path(__file__).resolve().parents[1]
    for f in ('app.py','app_pages/service.py','app_pages/account.py','app_pages/workspace.py','app_pages/admin.py'):
        ast.parse((root/f).read_text(),filename=f)
    content=(root/'app_pages/service.py').read_text()
    assert content.count('if permitted(')>=13
    assert 'if not permitted(\'upload_csv\')' in content
    assert 'return st.download_button(*args, **kwargs)' in content
    assert content.count('st.download_button(')==1
    assert 'if permitted(\'edit_csv\')' in content
    assert 'if permitted(\'tracking\')' in content
    assert 'if permitted(\'archive\')' in content
    assert 'if permitted(\'simulation\')' in content


def test_admin_page_uses_verified_admin():
    root=Path(__file__).resolve().parents[1]
    s=(root/'app_pages/admin.py').read_text()
    assert "profile.get('global_role') != 'admin'" in s
    assert 'is_active_profile(profile)' in s
    assert 'update_guest_features' in s
    assert 'st.rerun()' in s


def test_registration_protected_by_page_flag():
    root=Path(__file__).resolve().parents[1]
    account=(root/'app_pages/account.py').read_text()
    # v8 moved the sign-up form to the shared auth component (welcome + Akun),
    # but kept the server-backed registration_enabled flag and its UI guard.
    views=(root/'concretelab/auth_views.py').read_text()
    assert 'registration_enabled and client is not None' in views
    assert 'load_access_policy(' in account
    assert 'render_auth_forms(' in account
    workspace=(root/'app_pages/workspace.py').read_text()
    assert "profile.get('account_status') != 'active'" in workspace


def test_admin_invite_client_uses_only_user_jwt_and_publishable_key(monkeypatch):
    from concretelab.cloud import invite_account_by_email
    import sys
    # Keep unit test offline: mock external HTTP client.
    class FakeHTTP:
        def post(self,url,**kwargs):
            assert url=='https://demo.supabase.co/functions/v1/k4-admin-invite'
            assert kwargs['headers']['Authorization']=='Bearer user-access-token'
            assert kwargs['headers']['apikey']=='public-key-which-is-long-enough'
            assert kwargs['json']=={'email':'person@example.com'}
            assert 'service_role' not in str(kwargs)
            return SimpleNamespace(status_code=200)
    monkeypatch.setitem(sys.modules,'httpx',FakeHTTP())
    client=SimpleNamespace(auth=SimpleNamespace(get_session=lambda:SimpleNamespace(access_token='user-access-token')))
    assert invite_account_by_email(client,('https://demo.supabase.co','public-key-which-is-long-enough'), ' Person@Example.Com ')


def test_admin_invite_rejects_unsafe_input_before_http():
    from concretelab.cloud import invite_account_by_email
    client=SimpleNamespace(auth=SimpleNamespace(get_session=lambda: None))
    with pytest.raises(ValueError):
        invite_account_by_email(client,('https://demo.supabase.co','public-key-which-is-long-enough'),'not-an-email')
    with pytest.raises(ValueError):
        invite_account_by_email(client,('https://demo.supabase.co','public-key-which-is-long-enough'),'person@example.com')


def test_edge_invite_checks_verified_jwt_active_admin_and_limits():
    root=Path(__file__).resolve().parents[1]
    s=(root/'supabase/functions/k4-admin-invite/index.ts').read_text()
    assert 'auth.getUser(jwt)' in s
    assert "profile.global_role !== 'admin'" in s
    assert "profile.account_status !== 'active'" in s
    assert 'inviteUserByEmail(email)' in s
    assert 'count ?? 0' in s
    assert "Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')" in s
    app=(root/'app_pages/admin.py').read_text()
    assert 'invite_account_by_email(client,settings,invite_email)' in app
    assert 'service_role' not in (root/'concretelab/permissions.py').read_text()
