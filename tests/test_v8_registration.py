"""v8 unit and upgrade contract tests: no live cloud credentials needed."""
import ast
from pathlib import Path
import pytest
from concretelab.registration import check_registration, registration_requires_admin_approval
from concretelab.permissions import GUEST_FEATURES, AccessPolicy

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('email,first,second,valid', [
    ('new@example.com', 'x'*8, 'x'*8, True),
    (' new@example.com ', 'abcdefgh', 'abcdefgh', True),
    ('no-at-domain', 'abcdefgh', 'abcdefgh', False),
    ('bad @example.com', 'abcdefgh', 'abcdefgh', False),
    ('good@example.com', 'short', 'short', False),
    ('good@example.com', 'abcdefgh', 'abcdEFgh', False),
    ('good@example.com', 'abcdefgh', '', False),
    ('good@example.com', 'a'*129, 'a'*129, False),
])
def test_signup_validation(email,first,second,valid):
    ok,_=check_registration(email,first,second)
    assert ok is valid


def test_no_manual_approval_for_new_registrations():
    assert registration_requires_admin_approval() is False
    sql=(ROOT/'supabase/schema_v80.sql').read_text(encoding='utf-8')
    assert "ALTER COLUMN account_status SET DEFAULT 'active'" in sql
    assert 'UPDATE public.k4_profiles SET account_status' not in sql
    assert "global_role" in sql
    assert 'BEGIN;' in sql and 'COMMIT;' in sql


def test_guest_mode_keeps_private_permissions_separate():
    policy=AccessPolicy(guest={x: True for x in GUEST_FEATURES},
                        cloud_configured=True,source='test')
    assert policy.allowed('upload_csv')
    with pytest.raises(ValueError):
        policy.allowed('admin_users')
    with pytest.raises(ValueError):
        policy.allowed('private_projects')


def test_new_pages_have_valid_python_and_flexible_navigation():
    paths=['app.py','app_pages/welcome.py','app_pages/account.py',
           'app_pages/admin.py','concretelab/auth_views.py', 'concretelab/registration.py']
    for file in paths:
        ast.parse((ROOT/file).read_text(encoding='utf-8'))
    app=(ROOT/'app.py').read_text(encoding='utf-8')
    assert "app_pages/welcome.py" in app
    assert "position='hidden'" in app
    assert "app_pages/service.py" in app
    assert "if _signed_in_user is None and not st.session_state.get('k4_guest_continue', False)" in app
    welcome=(ROOT/'app_pages/welcome.py').read_text(encoding='utf-8')
    assert 'max-width:680px' in welcome
    assert 'st.columns(' in welcome
    views=(ROOT/'concretelab/auth_views.py').read_text(encoding='utf-8')
    for text in ('Konfirmasi password','Sudah punya akun? Masuk',
                 'Belum punya akun? Daftar sekarang','Lanjutkan sebagai Tamu',
                 'Ingat saya selama 7 hari','check_registration('):
        assert text in views
    assert 'service_role' not in views


def test_v8_admin_page_explains_new_registrations_auto_active():
    admin=(ROOT/'app_pages/admin.py').read_text(encoding='utf-8')
    assert 'akun baru otomatis aktif' in admin
    assert "k4_admin_set_role" in admin
    assert "Simpan 13 izin tamu" in admin


def test_sql_migration_only_changes_default_and_prechecks():
    sql=(ROOT/'supabase/schema_v80.sql').read_text(encoding='utf-8')
    assert "to_regclass('public.k4_profiles')" in sql
    assert "to_regclass('public.k4_public_settings')" in sql
    assert 'DROP TABLE' not in sql.upper()
    assert 'DISABLE ROW LEVEL SECURITY' not in sql.upper()
    assert 'DROP POLICY' not in sql.upper()
