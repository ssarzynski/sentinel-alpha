from datetime import datetime, timedelta, timezone

import pytest

from app.ingestion.sec_watchlist_worker import SecWatchRun
from app.services.ingestion_runs import fail_ingestion_run, finish_ingestion_run, start_ingestion_run


class FakeSession:
    def __init__(self): self.added = []
    def add(self, row): self.added.append(row)
    def flush(self): return None


def test_successful_run_records_operational_counts():
    db = FakeSession(); start = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)
    row = start_ingestion_run(db, source="SEC_FORM4", started_at=start, config={"watchlist_size": 2})
    summary = SecWatchRun(checked=2, discovered=4, new_filings=2, evidence_rows=3, skipped_existing=2)
    finish_ingestion_run(db, row=row, finished_at=start + timedelta(seconds=5), summary=summary)
    assert row.status == "completed"
    assert row.checked == 2 and row.discovered == 4 and row.new_records == 2
    assert row.evidence_rows == 3 and row.skipped_existing == 2
    assert row.failures_json == []


def test_partial_failures_are_visible_not_hidden():
    db = FakeSession(); start = datetime.now(timezone.utc)
    row = start_ingestion_run(db, source="SEC_FORM4", started_at=start, config={})
    summary = SecWatchRun(checked=2, failures=[{"ticker": "BAD", "error": "timeout"}])
    finish_ingestion_run(db, row=row, finished_at=start + timedelta(seconds=1), summary=summary)
    assert row.status == "completed_with_errors"
    assert row.failures_json[0]["ticker"] == "BAD"


def test_fatal_run_failure_is_persisted():
    db = FakeSession(); start = datetime.now(timezone.utc)
    row = start_ingestion_run(db, source="SEC_FORM4", started_at=start, config={})
    fail_ingestion_run(db, row=row, finished_at=start + timedelta(seconds=1), error=RuntimeError("database unavailable"))
    assert row.status == "failed"
    assert row.failures_json == [{"error": "database unavailable", "type": "RuntimeError"}]


def test_naive_timestamps_and_negative_duration_fail_closed():
    db = FakeSession()
    with pytest.raises(ValueError, match="timezone-aware"):
        start_ingestion_run(db, source="SEC", started_at=datetime.now(), config={})
    start = datetime.now(timezone.utc)
    row = start_ingestion_run(db, source="SEC", started_at=start, config={})
    with pytest.raises(ValueError, match="cannot precede"):
        finish_ingestion_run(db, row=row, finished_at=start - timedelta(seconds=1), summary=SecWatchRun())
