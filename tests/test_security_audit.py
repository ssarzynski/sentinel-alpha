import sqlite3

from sentinel_alpha.security_audit import SecurityAuditLog


def test_security_events_are_hash_chained(tmp_path):
    log = SecurityAuditLog(tmp_path / "audit.db")
    log.append("LOGIN_FAILURE", success=False, metadata={"reason": "invalid_credentials"})
    log.append("LOGIN_SUCCESS", success=True, actor_user_id=1)
    assert log.verify_integrity() is True
    events = log.recent()
    assert events[0].event_type == "LOGIN_SUCCESS"


def test_tampering_is_detected(tmp_path):
    db = tmp_path / "audit.db"
    log = SecurityAuditLog(db)
    log.append("ACCOUNT_APPROVED", success=True, actor_user_id=1, target_user_id=2)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE security_audit_log SET payload='{}' WHERE sequence=1"
        )
    assert log.verify_integrity() is False


def test_sensitive_values_need_not_be_logged(tmp_path):
    log = SecurityAuditLog(tmp_path / "audit.db")
    event = log.append(
        "PASSWORD_CHANGED", success=True, actor_user_id=1,
        metadata={"method": "authenticated_change"},
    )
    assert "password" not in str(event.metadata).lower()
    assert log.verify_integrity() is True


def test_recent_limit_is_bounded(tmp_path):
    log = SecurityAuditLog(tmp_path / "audit.db")
    try:
        log.recent(201)
        assert False
    except ValueError:
        pass
