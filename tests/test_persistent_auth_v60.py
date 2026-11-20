"""Session cookie unit tests; run without Supabase network or browser."""
import pytest
from cryptography.fernet import Fernet
from concretelab.persistent_session import (
    COOKIE_NAME, REMEMBER_DAYS, pack_refresh_token, unpack_refresh_token,
    persistence_enabled, restore_if_possible, sync_cookie_if_opted_in,
)

URL = 'https://example.supabase.co'

class CookieStore:
    def __init__(self, initial=None):
        self.items = {} if initial is None else dict(initial)
        self.options = {}
        self.removed = []
    def get(self, name): return self.items.get(name)
    def set(self, name, value, **kw):
        self.items[name] = value
        self.options = kw
    def remove(self, name, **kw):
        self.items.pop(name, None)
        self.removed.append(name)

class Auth:
    def __init__(self):
        self.refresh_count = 0
        self.existing = None
    def refresh_session(self, token):
        self.refresh_count += 1
        if token == 'bad':
            raise ValueError('invalid refresh token')
        from types import SimpleNamespace
        self.existing = SimpleNamespace(refresh_token='rotated-'+token)
        return SimpleNamespace(session=self.existing)
    def get_session(self):
        return self.existing

class Client:
    def __init__(self): self.auth = Auth()

@pytest.fixture
def secret():
    key = Fernet.generate_key()
    return key, {'auth_persistence': {'fernet_key': key.decode()}}


def test_encrypt_and_restore_token(secret):
    key, settings = secret
    ciphertext = pack_refresh_token('old-123', URL, key)
    assert b'old-123' not in ciphertext.encode()
    assert unpack_refresh_token(ciphertext, URL+'/', key) == 'old-123'


def test_wrong_project_cannot_restore(secret):
    key, _ = secret
    cookie = pack_refresh_token('old', URL, key)
    with pytest.raises(ValueError): unpack_refresh_token(cookie, 'https://other.supabase.co', key)


def test_tampered_cookie_rejected(secret):
    key, _ = secret
    cookie = pack_refresh_token('old', URL, key)
    with pytest.raises(ValueError): unpack_refresh_token(cookie+'x', URL, key)


def test_expired_cookie_rejected(secret):
    key, _ = secret
    from cryptography.fernet import Fernet
    import time
    original = pack_refresh_token('old', URL, key)
    from cryptography.fernet import Fernet
    token = Fernet(key).encrypt_at_time(b'{"v":1,"t":"old","project":"https://example.supabase.co"}',
                                        int(time.time())-10*86400).decode('ascii')
    with pytest.raises(ValueError): unpack_refresh_token(token, URL, key, ttl=7*86400)


def test_resume_rotates_cookie_and_opt_in_state(secret):
    key, settings = secret
    store = CookieStore({COOKIE_NAME: pack_refresh_token('old-123', URL, key)})
    client, state = Client(), {}
    assert restore_if_possible(client, (URL, 'public-key'), settings, state, store)
    assert client.auth.refresh_count == 1
    assert state['k4_remember_enabled'] is True
    assert state['k4_persist_attempted'] is True
    assert store.options['secure'] is True
    assert store.options['same_site'] == 'lax'
    assert unpack_refresh_token(store.items[COOKIE_NAME], URL, key) == 'rotated-old-123'
    assert not restore_if_possible(client, (URL, 'public-key'), settings, state, store)
    assert client.auth.refresh_count == 1


def test_invalid_cookie_cleared_and_not_authenticated(secret):
    key, settings = secret
    store = CookieStore({COOKIE_NAME: pack_refresh_token('bad', URL, key)})
    client, state = Client(), {}
    assert not restore_if_possible(client, (URL, 'public-key'), settings, state, store)
    assert COOKIE_NAME in store.removed
    assert state['k4_remember_enabled'] is False


def test_missing_cookie_does_not_set_attempted(secret):
    key, settings = secret
    client, state, store = Client(), {}, CookieStore()
    assert not restore_if_possible(client, (URL, 'public-key'), settings, state, store)
    assert 'k4_persist_attempted' not in state
    assert client.auth.refresh_count == 0


def test_refresh_token_rotation_synced_once(secret):
    key, settings = secret
    client, state, store = Client(), {'k4_remember_enabled': True}, CookieStore()
    client.auth.existing = type('Session', (), {'refresh_token': 'new-token'})()
    sync_cookie_if_opted_in(client, (URL, 'public-key'), settings, state, store)
    first = store.items[COOKIE_NAME]
    sync_cookie_if_opted_in(client, (URL, 'public-key'), settings, state, store)
    assert store.items[COOKIE_NAME] == first
    client.auth.existing.refresh_token = 'newer-token'
    sync_cookie_if_opted_in(client, (URL, 'public-key'), settings, state, store)
    assert unpack_refresh_token(store.items[COOKIE_NAME], URL, key) == 'newer-token'


def test_no_secret_disables_persistence():
    assert persistence_enabled({}) is False


def test_invalid_secret_is_reported():
    with pytest.raises(ValueError): persistence_enabled({'auth_persistence': {'fernet_key': 'not-a-valid-key'}})
