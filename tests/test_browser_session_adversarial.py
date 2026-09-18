from datetime import datetime, timedelta, timezone

from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.sessions import SessionStore


PASSWORD = "Correct-Horse-Battery-99"


def _active_account(db, username="session-adversary"):
    accounts = AccountStore(db)
    accounts.create_user(
        username, PASSWORD, role=Role.ADMIN, status=AccountStatus.ACTIVE
    )
    account = accounts.authenticate(username, PASSWORD)
    assert account is not None
    return account


def test_revoked_session_is_rejected_and_cannot_revalidate(tmp_path):
    db = tmp_path / "sentinel.db"
    account = _active_account(db)
    sessions = SessionStore(db)
    session = sessions.create(account)
    assert sessions.validate(session.token) is not None
    assert sessions.revoke_all(account.user_id) == 1
    assert sessions.validate(session.token) is None
    assert sessions.mfa_verified(session.token) is False


def test_absolute_expiry_rejects_session_even_with_recent_activity(tmp_path):
    db = tmp_path / "sentinel.db"
    account = _active_account(db)
    sessions = SessionStore(db)
    session = sessions.create(account)
    now = datetime.now(timezone.utc)
    with sessions._connect() as connection:
        connection.execute(
            "UPDATE auth_sessions SET expires_at=?, last_seen_at=? WHERE token_hash=?",
            (
                (now - timedelta(seconds=1)).isoformat(),
                now.isoformat(),
                sessions._digest(session.token),
            ),
        )
    assert sessions.validate(session.token) is None


def test_idle_expiry_rejects_session_before_absolute_expiry(tmp_path):
    db = tmp_path / "sentinel.db"
    account = _active_account(db)
    sessions = SessionStore(db, idle_minutes=30, absolute_hours=12)
    session = sessions.create(account)
    now = datetime.now(timezone.utc)
    with sessions._connect() as connection:
        connection.execute(
            "UPDATE auth_sessions SET last_seen_at=?, expires_at=? WHERE token_hash=?",
            (
                (now - timedelta(minutes=31)).isoformat(),
                (now + timedelta(hours=10)).isoformat(),
                sessions._digest(session.token),
            ),
        )
    assert sessions.validate(session.token) is None


def test_disabled_account_invalidates_existing_session(tmp_path):
    db = tmp_path / "sentinel.db"
    accounts = AccountStore(db)
    user_id = accounts.create_user(
        "disabled-session", PASSWORD,
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    account = accounts.authenticate("disabled-session", PASSWORD)
    assert account is not None
    sessions = SessionStore(db)
    session = sessions.create(account)
    assert sessions.validate(session.token) is not None
    with accounts._connect() as connection:
        connection.execute(
            "UPDATE users SET status=? WHERE id=?",
            (AccountStatus.DISABLED.value, user_id),
        )
    assert sessions.validate(session.token) is None
