import json
import logging
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


def test_job_creates_and_completes_persistent_run(caplog):
    caplog.set_level(logging.INFO, "app.ingestion.sec_watchlist_worker")
    db = FakeSession(); start = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)
    row = execute_sec_form4_job(db, items=[SecWatchItem("1045810", "NVDA")], fetch_text=lambda _: empty_submissions(), started_at=start, finished_at=lambda: start + timedelta(seconds=2), metadata={"worker_version": "m6.7"})
    assert row.status == "completed"
    assert row.checked == 1 and row.discovered == 0
    assert row.config_json == {"watchlist_size": 1}
    assert row.metadata_json["worker_version"] == "m6.7"
    assert db.added[0] is row
    text="\n".join(record.getMessage() for record in caplog.records)
    assert "event=watchlist_started" in text
    assert "event=company_discovered" in text
    assert "event=watchlist_completed" in text


def test_company_level_failure_is_durable_and_observable_without_stopping_next_company(caplog):
    caplog.set_level(logging.INFO, "app.ingestion.sec_watchlist_worker")
    db=FakeSession(); start=datetime.now(timezone.utc); calls=[]
    def fetch(url):
        calls.append(url)
        if "CIK0000000001" in url: raise RuntimeError("SEC unavailable")
        return empty_submissions("2")
    row=execute_sec_form4_job(db,items=[SecWatchItem("1","BAD"),SecWatchItem("2","GOOD")],fetch_text=fetch,started_at=start,finished_at=lambda:start+timedelta(seconds=1))
    assert row.status=="completed_with_errors"
    assert row.checked==2
    assert len(calls)==2
    failure=row.failures_json[0]
    assert failure["ticker"]=="BAD"
    assert failure["stage"]=="watchlist_company"
    assert failure["error_type"]=="RuntimeError"
    text="\n".join(record.getMessage() for record in caplog.records)
    assert "event=company_failed" in text
    assert "ticker=GOOD" in text
    assert "failures=1" in text


def test_fatal_job_failure_marks_run_failed_then_reraises(monkeypatch):
    db=FakeSession();start=datetime.now(timezone.utc)
    def fatal(*_args,**_kwargs): raise RuntimeError("worker crashed")
    monkeypatch.setattr("app.services.sec_ingestion_job.run_form4_watchlist",fatal)
    with pytest.raises(RuntimeError,match="worker crashed"):
        execute_sec_form4_job(db,items=[],fetch_text=lambda _:"",started_at=start,finished_at=lambda:start+timedelta(seconds=1))
    row=db.added[0]
    assert row.status=="failed"
    assert row.failures_json[0]["type"]=="RuntimeError"
