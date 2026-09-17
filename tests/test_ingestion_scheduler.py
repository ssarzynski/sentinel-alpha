from datetime import datetime, timedelta, timezone

from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.models import IngestionRun
from app.services.ingestion_scheduler import run_scheduled_sec_form4_cycle, sec_form4_schedule_decision


class FakeSession:
    def __init__(self, latest=None): self.latest = latest; self.added = []
    def scalar(self, _query): return self.latest
    def add(self, row): self.added.append(row)
    def flush(self): return None


def run(status, started_at, finished_at=None):
    return IngestionRun(
        run_key="r1", source="SEC_FORM4", status=status, started_at=started_at,
        finished_at=finished_at, checked=0, discovered=0, new_records=0,
        skipped_existing=0, evidence_rows=0, failures_json=[], config_json={}, metadata_json={},
    )


def empty_submissions():
    return '{"cik":"1045810","name":"Example","filings":{"recent":{"accessionNumber":[],"filingDate":[],"reportDate":[],"form":[],"primaryDocument":[]}}}'


def test_never_run_is_due_immediately():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    decision = sec_form4_schedule_decision(FakeSession(), now=now)
    assert decision.due is True
    assert decision.reason == "never_run"


def test_recent_completed_run_waits_for_interval():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    latest = run("completed", now - timedelta(minutes=5), now - timedelta(minutes=4))
    decision = sec_form4_schedule_decision(FakeSession(latest), now=now, interval_minutes=15)
    assert decision.due is False
    assert decision.reason == "waiting_for_interval"


def test_active_running_job_blocks_overlap():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    latest = run("running", now - timedelta(minutes=10))
    decision = sec_form4_schedule_decision(FakeSession(latest), now=now, max_running_minutes=30)
    assert decision.due is False
    assert decision.reason == "run_in_progress"


def test_stale_running_job_allows_recovery_cycle():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    latest = run("running", now - timedelta(minutes=45))
    decision = sec_form4_schedule_decision(FakeSession(latest), now=now, max_running_minutes=30)
    assert decision.due is True
    assert decision.reason == "stale_running_run"


def test_due_cycle_executes_observable_ingestion_job():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    db = FakeSession()
    decision, row = run_scheduled_sec_form4_cycle(
        db,
        items=[SecWatchItem("1045810", "NVDA")],
        fetch_text=lambda _url: empty_submissions(),
        now=now,
        finished_at=lambda: now + timedelta(seconds=2),
        interval_minutes=15,
    )
    assert decision.due is True
    assert row is not None
    assert row.status == "completed"
    assert row.metadata_json["scheduler"] == "sec_form4"
    assert row.metadata_json["interval_minutes"] == 15


def test_not_due_cycle_does_not_execute_worker():
    now = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)
    latest = run("completed", now - timedelta(minutes=2), now - timedelta(minutes=1))
    db = FakeSession(latest)
    called = False
    def fetch(_url):
        nonlocal called; called = True; return empty_submissions()
    decision, row = run_scheduled_sec_form4_cycle(
        db, items=[SecWatchItem("1045810", "NVDA")], fetch_text=fetch,
        now=now, finished_at=lambda: now + timedelta(seconds=1), interval_minutes=15,
    )
    assert decision.due is False
    assert row is None
    assert called is False
