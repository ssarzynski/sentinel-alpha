from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_dashboard_shell_is_served():
    response=TestClient(app,base_url="https://testserver").get("/")
    assert response.status_code==200
    assert "Sentinel Alpha" in response.text
    assert "Human approval required" in response.text
    assert "Auto-trading off" in response.text

def test_frontend_assets_are_served():
    client=TestClient(app,base_url="https://testserver")
    assert client.get("/ui/app.css").status_code==200
    assert client.get("/ui/app.js").status_code==200
