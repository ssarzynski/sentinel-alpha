from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_frontend_explains_admin_security_boundary():
    response=TestClient(app,base_url="https://testserver").get("/")
    assert response.status_code==200
    assert "Account approvals and security controls" in response.text
    assert "administrator authentication and MFA" in response.text
