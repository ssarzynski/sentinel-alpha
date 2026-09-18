from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_frontend_contains_guided_secure_login():
    response=TestClient(app,base_url="https://testserver").get("/")
    assert response.status_code==200
    assert "Administrator sign in" in response.text
    assert 'autocomplete="current-password"' in response.text
    assert 'autocomplete="one-time-code"' in response.text
    assert "guide you to the next step" in response.text
