"""Optional, opt-in persistence for Supabase Auth across hard refreshes.

The Streamlit WebSocket/session_state alone is not persistent. Only a Supabase
refresh token is persisted, encrypted with a server-side Fernet key. No password,
access JWT, user ID, or Supabase service key is put into a cookie.

Caveats: this uses a JavaScript-based cookie component, so the cookie itself is
not HttpOnly. Encryption protects token contents from client-side inspection;
a copied encrypted cookie could still be replayed at the same app. Use only on
trusted devices. Supabase always validates the refresh token on restoration.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

COOKIE_NAME = 'k4_remember_auth_v1'
CONTROLLER_KEY = 'k4_remember_cookie_controller'
REMEMBER_DAYS = 7


def _key_from_secrets(secrets):
    """Return a configured Fernet instance, or None if not configured."""
    try:
        config = secrets.get('auth_persistence', {})
        key = str(config.get('fernet_key', '')).strip()
    except (AttributeError, FileNotFoundError, KeyError, TypeError):
        return None
    if not key:
        return None
    from cryptography.fernet import Fernet
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValueError('auth_persistence.fernet_key harus kunci Fernet 32 byte yang valid.') from exc


def persistence_enabled(secrets):
    return _key_from_secrets(secrets) is not None


def pack_refresh_token(refresh_token: str, supabase_url: str, key: bytes) -> str:
    """Encrypt a refresh token, binding it to the specific Supabase project."""
    if not refresh_token or not isinstance(refresh_token, str):
        raise ValueError('Refresh token kosong.')
    from cryptography.fernet import Fernet
    plain = json.dumps({'v': 1, 't': refresh_token, 'project': supabase_url.strip().rstrip('/')},
                       separators=(',', ':')).encode('utf-8')
    return Fernet(key).encrypt(plain).decode('ascii')


def unpack_refresh_token(cookie: str, supabase_url: str, key: bytes, ttl: int = REMEMBER_DAYS * 86400) -> str:
    """Reject expired, tampered, or wrong-project cookies."""
    from cryptography.fernet import Fernet
    if not isinstance(cookie, str) or len(cookie) > 8192:
        raise ValueError('Cookie tidak valid.')
    try:
        data = json.loads(Fernet(key).decrypt(cookie.encode('ascii'), ttl=ttl))
    except Exception as exc:
        raise ValueError('Sesi tersimpan tidak valid atau kedaluwarsa.') from exc
    if (not isinstance(data, dict) or data.get('v') != 1 or
        data.get('project') != supabase_url.strip().rstrip('/') or
        not isinstance(data.get('t'), str) or not data['t']):
        raise ValueError('Sesi tersimpan tidak sesuai proyek Supabase.')
    return data['t']


def cookie_controller():
    # This component is mounted from app.py on *every* rerun, before navigation.
    from streamlit_cookies_controller import CookieController
    return CookieController(key=CONTROLLER_KEY)


def mount_cookie_controller():
    """Mount once per script run so browser can pass cookies after page reload."""
    return cookie_controller()


def _token_key(secrets):
    fernet = _key_from_secrets(secrets)
    return fernet


def clear_browser_remember_cookie():
    try:
        controller = cookie_controller()
        if controller.get(COOKIE_NAME) is not None:
            controller.remove(COOKIE_NAME, path='/', secure=True, same_site='lax')
    except Exception:
        # Do not block sign out when the browser component is unavailable.
        pass


def restore_if_possible(client, settings, secrets, state, cookie_store=None):
    """Restore once when a new Streamlit session receives the browser cookie.

    Returns True only if Supabase actually refreshed/accepted the token. A
    missing cookie is *not* cached, since the component loads asynchronously.
    """
    if client is None or settings is None or state.get('k4_persist_attempted'):
        return False
    fernet = _token_key(secrets)
    if fernet is None:
        return False
    try:
        store = cookie_store if cookie_store is not None else cookie_controller()
        cookie = store.get(COOKIE_NAME)
    except Exception:
        return False
    if not cookie:
        return False
    state['k4_persist_attempted'] = True
    try:
        data = json.loads(fernet.decrypt(cookie.encode('ascii'), ttl=REMEMBER_DAYS*86400))
        if (data.get('v') != 1 or data.get('project') != settings[0].strip().rstrip('/') or
            not isinstance(data.get('t'), str) or not data['t']):
            raise ValueError('Cookie dari proyek lain.')
        response = client.auth.refresh_session(data['t'])
        if not response.session or not response.session.refresh_token:
            raise ValueError('Sesi Supabase sudah tidak berlaku.')
        state['k4_remember_enabled'] = True
        _write_cookie(store, response.session.refresh_token, settings[0], fernet, state)
        return True
    except Exception:
        try: store.remove(COOKIE_NAME, path='/', secure=True, same_site='lax')
        except Exception: pass
        state['k4_remember_enabled'] = False
        return False


def _write_cookie(store, refresh_token, supabase_url, fernet, state):
    if not refresh_token:
        return
    # Don't rewrite the same cookie on every page rerun.
    if state.get('k4_persist_current_token') == refresh_token:
        return
    payload = json.dumps({'v': 1, 't': refresh_token, 'project': supabase_url.strip().rstrip('/')},
                         separators=(',', ':')).encode('utf-8')
    encrypted = fernet.encrypt(payload).decode('ascii')
    store.set(COOKIE_NAME, encrypted, path='/',
              expires=datetime.now(timezone.utc) + timedelta(days=REMEMBER_DAYS),
              secure=True, same_site='lax')
    state['k4_persist_current_token'] = refresh_token


def sync_cookie_if_opted_in(client, settings, secrets, state, cookie_store=None):
    """Save the latest ROTATED Supabase refresh token after sign-in/refresh."""
    if not state.get('k4_remember_enabled') or client is None or settings is None:
        return
    fernet = _token_key(secrets)
    if fernet is None:
        return
    try:
        session = client.auth.get_session()
        if session is not None and session.refresh_token:
            store = cookie_store if cookie_store is not None else cookie_controller()
            _write_cookie(store, session.refresh_token, settings[0], fernet, state)
    except Exception:
        # Persisting is optional; keep normal authentication working.
        pass
