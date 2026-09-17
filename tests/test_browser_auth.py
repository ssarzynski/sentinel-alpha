from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.auth import AccountStatus, AccountStore


def test_login_sets_hardened_host_cookies(monkeypatch, tmp_path):
    db = tmp_path / "browser.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    AccountStore(db).create_user(
        "member", "member-test-passphrase", status=AccountStatus.ACTIVE
    )
    client = TestClient(app, base_url="https://testserver")
    response = client.post(
        "/v1/auth/login",
        json={"username": "member", "password": "member-test-passphrase"},
    )
    assert response.status_code == 200
    headers = response.headers.get_list("set-cookie")
    session = next(value for value in headers if "__Host-sentinel_session=" in value)
    csrf = next(value for value in headers if "__Host-sentinel_csrf=" in value)
    assert "HttpOnly" in session and "Secure" in session and "SameSite=strict" in session
    assert "Secure" in csrf and "SameSite=strict" in csrf


def test_logout_requires_matching_csrf(monkeypatch, tmp_path):
    db = tmp_path / "browser.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(db))
    AccountStore(db).create_user(
        "member", "member-test-passphrase", status=AccountStatus.ACTIVE
    )
    client = TestClient(app, base_url="https://testserver")
    login = client.post(
        "/v1/auth/login",
        json={"username": "member", "password": "member-test-passphrase"},
    )
    assert login.status_code == 200
    assert client.post("/v1/auth/logout").status_code == 403
    csrf = client.cookies.get("__Host-sentinel_csrf")
    assert csrf
    assert client.post("/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200


def test_login_failure_is_generic(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "browser.db"))
    client = TestClient(app, base_url="https://testserver")
    response = client.post(
        "/v1/auth/login", json={"username": "unknown", "password": "wrong-password-value"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."
