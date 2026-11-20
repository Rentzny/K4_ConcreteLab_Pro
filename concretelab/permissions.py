"""ConcreteLab v6 permissions: admin-managed guest capabilities, not arbitrary roles.

Guest gates govern only public, session-local analysis views; they NEVER grant
access to authenticated Supabase projects, users, approval or SQL management.
Database RLS independently controls persistent user/project records.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# Keep stable SQL keys; no editable dynamic RPC/function/table names.
GUEST_FEATURES: dict[str, str] = {
    'upload_csv': 'Upload CSV dan analisis dasar',
    'edit_csv': 'Edit data CSV dalam sesi',
    'summary': 'Ringkasan eksekutif',
    'statistics': 'Tabel dan statistik lanjutan',
    'quality': 'Evaluasi mutu',
    'visuals': 'Visualisasi dan grafik interaktif',
    'simulation': 'Simulasi target dan skenario beban',
    'comparison': 'Bandingkan dua CSV',
    'audit': 'Audit data terperinci',
    'exports': 'Unduh CSV, PDF, ZIP, dan label',
    'archive': 'Arsip proyek lokal',
    'tracking': 'Pelacakan sampel dan jadwal',
    'method': 'Penjelasan metode',
}
DEFAULT_GUEST: dict[str, bool] = {k: True for k in GUEST_FEATURES}
# When a configured DB exists but permissions cannot be checked, fail closed.
CLOSED_GUEST: dict[str, bool] = {k: False for k in GUEST_FEATURES}

# Existing deployments without Supabase still work as offline demo; these flags
# are NOT advertised as cloud-admin enforced without the v6 schema.


@dataclass(frozen=True)
class AccessPolicy:
    guest: Mapping[str, bool]
    cloud_configured: bool
    source: str
    registration_enabled: bool = True

    def allowed(self, feature: str, *, logged_in: bool = False, account_active: bool = False) -> bool:
        if feature not in GUEST_FEATURES:
            raise ValueError(f'Fitur tidak dikenal: {feature}')
        if logged_in and account_active:
            return True
        # Unknown, pending, suspended accounts get public permissions only.
        return bool(self.guest.get(feature, False))


def decode_policy_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, bool], bool]:
    """Require every expected key. Invalid/missing rows deny guest privileges."""
    seen: dict[str, bool] = {}
    for record in rows:
        name = record.get('feature_key')
        flag = record.get('enabled')
        if name not in GUEST_FEATURES and name != 'registration_enabled':
            continue
        if type(flag) is not bool or name in seen:
            raise ValueError('Kebijakan izin tamu tidak valid / duplikat')
        seen[name] = flag
    if set(seen) != set(GUEST_FEATURES) | {'registration_enabled'}:
        raise ValueError('Kebijakan izin tamu belum lengkap')
    return {key: seen[key] for key in GUEST_FEATURES}, seen['registration_enabled']


def load_access_policy(client, *, cloud_configured: bool) -> AccessPolicy:
    if not cloud_configured:
        return AccessPolicy(dict(DEFAULT_GUEST), False, 'mode lokal tanpa kendali cloud')
    if client is None:
        return AccessPolicy(dict(CLOSED_GUEST), True, 'gagal membaca; seluruh izin tamu diblokir', False)
    try:
        r = client.table('k4_public_settings').select('feature_key,enabled').execute()
        guest, reg = decode_policy_rows(r.data or [])
        return AccessPolicy(guest, True, 'pengaturan administrator dari Supabase', reg)
    except Exception:
        return AccessPolicy(dict(CLOSED_GUEST), True, 'kebijakan tidak dapat diverifikasi (tertutup)', False)


def set_guest_flag(client, *, feature: str, enabled: bool):
    """Write via SQL SECURITY DEFINER RPC that checks active admin identity."""
    if feature not in GUEST_FEATURES and feature != 'registration_enabled':
        raise ValueError('Fitur tidak dikenal')
    if type(enabled) is not bool:
        raise ValueError('Status harus boolean')
    return client.rpc('k4_admin_set_public_setting', {
        'p_feature': feature, 'p_enabled': enabled,
    }).execute().data


def set_guest_preset(client, *, preset: str):
    """A single DB transaction (no intermediate partial states)."""
    if preset not in ('all_analytics', 'basic_only', 'closed'):
        raise ValueError('Preset tidak dikenal')
    return client.rpc('k4_admin_guest_preset', {'p_preset': preset}).execute().data


def update_account_status(client, user_id: str, status: str):
    if status not in ('active','pending','suspended'):
        raise ValueError('Status akun tidak dikenal')
    return client.rpc('k4_admin_set_account_status', {
        'p_user': str(user_id), 'p_status': status,
    }).execute().data


def is_active_profile(profile: dict | None) -> bool:
    return bool(profile and profile.get('account_status') == 'active')


def update_guest_features(client, values: Mapping[str, bool]):
    if set(values) != set(GUEST_FEATURES) or any(type(v) is not bool for v in values.values()):
        raise ValueError('Semua izin tamu harus disediakan sebagai boolean')
    return client.rpc('k4_admin_set_guest_features', {'p_values': dict(values)}).execute().data
