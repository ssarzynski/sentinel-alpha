from pathlib import Path

import pytest

from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore


def test_audit_failure_rolls_back_session_revocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "sentinel.db"
    accounts = AccountStore(db)
    sessions = SessionStore(db)
    audit = SecurityAuditLog(db)
    user_id = accounts.create_user(
        "atomicuser", "correct-horse-battery-staple",
        role=Role.USER, status=AccountStatus.ACTIVE,
    )
    account = accounts.authenticate("atomicuser", "correct-horse-battery-staple")
    assert account is not None
    session = sessions.create(account)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(audit, "append_in_connection", fail_audit)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        with accounts._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            sessions.revoke_all_in_connection(connection, user_id)
            audit.append_in_connection(
                connection, "SESSIONS_REVOKED", success=True, target_user_id=user_id
            )

    assert sessions.validate(session.token) is not None


def test_audit_failure_rolls_back_password_policy_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "sentinel.db"
    accounts = AccountStore(db)
    audit = SecurityAuditLog(db)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(audit, "append_in_connection", fail_audit)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        with accounts._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE password_policy SET expiration_days=30 WHERE id=1")
            audit.append_in_connection(
                connection, "PASSWORD_POLICY_CHANGED", success=True
            )

    with accounts._connect() as connection:
        days = connection.execute(
            "SELECT expiration_days FROM password_policy WHERE id=1"
        ).fetchone()["expiration_days"]
    assert days == 90
