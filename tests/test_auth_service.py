from sentinel_alpha.auth import AccountStatus, AccountStore
from sentinel_alpha.auth_service import AuthenticationService
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore


def service(tmp_path, max_failures=3):
    db = tmp_path / "auth.db"
    accounts = AccountStore(db)
    sessions = SessionStore(db)
    audit = SecurityAuditLog(db)
    return accounts, sessions, audit, AuthenticationService(
        accounts, sessions, audit, max_failures=max_failures, lock_minutes=15
    )


def test_unknown_and_wrong_password_both_fail_without_session(tmp_path):
    accounts, sessions, audit, auth = service(tmp_path)
    accounts.create_user("member", "member-test-passphrase", status=AccountStatus.ACTIVE)
    assert auth.login("unknown", "wrong-password-value").session is None
    assert auth.login("member", "wrong-password-value").session is None


def test_successful_login_is_audited(tmp_path):
    accounts, sessions, audit, auth = service(tmp_path)
    accounts.create_user("member", "member-test-passphrase", status=AccountStatus.ACTIVE)
    result = auth.login("member", "member-test-passphrase", source="127.0.0.1")
    assert result.session is not None
    assert audit.recent(1)[0].event_type == "LOGIN_SUCCESS"
    assert audit.verify_integrity() is True


def test_repeated_failures_temporarily_block_account(tmp_path):
    accounts, sessions, audit, auth = service(tmp_path, max_failures=3)
    accounts.create_user("member", "member-test-passphrase", status=AccountStatus.ACTIVE)
    for _ in range(3):
        assert auth.login("member", "wrong-password-value").session is None
    blocked = auth.login("member", "member-test-passphrase")
    assert blocked.session is None
    assert blocked.retry_after_seconds > 0


def test_source_is_hashed_before_audit_storage(tmp_path):
    accounts, sessions, audit, auth = service(tmp_path)
    auth.login("unknown", "wrong-password-value", source="203.0.113.99")
    event = audit.recent(1)[0]
    assert event.metadata is not None
    assert event.metadata["source_fingerprint"] != "203.0.113.99"
