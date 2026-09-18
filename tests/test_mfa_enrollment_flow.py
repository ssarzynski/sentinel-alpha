import pyotp
from fastapi.testclient import TestClient
from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE

def test_admin_can_follow_guided_mfa_setup(monkeypatch,tmp_path):
    db=tmp_path/"enroll.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("administrator","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    client=TestClient(app,base_url="https://testserver")
    assert client.post("/v1/auth/login",json={"username":"administrator","password":"administrator-passphrase"}).status_code==200
    csrf=client.cookies.get(CSRF_COOKIE)
    enroll=client.post("/v1/auth/mfa/enroll",headers={"X-CSRF-Token":csrf})
    assert enroll.status_code==200
    data=enroll.json()
    assert len(data["instructions"])==3
    code=pyotp.TOTP(data["secret"]).now()
    confirm=client.post("/v1/auth/mfa/confirm",json={"code":code},headers={"X-CSRF-Token":csrf})
    assert confirm.status_code==200
    assert confirm.json()["next_step"]=="dashboard"
    assert client.get("/v1/admin/dashboard").status_code==200

def test_mfa_setup_rejects_normal_user(monkeypatch,tmp_path):
    db=tmp_path/"enroll.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("member","member-test-passphrase",status=AccountStatus.ACTIVE)
    client=TestClient(app,base_url="https://testserver")
    assert client.post("/v1/auth/login",json={"username":"member","password":"member-test-passphrase"}).status_code==200
    csrf=client.cookies.get(CSRF_COOKIE)
    assert client.post("/v1/auth/mfa/enroll",headers={"X-CSRF-Token":csrf}).status_code==403
