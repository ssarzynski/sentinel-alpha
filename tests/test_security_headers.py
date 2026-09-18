from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_security_headers_are_present():
    response=TestClient(app,base_url="https://testserver").get("/health")
    assert response.status_code==200
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")
    assert response.headers["x-content-type-options"]=="nosniff"
    assert response.headers["referrer-policy"]=="no-referrer"
    assert response.headers["x-frame-options"]=="DENY"
