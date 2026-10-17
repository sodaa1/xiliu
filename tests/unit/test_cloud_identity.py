from concurrent.futures import ThreadPoolExecutor

import pytest

from xiliu.api.errors import WebError
from xiliu.cloud.identity import IdentityStore

PASSWORD = "correct horse battery staple"


def test_password_session_revocation_and_restart(tmp_path):
    clock = [1000.0]
    store = IdentityStore(tmp_path, clock=lambda: clock[0])
    alice = store.register("Alice", PASSWORD)
    assert alice["username"] == "alice"
    assert alice["id"] != alice["workspace_id"]
    token = store.login("ALICE", PASSWORD, ttl=60)
    assert store.session(token)["id"] == alice["id"]
    restored = IdentityStore(tmp_path, clock=lambda: clock[0])
    assert restored.session(token) == alice
    raw = (tmp_path / "accounts.sqlite3").read_bytes()
    assert PASSWORD.encode() not in raw and token.encode() not in raw
    with store.connect() as db:
        assert db.execute("SELECT password_hash FROM users").fetchone()[0].startswith("$argon2id$")
    restored.revoke(token)
    with pytest.raises(WebError, match="登录"):
        store.session(token)
    token = restored.login("alice", PASSWORD, ttl=60)
    clock[0] += 61
    with pytest.raises(WebError, match="登录"):
        restored.session(token)


def test_reset_password_revokes_all_sessions_and_credentials_errors_match(tmp_path):
    store = IdentityStore(tmp_path)
    store.register("alice", PASSWORD)
    first, second = (store.login("alice", PASSWORD) for _ in range(2))
    errors = []
    for name in ("alice", "missing"):
        with pytest.raises(WebError) as error:
            store.login(name, "wrong password value")
        errors.append((error.value.code, error.value.message, error.value.status))
    assert errors[0] == errors[1]
    store.reset_password("alice", "another strong password value")
    for token in (first, second):
        with pytest.raises(WebError):
            store.session(token)
    assert (
        store.session(store.login("alice", "another strong password value"))["username"] == "alice"
    )


def test_registration_uniqueness_capacity_and_rate_limits_are_atomic(tmp_path):
    store = IdentityStore(tmp_path, max_users=2)

    def register(_):
        try:
            return store.register("same_name", PASSWORD)["id"]
        except WebError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(value is not None for value in pool.map(register, range(2))) == 1
    store.register("another", PASSWORD)
    with pytest.raises(WebError) as error:
        store.register("third", PASSWORD)
    assert error.value.status == 503

    def hit(_):
        try:
            store.rate_limit("login", "same-ip", limit=2, seconds=60)
            return True
        except WebError as error:
            assert error.status == 429
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(hit, range(4))) == 2


@pytest.mark.parametrize(
    "name,password", [("../escape", PASSWORD), ("ab", PASSWORD), ("alice", "short")]
)
def test_invalid_registration_never_creates_an_account(tmp_path, name, password):
    store = IdentityStore(tmp_path)
    with pytest.raises(WebError):
        store.register(name, password)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 0
