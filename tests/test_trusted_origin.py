import os
from fastapi.testclient import TestClient
from sentinel_alpha.api import app

client=TestClient(app,base_url="https://testserver")

def test_login_rejects_cross_origin_before_credentials():
    r=client.post("/v1/auth/login",headers={"Origin":"https://evil.example"},json={"username":"nobody","password":"wrong"})
    assert r.status_code==403
    assert r.json()["detail"]=="untrusted request origin"

def test_same_origin_login_reaches_authentication():
    r=client.post("/v1/auth/login",headers={"Origin":"https://testserver"},json={"username":"nobody","password":"wrong"})
    assert r.status_code in {401,429}
