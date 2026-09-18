from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyotp
from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE, SESSION_COOKIE, _csrf_for_session
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore


def test_expired_admin_password_cannot_reach_admin_api(monkeypatch, tmp_path: Path):
    db = tmp_path / "state.db"; monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    uid = accounts.create_user("expiredadmin", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE)
    with accounts._connect() as c:
        c.execute("UPDATE users SET password_expires_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(days=1)).isoformat(), uid))
    admin = accounts.authenticate("expiredadmin", "administrator-passphrase"); assert admin
    token = SessionStore(db).create(admin).token
    client = TestClient(app, base_url="https://testserver"); client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/v1/admin/users").status_code in {401, 403}


def test_forced_change_admin_cannot_reach_admin_api(monkeypatch, tmp_path: Path):
    db = tmp_path / "state.db"; monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user("forcedadmin", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE, must_change_password=True)
    admin = accounts.authenticate("forcedadmin", "administrator-passphrase"); assert admin
    token = SessionStore(db).create(admin).token
    client = TestClient(app, base_url="https://testserver"); client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/v1/admin/users").status_code in {401,403}


def test_admin_cannot_read_nonexistent_users_sessions(monkeypatch, tmp_path: Path):
    db = tmp_path / "state.db"; monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user("idoradmin", "administrator-passphrase", role=Role.ADMIN, status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("idoradmin","administrator-passphrase"); assert admin
    sessions=SessionStore(db); token=sessions.create(admin).token
    mfa=AdminMfaStore(db, SecurityAuditLog(db)); e=mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin, pyotp.TOTP(e.secret).now()); sessions.mark_mfa_verified(token, admin.user_id)
    client=TestClient(app,base_url="https://testserver"); client.cookies.set(SESSION_COOKIE,token)
    assert client.get("/v1/admin/users/999999/sessions").status_code == 404


def test_recovery_code_is_single_use(tmp_path: Path):
    db=tmp_path/"state.db"; accounts=AccountStore(db)
    accounts.create_user("recoveryadmin","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("recoveryadmin","administrator-passphrase"); assert admin
    mfa=AdminMfaStore(db,SecurityAuditLog(db)); e=mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin,pyotp.TOTP(e.secret).now())
    code=mfa.generate_recovery_codes(admin,count=1)[0]
    assert mfa.verify_recovery_code(admin,code) is True
    assert mfa.verify_recovery_code(admin,code) is False


def test_enable_and_unlock_reject_wrong_source_states(monkeypatch,tmp_path:Path):
    db=tmp_path/"state.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("stateadmin","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("stateadmin","administrator-passphrase"); assert admin
    sessions=SessionStore(db); token=sessions.create(admin).token
    mfa=AdminMfaStore(db,SecurityAuditLog(db)); e=mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin,pyotp.TOTP(e.secret).now()); sessions.mark_mfa_verified(token,admin.user_id)
    target=accounts.create_user("activeuser","target-test-passphrase",status=AccountStatus.ACTIVE)
    client=TestClient(app,base_url="https://testserver"); client.cookies.set(SESSION_COOKIE,token)
    csrf=_csrf_for_session(token); client.cookies.set(CSRF_COOKIE,csrf); h={"X-CSRF-Token":csrf}
    assert client.post(f"/v1/admin/users/{target}/enable",headers=h).status_code == 409
    assert client.post(f"/v1/admin/users/{target}/unlock",headers=h).status_code == 409
