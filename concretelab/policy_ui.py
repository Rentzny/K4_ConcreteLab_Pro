"""Streamlit per-session policy loader without global caches or user data leaks."""
from __future__ import annotations

import streamlit as st
from .cloud_ui import signed_user
from .cloud import get_profile, get_supabase_settings
from .permissions import AccessPolicy, load_access_policy


def current_policy() -> tuple[AccessPolicy, object | None, dict | None]:
    """Fetch settings fresh each rerun: admin changes take effect on next rerun."""
    try:
        configured = get_supabase_settings(st.secrets) is not None
        client, user = signed_user()
    except Exception:
        # If Secrets exist but connection fails, do not grant unverified guest access.
        return load_access_policy(None, cloud_configured=True), None, None
    policy = load_access_policy(client, cloud_configured=configured)
    profile = None
    if user is not None and configured:
        try:
            profile = get_profile(client, str(user.id))
        except Exception:
            profile = None
    return policy, user, profile
