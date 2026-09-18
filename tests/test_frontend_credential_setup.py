from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_frontend_guides_forced_password_and_mfa_setup():
    text=TestClient(app,base_url="https://testserver").get("/").text
    assert "Change required password" in text
    assert 'autocomplete="new-password"' in text
    assert "Set up administrator MFA" in text
    assert "temporary or expired password" in text
