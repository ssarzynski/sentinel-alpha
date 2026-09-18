from pathlib import Path
import pyotp
from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE, SESSION_COOKIE, _csrf_for_session
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore


def test_admin_status_audit_carries_validated_request_id(monkeypatch,tmp_path:Path):
    db=tmp_path/"trace.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("traceadmin","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("traceadmin","administrator-passphrase"); assert admin
    target=accounts.create_user("pendingtrace","target-passphrase",status=AccountStatus.PENDING_APPROVAL)
    sessions=SessionStore(db); token=sessions.create(admin).token
    audit=SecurityAuditLog(db); mfa=AdminMfaStore(db,audit); enrollment=mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin,pyotp.TOTP(enrollment.secret).now()); sessions.mark_mfa_verified(token,admin.user_id)
    csrf=_csrf_for_session(token)
    client=TestClient(app,base_url="https://testserver"); client.cookies.set(SESSION_COOKIE,token); client.cookies.set(CSRF_COOKIE,csrf)
    rid="incident-2026-09-18.001"
    r=client.post(f"/v1/admin/users/{target}/approve",headers={"X-CSRF-Token":csrf,"X-Request-ID":rid})
    assert r.status_code==200
    event=next(e for e in audit.recent() if e.event_type=="ACCOUNT_APPROVED")
    assert event.request_id==rid
