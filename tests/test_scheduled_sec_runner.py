import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.services.scheduled_sec_runner import run_scheduled_sec_form4


class FakeSession:
    def __init__(self): self.added = []
    def scalar(self, _query): return None
    def add(self, row): self.added.append(row)
    def flush(self): return None


def submissions():
    return json.dumps({"cik": "1045810", "name": "Example", "filings": {"recent": {
        "accessionNumber": [], "filingDate": [], "reportDate": [], "form": [], "primaryDocument": []
    }}})


def lock(acquired):
    @contextmanager
    def _lock(_db, _name):
        yield acquired
    return _lock


def test_busy_lock_records_skipped_overlap(monkeypatch):
    monkeypatch.setattr("app.services.scheduled_sec_runner.advisory_job_lock", lock(False))
    db = FakeSession(); start = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    result = run_scheduled_sec_form4(
        db, items=[SecWatchItem("1045810", "NVDA")], fetch_text=lambda _: submissions(),
        started_at=start, finished_at=lambda: start + timedelta(seconds=1), metadata={"trigger": "interval"},
    )
    assert result.executed is False
    assert result.reason == "overlap_lock_busy"
    assert result.run.status == "skipped_overlap"
    assert result.run.metadata_json["skip_reason"] == "overlap_lock_busy"


def test_owned_lock_executes_normal_job(monkeypatch):
    monkeypatch.setattr("app.services.scheduled_sec_runner.advisory_job_lock", lock(True))
    db = FakeSession(); start = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    result = run_scheduled_sec_form4(
        db, items=[SecWatchItem("1045810", "NVDA")], fetch_text=lambda _: submissions(),
        started_at=start, finished_at=lambda: start + timedelta(seconds=2), metadata={"trigger": "interval"},
    )
    assert result.executed is True
    assert result.reason == "executed"
    assert result.run.status == "completed"
    assert result.run.checked == 1
    assert result.run.metadata_json["scheduler_lock"] == "SEC_FORM4"
