import sqlite3

from fastapi.testclient import TestClient

from sentinel_alpha.api import app
from sentinel_alpha.journal import EvaluationJournal

client = TestClient(app)


def test_audit_verify_reports_valid_empty_chain(tmp_path, monkeypatch):
    database = tmp_path / "audit.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(database))
    response = client.get("/v1/audit/verify")
    assert response.status_code == 200
    assert response.json() == {"valid": True, "status": "verified"}


def test_audit_verify_reports_tampering(tmp_path, monkeypatch):
    database = tmp_path / "audit.db"
    monkeypatch.setenv("SENTINEL_DB_PATH", str(database))
    journal = EvaluationJournal(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT INTO evaluations
            (evaluation_id, created_at, asset, payload, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("tampered", "2026-09-17T00:00:00+00:00", "NVDA", "{}", "0" * 64, "bad-hash"),
        )
    response = client.get("/v1/audit/verify")
    assert response.status_code == 200
    assert response.json() == {"valid": False, "status": "integrity_failure"}
