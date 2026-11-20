"""v7 administrator summary and upgrade contract; no cloud credentials needed."""
import ast
from pathlib import Path
from concretelab.admin_metrics import summarize_admin, guest_mode_label, safe_percent
from concretelab.permissions import GUEST_FEATURES
from concretelab.cloud import validate_config, CloudConfigError
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_admin_overview_counts_and_does_not_expose_emails():
    report = summarize_admin(
        [{'email':'private@sample.org','global_role':'admin','account_status':'active'},
         {'email':'other@sample.org','global_role':'user','account_status':'pending'}],
        [{'id':'P1'}],
        [{'status':'submitted'}, {'status':'approved'}, {'status':'approved'}],
        {k:True for k in GUEST_FEATURES},
    )
    assert (report['accounts'],report['pending_accounts'],report['projects'],report['reports']) == (2,1,1,3)
    assert report['admins'] == 1
    assert report['awaiting_review'] == 1
    assert report['approved_reports'] == 2
    assert report['guest_enabled'] == len(GUEST_FEATURES)
    assert 'private@sample.org' not in str(report)


def test_empty_dashboard_is_valid():
    result=summarize_admin([],[],[],{})
    assert result['accounts'] == 0
    assert result['pending_accounts'] == 0
    assert safe_percent(0,0)==0.0


def test_guest_mode_templates():
    assert guest_mode_label({k:True for k in GUEST_FEATURES}) == 'Semua analisis aktif'
    assert guest_mode_label({k:False for k in GUEST_FEATURES}) == 'Tertutup'
    basic={'upload_csv','summary','statistics','visuals','method'}
    assert guest_mode_label({k:k in basic for k in GUEST_FEATURES}) == 'Akses dasar'
    flags={k:True for k in GUEST_FEATURES}
    flags['exports']=False
    assert guest_mode_label(flags) == 'Kustom'
    assert safe_percent(4,5)==80.0


@pytest.mark.parametrize('bad',[
    'https://myproject.supabase.co/rest/v1/',
    'https://myproject.supabase.co/auth/v1',
    'https://myproject.supabase.co?x=1',
    'https://myproject.supabase.co/#fragment',
])
def test_old_rest_endpoint_secrets_rejected(bad):
    with pytest.raises(CloudConfigError, match='Project URL'):
        validate_config(bad,'sb_publishable_'+'x'*30)


def test_v7_files_integrated_with_v55_install():
    for file in ('app.py','app_pages/admin.py','app_pages/account.py','concretelab/persistent_session.py'):
        ast.parse((ROOT/file).read_text())
    app=(ROOT/'app.py').read_text()
    assert 'app_pages/admin.py' in app
    assert 'mount_cookie_controller' in app
    admin=(ROOT/'app_pages/admin.py').read_text()
    for phrase in ('k4_admin_guest_preset','Simpan 13 izin tamu','k4_admin_set_role','k4_admin_events',
                   'update_account_status',"st.tabs(", "st.metric"):
        if phrase=='st.metric':
            assert 'col.metric(' in admin
        elif phrase=='k4_admin_guest_preset':
            # called through typed permissions helper
            assert 'set_guest_preset(' in admin
        else:
            assert phrase in admin
    assert "if user is None or not is_active_profile(profile)" in admin
    assert "if not candidates:" in admin


def test_fixed_initial_schema_replaces_nonimmutable_generated_expression():
    sql=(ROOT/'supabase/schema_v55.sql').read_text()
    assert "digest(csv_text,'sha256')" in sql
    assert "digest(convert_to(csv_text,'UTF8')" not in sql
