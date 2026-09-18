from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.browser_auth import CSRF_COOKIE, SESSION_COOKIE
from sentinel_alpha.sessions import SessionStore


def test_admin_routes_reject_unauthenticated_request(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "api.db"))
    response = TestClient(app, base_url="https://testserver").get("/v1/admin/users")
    assert response.status_code == 401


def test_normal_user_cookie_cannot_call_admin_api(monkeypatch, tmp_path):
    db = tmp_path / "api.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user("member", "member-test-passphrase", status=AccountStatus.ACTIVE)
    account = accounts.authenticate("member", "member-test-passphrase")
    assert account is not None
    token = SessionStore(db).create(account).token
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    response = client.get("/v1/admin/users")
    assert response.status_code == 403


def test_admin_mutation_requires_csrf(monkeypatch, tmp_path):
    db = tmp_path / "api.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    token = SessionStore(db).create(admin).token
    user_id = accounts.create_user("pending", "pending-test-passphrase")
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    assert client.post(f"/v1/admin/users/{user_id}/approve").status_code == 403


def test_admin_can_approve_with_cookie_and_csrf(monkeypatch, tmp_path):
    db = tmp_path / "api.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    token = SessionStore(db).create(admin).token
    user_id = accounts.create_user("pending", "pending-test-passphrase")
    client = TestClient(app, base_url="https://testserver")
    client.cookies.set(SESSION_COOKIE, token)
    client.cookies.set(CSRF_COOKIE, "csrf-test-value")
    response = client.post(
        f"/v1/admin/users/{user_id}/approve",
        headers={"X-CSRF-Token": "csrf-test-value"},
    )
    assert response.status_code == 200
    assert accounts.authenticate("pending", "pending-test-passphrase") is not None


def test_bearer_token_no_longer_authorizes_admin(monkeypatch, tmp_path):
    db = tmp_path / "api.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    token = SessionStore(db).create(admin).token
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/v1/admin/users", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
