from datetime import datetime, timezone

from fastapi.testclient import TestClient

from sentinel_alpha.api import app

client = TestClient(app)


def payload() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "asset": "NVDA",
        "status": "confirmed",
        "evidence": [
            {"provider": "sec", "observed_at": now, "role": "support", "rationale": "test classified filing", "payload": {"asset": "NVDA", "metric": "filing", "statement": "classified event"}},
            {"provider": "finviz", "observed_at": now, "role": "support", "rationale": "test classified screen", "payload": {"asset": "NVDA", "metric": "screen", "statement": "classified screen"}},
        ],
        "proposal": {"stop_loss_defined": True},
        "new_entries_this_week": 0,
    }


def test_evaluate_persists_and_can_be_retrieved(tmp_path, monkeypatch):
    database = tmp_path / "api.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(database))
    response = client.post("/v1/evaluate", json=payload())
    assert response.status_code == 200
    evaluation_id = response.json()["evaluation_id"]
    stored = client.get(f"/v1/evaluations/{evaluation_id}")
    assert stored.status_code == 200
    assert stored.json()["asset"] == "NVDA"
    assert stored.json()["result"]["decision"]["confirmation_count"] == 2


def test_recent_history_lists_persisted_evaluation(tmp_path, monkeypatch):
    database = tmp_path / "api.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(database))
    created = client.post("/v1/evaluate", json=payload()).json()
    response = client.get("/v1/evaluations?limit=10")
    assert response.status_code == 200
    assert any(row["evaluation_id"] == created["evaluation_id"] for row in response.json())


def test_unknown_evaluation_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DB_PATH", str(tmp_path / "api.db"))
    response = client.get("/v1/evaluations/not-found")
    assert response.status_code == 404


def test_history_limit_is_validated():
    response = client.get("/v1/evaluations?limit=201")
    assert response.status_code == 422
