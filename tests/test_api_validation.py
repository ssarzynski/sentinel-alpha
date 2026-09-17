from datetime import datetime, timezone

from fastapi.testclient import TestClient

from sentinel_alpha.api import app

client = TestClient(app)


def evidence(provider="SEC", asset="NVDA"):
    return {
        "provider": provider,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "asset": asset,
            "metric": "signal",
            "value": True,
            "statement": "test evidence",
        },
    }


def request_body(provider="SEC", evidence_asset="NVDA"):
    return {
        "asset": "NVDA",
        "status": "confirmed",
        "evidence": [evidence(provider, evidence_asset)],
        "proposal": {"stop_loss_defined": True},
    }


def test_unknown_provider_returns_422_not_500():
    response = client.post("/v1/evaluate", json=request_body(provider="UNKNOWN"))
    assert response.status_code == 422


def test_evidence_asset_must_match_requested_asset():
    response = client.post("/v1/evaluate", json=request_body(evidence_asset="BTC"))
    assert response.status_code == 422
    assert response.json()["detail"] == "evidence asset must match request asset"


def test_rules_endpoint_publishes_non_negotiable_safety_constraints():
    response = client.get("/v1/rules")
    assert response.status_code == 200
    rules = response.json()
    assert rules["minimum_independent_confirmations"] == 2
    assert rules["maximum_new_entries_per_week"] == 2
    assert rules["options_allowed"] is False
    assert rules["leverage_allowed"] is False
    assert rules["human_approval_required"] is True
    assert rules["automatic_trading"] is False
