from fastapi.testclient import TestClient
from sentinel_alpha.api import app

client=TestClient(app,base_url="https://testserver")

def test_recovery_challenge_rejects_malformed_code_before_auth():
    response=client.post("/v1/auth/mfa/recovery/verify",json={"code":"not-a-recovery-code"})
    assert response.status_code==422

def test_recovery_generation_requires_authentication_and_csrf():
    response=client.post("/v1/auth/mfa/recovery/generate")
    assert response.status_code==403
