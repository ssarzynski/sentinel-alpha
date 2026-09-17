from datetime import datetime, timezone

from fastapi.testclient import TestClient

from sentinel_alpha.api import app

client = TestClient(app)


def evidence(provider: str, asset: str = "NVDA") -> dict:
    return {
        "provider": provider,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "asset": asset,
            "metric": "signal",
            "value": True,
            "statement": f"confirmation from {provider}",
        },
    }


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sentinel-alpha"}


def test_evaluate_endpoint_returns_human_review_eligibility():
    response = client.post(
        "/v1/evaluate",
        json={
            "asset": "NVDA",
            "status": "confirmed",
            "evidence": [evidence("sec"), evidence("finviz")],
            "proposal": {"stop_loss_defined": True},
            "new_entries_this_week": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confirmations"] == 2
    assert body["strong_alert"] is True
    assert body["eligible_for_review"] is True
    assert body["requires_human_approval"] is True


def test_evaluate_endpoint_preserves_risk_blocks():
    response = client.post(
        "/v1/evaluate",
        json={
            "asset": "NVDA",
            "status": "confirmed",
            "evidence": [evidence("sec"), evidence("finviz")],
            "proposal": {"instrument_type": "options", "stop_loss_defined": True},
            "new_entries_this_week": 0,
        },
    )
    assert response.status_code == 200
    assert response.json()["blocked"] is True
    assert "options_prohibited" in response.json()["reasons"]


def test_request_validation_rejects_negative_entry_count():
    response = client.post(
        "/v1/evaluate",
        json={
            "asset": "NVDA",
            "status": "confirmed",
            "evidence": [evidence("sec")],
            "proposal": {"stop_loss_defined": True},
            "new_entries_this_week": -1,
        },
    )
    assert response.status_code == 422
