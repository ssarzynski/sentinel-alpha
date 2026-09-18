from pathlib import Path
import pyotp
from fastapi.testclient import TestClient
from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE, SESSION_COOKIE, _csrf_for_session
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog
from sentinel_alpha.sessions import SessionStore

def test_password_policy_audit_carries_request_id(monkeypatch,tmp_path:Path):
    db=tmp_path/"trace2.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    a=AccountStore(db); a.create_user("traceadmin2","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=a.authenticate("traceadmin2","administrator-passphrase"); assert admin
    s=SessionStore(db); token=s.create(admin).token; audit=SecurityAuditLog(db); m=AdminMfaStore(db,audit)
    e=m.begin_enrollment(admin); assert m.confirm_enrollment(admin,pyotp.TOTP(e.secret).now()); s.mark_mfa_verified(token,admin.user_id)
    csrf=_csrf_for_session(token); client=TestClient(app,base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE,token); client.cookies.set(CSRF_COOKIE,csrf)
    rid="policy-change-001"
    r=client.put("/v1/admin/password-policy",json={"expiration_days":60},headers={"X-CSRF-Token":csrf,"X-Request-ID":rid})
    assert r.status_code==200
    event=next(x for x in audit.recent() if x.event_type=="PASSWORD_POLICY_CHANGED")
    assert event.request_id==rid
