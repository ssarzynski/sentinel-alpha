from pathlib import Path

from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.auth_service import AuthenticationService
from sentinel_alpha.browser_auth import _record_recovery_failure, _recovery_attempt_allowed
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore


def test_recovery_failures_follow_account_across_sessions(monkeypatch, tmp_path: Path):
    db = tmp_path / "recovery-limit.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user("ratelimitadmin", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE)
    admin = accounts.authenticate("ratelimitadmin", "administrator-passphrase")
    assert admin is not None
    sessions = SessionStore(db)
    session_a = sessions.create(admin).token
    session_b = sessions.create(admin).token
    auth = AuthenticationService(accounts, sessions, SecurityAuditLog(db))

    for _ in range(4):
        assert _record_recovery_failure(auth, admin.user_id, session_a, "198.51.100.10") == 0
    assert _record_recovery_failure(auth, admin.user_id, session_b, "203.0.113.20") == 900

    allowed, retry = _recovery_attempt_allowed(auth, admin.user_id, session_a, "192.0.2.30")
    assert allowed is False
    assert retry > 0
