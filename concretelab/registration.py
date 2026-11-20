"""Registration input validation for ConcreteLab Pro v8.

This only improves UI feedback. Supabase Auth owns passwords and email
verification; PostgreSQL/RLS own account and data authorization.
"""
from __future__ import annotations
import re

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def check_registration(email: str, password: str, confirmation: str) -> tuple[bool, str]:
    if not isinstance(email, str) or not EMAIL_RE.fullmatch(email.strip()) or len(email.strip()) > 254:
        return False, 'Masukkan alamat email yang valid.'
    if not isinstance(password, str) or len(password) < 8:
        return False, 'Password harus terdiri dari minimal 8 karakter.'
    if len(password) > 128:
        return False, 'Password maksimal 128 karakter.'
    if password != confirmation:
        return False, 'Konfirmasi password tidak sama. Ketik ulang kedua password.'
    return True, ''


def registration_requires_admin_approval() -> bool:
    """v8 account bootstrap is handled by SQL v8 migration default ACTIVE.

    This function documents UI behavior only; never use it for authentication
    or database access decisions.
    """
    return False
