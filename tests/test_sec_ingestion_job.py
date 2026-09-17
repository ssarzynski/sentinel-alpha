import json
from datetime import datetime, timedelta, timezone

import pytest

from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.services.sec_ingestion_job import execute_sec_form4_job


class FakeSession:
    def __init__(self): self.added = []
    def scalar(self, _query): return None
    def add(self, row): self.added.append(row)
    def flush(self): return None


def empty_submissions(cik="1045810"):
    return json.dumps({"cik": cik, "name": "Example", "filings": {"recent": {
        "accessionNumber": [], "filingDate": [], "reportDate": [], "form": [], "primaryDocument": []
    }}})


def test_job_creates_and_completes_persistent_run():
    db = FakeSession(); start = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)
    row = execute_sec_form4_job(
        db, items=[SecWatchItem("1045810", "NVDA")],
        fetch_text=lambda _: empty_submissions(), started_at=start,
        finished_at=lambda: start + timedelta(seconds=2), metadata={"worker_version": "m6.7"},
    )
    assert row.status == "completed"
    assert row.checked == 1
    assert row.discovered == 0
    assert row.config_json == {"watchlist_size": 1}
    assert row.metadata_json["worker_version"] == "m6.7"
    assert db.added[0] is row


def test_company_level_failure_completes_with_errors():
    db = FakeSession(); start = datetime.now(timezone.utc)
    row = execute_sec_form4_job(
        db, items=[SecWatchItem("1", "BAD")],
        fetch_text=lambda _: (_ for _ in ()).throw(RuntimeError("SEC unavailable")),
        started_at=start, finished_at=lambda: start + timedelta(seconds=1),
    )
    assert row.status == "completed_with_errors"
    assert row.checked == 1
    assert row.failures_json[0]["ticker"] == "BAD"


def test_fatal_job_failure_marks_run_failed_then_reraises(monkeypatch):
    db = FakeSession(); start = datetime.now(timezone.utc)
    def fatal(*_args, **_kwargs): raise RuntimeError("worker crashed")
    monkeypatch.setattr("app.services.sec_ingestion_job.run_form4_watchlist", fatal)
    with pytest.raises(RuntimeError, match="worker crashed"):
        execute_sec_form4_job(
            db, items=[], fetch_text=lambda _: "", started_at=start,
            finished_at=lambda: start + timedelta(seconds=1),
        )
    row = db.added[0]
    assert row.status == "failed"
    assert row.failures_json[0]["type"] == "RuntimeError"
