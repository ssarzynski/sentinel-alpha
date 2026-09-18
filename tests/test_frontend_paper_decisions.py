from fastapi.testclient import TestClient
from sentinel_alpha.api import app

def test_frontend_explains_paper_decisions_are_non_executing():
    response=TestClient(app,base_url="https://testserver").get("/")
    assert response.status_code==200
    assert "Paper decisions" in response.text
    assert "Nothing here sends an order" in response.text
