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
