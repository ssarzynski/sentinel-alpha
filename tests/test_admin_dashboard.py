import pyotp
from fastapi.testclient import TestClient
from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog

def setup_client(monkeypatch, tmp_path):
    db = tmp_path / "dashboard.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user("administrator", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE)
    accounts.create_user("pending", "pending-test-passphrase")
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    mfa = AdminMfaStore(db, SecurityAuditLog(db))
    enrollment = mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin, pyotp.TOTP(enrollment.secret).now())
    client = TestClient(app, base_url="https://testserver")
    assert client.post("/v1/auth/login", json={"username":"administrator","password":"administrator-passphrase"}).status_code == 200
    csrf = client.cookies.get(CSRF_COOKIE)
    assert client.post("/v1/auth/mfa/verify", json={"code":pyotp.TOTP(enrollment.secret).now()}, headers={"X-CSRF-Token":csrf}).status_code == 200
    return client

def test_dashboard_summary(monkeypatch, tmp_path):
    data = setup_client(monkeypatch, tmp_path).get("/v1/admin/dashboard").json()
    assert data["users_total"] == 2
    assert data["pending_accounts"] == 1
    assert data["active_users"] == 1
    assert data["audit_integrity"] is True

def test_security_events(monkeypatch, tmp_path):
    response = setup_client(monkeypatch, tmp_path).get("/v1/admin/security-events?limit=10")
    assert response.status_code == 200
    assert any(event["event_type"] == "MFA_CHALLENGE" for event in response.json())
