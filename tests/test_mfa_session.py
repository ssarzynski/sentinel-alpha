import pyotp
from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog


def test_admin_session_requires_completed_mfa(monkeypatch, tmp_path):
    db = tmp_path / "mfa-session.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    mfa = AdminMfaStore(db, SecurityAuditLog(db))
    enrollment = mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin, pyotp.TOTP(enrollment.secret).now())

    client = TestClient(app, base_url="https://testserver")
    login = client.post(
        "/v1/auth/login",
        json={"username": "administrator", "password": "administrator-passphrase"},
    )
    assert login.status_code == 200
    assert client.get("/v1/admin/users").status_code == 403

    csrf = client.cookies.get(CSRF_COOKIE)
    assert csrf
    challenge = client.post(
        "/v1/auth/mfa/verify",
        json={"code": pyotp.TOTP(enrollment.secret).now()},
        headers={"X-CSRF-Token": csrf},
    )
    assert challenge.status_code == 200
    assert client.get("/v1/admin/users").status_code == 200


def test_wrong_mfa_code_does_not_unlock_admin_session(monkeypatch, tmp_path):
    db = tmp_path / "mfa-session.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    mfa = AdminMfaStore(db, SecurityAuditLog(db))
    enrollment = mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin, pyotp.TOTP(enrollment.secret).now())

    client = TestClient(app, base_url="https://testserver")
    assert client.post(
        "/v1/auth/login",
        json={"username": "administrator", "password": "administrator-passphrase"},
    ).status_code == 200
    csrf = client.cookies.get(CSRF_COOKIE)
    response = client.post(
        "/v1/auth/mfa/verify", json={"code": "000000"}, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 401
    assert client.get("/v1/admin/users").status_code == 403
