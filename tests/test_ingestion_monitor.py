from datetime import datetime, timedelta, timezone

from app.models import IngestionRun
from app.services.ingestion_monitor import ingestion_health


class FakeSession:
    def __init__(self, row=None): self.row = row
    def scalar(self, _query): return self.row


def run(status="completed", minutes_ago=5):
    now = datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc)
    started = now - timedelta(minutes=minutes_ago + 1)
    finished = now - timedelta(minutes=minutes_ago)
    return now, IngestionRun(run_key="run-1", source="SEC_FORM4", status=status, started_at=started,
        finished_at=finished, checked=1, discovered=0, new_records=0, skipped_existing=0,
        evidence_rows=0, failures_json=[] if status == "completed" else [{"error": "x"}], config_json={}, metadata_json={})


def test_recent_completed_run_is_healthy():
    now, row = run()
    result = ingestion_health(FakeSession(row), source="SEC_FORM4", now=now, stale_after_minutes=60)
    assert result["healthy"] is True and result["status"] == "completed"


def test_recent_error_run_is_not_healthy():
    now, row = run(status="completed_with_errors")
    result = ingestion_health(FakeSession(row), source="SEC_FORM4", now=now, stale_after_minutes=60)
    assert result["healthy"] is False and result["status"] == "completed_with_errors"


def test_old_run_is_reported_stale():
    now, row = run(minutes_ago=120)
    result = ingestion_health(FakeSession(row), source="SEC_FORM4", now=now, stale_after_minutes=60)
    assert result["healthy"] is False and result["status"] == "stale" and result["stale"] is True


def test_never_run_is_explicit():
    now = datetime.now(timezone.utc)
    result = ingestion_health(FakeSession(), source="SEC_FORM4", now=now)
    assert result == {"source": "SEC_FORM4", "status": "never_run", "healthy": False, "latest_run": None}
