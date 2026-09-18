"""Launch-oriented security acceptance tests for the HTTP boundary."""

from pathlib import Path

from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.security_audit import SecurityAuditLog


def test_security_headers_and_request_id_are_present(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "sentinel.db"))
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_malformed_request_id_is_not_reflected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "sentinel.db"))
    bad = "bad request id\r\nInjected: yes"
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": bad})
    assert response.status_code == 200
    assert response.headers["x-request-id"] != bad
    assert len(response.headers["x-request-id"]) <= 128


def test_admin_endpoint_denies_unauthenticated_request(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "sentinel.db"))
    with TestClient(app) as client:
        response = client.get("/v1/admin/users")
    assert response.status_code == 401


def test_admin_mutation_denies_unauthenticated_request(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "sentinel.db"))
    with TestClient(app) as client:
        response = client.post("/v1/admin/users/1/disable")
    assert response.status_code == 401


def test_non_admin_account_cannot_satisfy_admin_authorization(tmp_path: Path) -> None:
    db = tmp_path / "sentinel.db"
    accounts = AccountStore(db)
    user_id = accounts.create_user(
        "ordinaryuser", "correct-horse-battery-staple",
        role=Role.USER, status=AccountStatus.ACTIVE,
    )
    account = accounts.authenticate("ordinaryuser", "correct-horse-battery-staple")
    assert account is not None and account.user_id == user_id
    from sentinel_alpha.auth import require_admin
    try:
        require_admin(account)
    except PermissionError:
        pass
    else:
        raise AssertionError("ordinary USER passed administrator authorization")


def test_security_audit_chain_detects_payload_tampering(tmp_path: Path) -> None:
    db = tmp_path / "sentinel.db"
    accounts = AccountStore(db)
    audit = SecurityAuditLog(db)
    audit.append("SECURITY_ACCEPTANCE", success=True)
    assert audit.verify_integrity() is True
    with accounts._connect() as connection:
        connection.execute(
            "UPDATE security_audit_log SET payload=? WHERE sequence=1",
            ('{"tampered":true}',),
        )
    assert audit.verify_integrity() is False
