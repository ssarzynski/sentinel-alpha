from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_frontend_explains_evidence_and_independence():
    response=TestClient(app,base_url="https://testserver").get("/")
    assert response.status_code==200
    assert "Evidence &amp; provenance" in response.text or "Evidence & provenance" in response.text
    assert "which sources count independently" in response.text
