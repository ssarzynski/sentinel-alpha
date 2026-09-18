import pyotp
from fastapi.testclient import TestClient
from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog

def admin_client(monkeypatch,tmp_path):
    db=tmp_path/"policy.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("administrator","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("administrator","administrator-passphrase")
    mfa=AdminMfaStore(db,SecurityAuditLog(db)); enrollment=mfa.begin_enrollment(admin)
    assert mfa.confirm_enrollment(admin,pyotp.TOTP(enrollment.secret).now())
    client=TestClient(app,base_url="https://testserver")
    assert client.post("/v1/auth/login",json={"username":"administrator","password":"administrator-passphrase"}).status_code==200
    csrf=client.cookies.get(CSRF_COOKIE)
    assert client.post("/v1/auth/mfa/verify",json={"code":pyotp.TOTP(enrollment.secret).now()},headers={"X-CSRF-Token":csrf}).status_code==200
    return client,csrf

def test_policy_is_helpful_and_explicit(monkeypatch,tmp_path):
    client,csrf=admin_client(monkeypatch,tmp_path)
    data=client.get("/v1/admin/password-policy").json()
    assert data["expiration_days"]==90
    assert data["allowed_expiration_days"]==[30,60,90]

def test_admin_can_change_policy(monkeypatch,tmp_path):
    client,csrf=admin_client(monkeypatch,tmp_path)
    response=client.put("/v1/admin/password-policy",json={"expiration_days":60},headers={"X-CSRF-Token":csrf})
    assert response.status_code==200
    assert response.json()["applies_to_new_password_changes"] is True

def test_policy_rejects_unsupported_value(monkeypatch,tmp_path):
    client,csrf=admin_client(monkeypatch,tmp_path)
    response=client.put("/v1/admin/password-policy",json={"expiration_days":45},headers={"X-CSRF-Token":csrf})
    assert response.status_code==422
