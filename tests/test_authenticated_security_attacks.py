from pathlib import Path

import pyotp
from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE, SESSION_COOKIE, _csrf_for_session
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore


def _admin(db: Path):
    accounts = AccountStore(db)
    accounts.create_user("adminattack", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE)
    admin = accounts.authenticate("adminattack", "administrator-passphrase")
    assert admin is not None
    sessions = SessionStore(db)
    token = sessions.create(admin).token
    mfa = AdminMfaStore(db, SecurityAuditLog(db))
    enrollment = mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin, pyotp.TOTP(enrollment.secret).now())
    sessions.mark_mfa_verified(token, admin.user_id)
    return accounts, admin, sessions, token


def test_cross_session_csrf_token_is_rejected(monkeypatch, tmp_path: Path):
    db = tmp_path / "attack.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts, admin, sessions, token_a = _admin(db)
    token_b = sessions.create(admin).token
    sessions.mark_mfa_verified(token_b, admin.user_id)
    target = accounts.create_user("pendingattack", "pending-test-passphrase")
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token_b)
    csrf_a = _csrf_for_session(token_a)
    client.cookies.set(CSRF_COOKIE, csrf_a)
    response = client.post(f"/v1/admin/users/{target}/approve", headers={"X-CSRF-Token": csrf_a})
    assert response.status_code == 403


def test_admin_session_without_mfa_cannot_read_admin_api(monkeypatch, tmp_path: Path):
    db = tmp_path / "attack.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user("nomfaadmin", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE)
    admin = accounts.authenticate("nomfaadmin", "administrator-passphrase")
    assert admin is not None
    token = SessionStore(db).create(admin).token
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/v1/admin/users").status_code == 403


def test_revoked_session_cannot_reenter_admin_api(monkeypatch, tmp_path: Path):
    db = tmp_path / "attack.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts, admin, sessions, token = _admin(db)
    sessions.revoke_all(admin.user_id)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/v1/admin/users").status_code == 401


def test_approve_endpoint_cannot_activate_disabled_account(monkeypatch, tmp_path: Path):
    db = tmp_path / "attack.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts, admin, sessions, token = _admin(db)
    target = accounts.create_user("disabledtarget", "target-test-passphrase", status=AccountStatus.DISABLED)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    csrf = _csrf_for_session(token)
    client.cookies.set(CSRF_COOKIE, csrf)
    response = client.post(f"/v1/admin/users/{target}/approve", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 409


def test_admin_cannot_disable_self(monkeypatch, tmp_path: Path):
    db = tmp_path / "attack.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts, admin, sessions, token = _admin(db)
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    csrf = _csrf_for_session(token)
    client.cookies.set(CSRF_COOKIE, csrf)
    response = client.post(f"/v1/admin/users/{admin.user_id}/disable", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 409
