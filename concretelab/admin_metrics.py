"""Pure helpers for ConcreteLab Pro v7 administrator overview.

Do not aggregate confidential CSV contents. Only counts and metadata already
retrieved under an authenticated administrator's RLS privileges are used.
"""
from __future__ import annotations
from collections import Counter
from typing import Iterable, Mapping

REPORT_STATES = ('draft', 'submitted', 'needs_revision', 'approved', 'rejected')
USER_STATES = ('pending', 'active', 'suspended')


def summarize_admin(
    profiles: Iterable[Mapping],
    projects: Iterable[Mapping],
    reports: Iterable[Mapping],
    guest_flags: Mapping[str, bool],
) -> dict:
    """Return bounded, deterministic overview statistics without PII."""
    profiles, projects, reports = list(profiles), list(projects), list(reports)
    user_counts = Counter(str(row.get('account_status', 'unknown')) for row in profiles)
    report_counts = Counter(str(row.get('status', 'unknown')) for row in reports)
    admins = sum(row.get('global_role') == 'admin' for row in profiles)
    return {
        'accounts': len(profiles),
        'active_accounts': user_counts['active'],
        'pending_accounts': user_counts['pending'],
        'suspended_accounts': user_counts['suspended'],
        'admins': admins,
        'projects': len(projects),
        'reports': len(reports),
        'awaiting_review': report_counts['submitted'],
        'approved_reports': report_counts['approved'],
        'guest_enabled': sum(v is True for v in guest_flags.values()),
        'guest_total': len(guest_flags),
        'user_status_counts': {key: user_counts[key] for key in USER_STATES},
        'report_status_counts': {key: report_counts[key] for key in REPORT_STATES},
    }


def guest_mode_label(flags: Mapping[str, bool]) -> str:
    if not flags or not any(flags.values()):
        return 'Tertutup'
    if all(flags.values()):
        return 'Semua analisis aktif'
    basic = {'upload_csv', 'summary', 'statistics', 'visuals', 'method'}
    if all(flags.get(key, False) == (key in basic) for key in flags):
        return 'Akses dasar'
    return 'Kustom'


def safe_percent(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0
