from fastapi.testclient import TestClient
from sentinel_alpha.api import app

client=TestClient(app,base_url="https://testserver")

def test_login_rejects_oversized_username_before_authentication():
    r=client.post("/v1/auth/login",json={"username":"u"*129,"password":"x"})
    assert r.status_code==422

def test_login_rejects_oversized_password_before_hash_work():
    r=client.post("/v1/auth/login",json={"username":"user","password":"x"*1025})
    assert r.status_code==422

def test_mfa_challenge_requires_exactly_six_digits():
    r=client.post("/v1/auth/mfa/verify",json={"code":"1234567"})
    assert r.status_code==422

def test_password_change_rejects_oversized_current_password():
    r=client.post("/v1/auth/password",json={"current_password":"x"*1025,"new_password":"long-enough-new-password"})
    assert r.status_code==422
