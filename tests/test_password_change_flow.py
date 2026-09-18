from fastapi.testclient import TestClient
from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE

def test_forced_password_change_rotates_session(monkeypatch,tmp_path):
    db=tmp_path/"password.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("administrator","old-administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE,must_change_password=True)
    client=TestClient(app,base_url="https://testserver")
    login=client.post("/v1/auth/login",json={"username":"administrator","password":"old-administrator-passphrase"})
    assert login.status_code==200
    assert login.json()["password_change_required"] is True
    csrf=client.cookies.get(CSRF_COOKIE)
    changed=client.post("/v1/auth/password",json={"current_password":"old-administrator-passphrase","new_password":"new-administrator-passphrase"},headers={"X-CSRF-Token":csrf})
    assert changed.status_code==200
    assert changed.json()["mfa_required"] is True
    assert accounts.authenticate("administrator","old-administrator-passphrase") is None
    assert accounts.authenticate("administrator","new-administrator-passphrase") is not None

def test_password_reuse_is_rejected(monkeypatch,tmp_path):
    db=tmp_path/"password.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("member","member-test-passphrase",status=AccountStatus.ACTIVE)
    client=TestClient(app,base_url="https://testserver")
    assert client.post("/v1/auth/login",json={"username":"member","password":"member-test-passphrase"}).status_code==200
    csrf=client.cookies.get(CSRF_COOKIE)
    response=client.post("/v1/auth/password",json={"current_password":"member-test-passphrase","new_password":"member-test-passphrase"},headers={"X-CSRF-Token":csrf})
    assert response.status_code==422


def test_recent_password_history_rejects_prior_password(monkeypatch,tmp_path):
    db=tmp_path/"password-history.db"; monkeypatch.setenv("SENTINEL_DB_PATH",str(db))
    accounts=AccountStore(db)
    accounts.create_user("history-member","history-original-passphrase",status=AccountStatus.ACTIVE)
    client=TestClient(app,base_url="https://testserver")
    assert client.post("/v1/auth/login",json={"username":"history-member","password":"history-original-passphrase"}).status_code==200
    csrf=client.cookies.get(CSRF_COOKIE)
    first=client.post("/v1/auth/password",json={"current_password":"history-original-passphrase","new_password":"history-second-passphrase"},headers={"X-CSRF-Token":csrf})
    assert first.status_code==200
    csrf=client.cookies.get(CSRF_COOKIE)
    reused=client.post("/v1/auth/password",json={"current_password":"history-second-passphrase","new_password":"history-original-passphrase"},headers={"X-CSRF-Token":csrf})
    assert reused.status_code==400
    assert reused.json()["detail"]=="password change failed"
    assert accounts.authenticate("history-member","history-second-passphrase") is not None
