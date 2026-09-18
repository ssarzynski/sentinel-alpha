from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from sentinel_alpha.browser_auth import security_client_ip


def _client():
    app = FastAPI()
    @app.get("/")
    def read(request: Request):
        return {"ip": security_client_ip(request)}
    return TestClient(app)


def test_forwarded_for_ignored_from_untrusted_peer(monkeypatch):
    monkeypatch.delenv("SENTINEL_TRUSTED_PROXIES", raising=False)
    response = _client().get("/", headers={"X-Forwarded-For": "203.0.113.50"})
    assert response.json()["ip"] == "testclient"


def test_forwarded_for_accepted_from_explicit_trusted_peer(monkeypatch):
    monkeypatch.setenv("SENTINEL_TRUSTED_PROXIES", "testclient")
    response = _client().get("/", headers={"X-Forwarded-For": "203.0.113.50, 10.0.0.2"})
    assert response.json()["ip"] == "203.0.113.50"


def test_invalid_forwarded_for_fails_closed_to_peer(monkeypatch):
    monkeypatch.setenv("SENTINEL_TRUSTED_PROXIES", "testclient")
    response = _client().get("/", headers={"X-Forwarded-For": "spoofed-client"})
    assert response.json()["ip"] == "testclient"
