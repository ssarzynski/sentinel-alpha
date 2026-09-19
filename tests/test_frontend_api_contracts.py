from pathlib import Path

from fastapi.testclient import TestClient

from sentinel_alpha.api import app

client = TestClient(app)
STATIC = Path(__file__).parents[1] / "sentinel_alpha" / "static"


def test_dashboard_summary_contract_matches_frontend_fields():
    body = client.get("/v1/dashboard/summary").json()
    assert {"evaluation_count","strong_alert_count","blocked_count","paper_decision_count","audit_chain_valid","automatic_trading","human_approval_required"} <= body.keys()


def test_paper_decision_contract_matches_frontend_fields():
    response = client.get("/v1/paper-decisions")
    assert response.status_code == 200
    for item in response.json():
        assert {"paper_id","evaluation_id","asset","created_at","approved_by_human","hypothetical_action","notes"} <= item.keys()


def test_frontend_recovery_code_length_matches_backend_security_contract():
    html = (STATIC / "index.html").read_text()
    assert 'pattern="[0-9a-fA-F]{32}"' in html
    assert 'minlength="32"' in html
    assert 'maxlength="32"' in html


def test_frontend_evidence_renderer_uses_stored_evidence_shape():
    js = (STATIC / "app.js").read_text()
    assert 'ev.source||"Source"' in js
    assert 'ev.statement||"Evidence record"' in js
    assert 'ev.observed_at||"Time unavailable"' in js
