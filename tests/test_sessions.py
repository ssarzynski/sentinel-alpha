from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.sessions import SessionStore, change_password


def test_bootstrap_session_is_password_change_only(tmp_path):
    db = tmp_path / "auth.db"
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "temporary-test-passphrase", role=Role.ADMIN,
        status=AccountStatus.ACTIVE, must_change_password=True,
    )
    account = accounts.authenticate("administrator", "temporary-test-passphrase")
    assert account is not None
    sessions = SessionStore(db)
    session = sessions.create(account)
    assert session.restricted_to_password_change is True
    assert sessions.validate(session.token) is None
    assert sessions.validate(session.token, allow_password_change_only=True) is not None


def test_password_change_revokes_old_session_and_old_password(tmp_path):
    db = tmp_path / "auth.db"
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "temporary-test-passphrase", role=Role.ADMIN,
        status=AccountStatus.ACTIVE, must_change_password=True,
    )
    account = accounts.authenticate("administrator", "temporary-test-passphrase")
    assert account is not None
    sessions = SessionStore(db)
    session = sessions.create(account)
    change_password(
        accounts, sessions, account=account,
        current_password="temporary-test-passphrase",
        new_password="replacement-test-passphrase",
    )
    assert sessions.validate(session.token, allow_password_change_only=True) is None
    assert accounts.authenticate("administrator", "temporary-test-passphrase") is None
    replacement = accounts.authenticate("administrator", "replacement-test-passphrase")
    assert replacement is not None
    assert replacement.must_change_password is False
    assert sessions.create(replacement).restricted_to_password_change is False


def test_disabled_account_invalidates_existing_session(tmp_path):
    db = tmp_path / "auth.db"
    accounts = AccountStore(db)
    user_id = accounts.create_user(
        "member", "long-test-passphrase", status=AccountStatus.ACTIVE
    )
    account = accounts.authenticate("member", "long-test-passphrase")
    assert account is not None
    sessions = SessionStore(db)
    session = sessions.create(account)
    with accounts._connect() as connection:
        connection.execute("UPDATE users SET status='DISABLED' WHERE id=?", (user_id,))
    assert sessions.validate(session.token) is None


def test_compromised_password_lookup_uses_only_sha1_prefix(monkeypatch):
    import io
    import hashlib
    from sentinel_alpha.sessions import compromised_password_count

    password = "known-compromised-test-passphrase"
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    seen = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return f"{digest[5:]}:42\r\nDEADBEEF:0\r\n".encode()

    def fake_open(request, timeout):
        seen["url"] = request.full_url
        seen["padding"] = request.get_header("Add-padding")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    assert compromised_password_count(password) == 42
    assert password not in seen["url"]
    assert digest not in seen["url"]
    assert seen["url"].endswith(digest[:5])
    assert seen["padding"] == "true"


def test_compromised_password_lookup_fails_open_when_service_unavailable(monkeypatch):
    from sentinel_alpha.sessions import compromised_password_count

    def unavailable(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    assert compromised_password_count("offline-safe-test-passphrase") is None
