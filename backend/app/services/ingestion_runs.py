from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import IngestionRun


def start_ingestion_run(
    db: Session, *, source: str, started_at: datetime, config: dict, metadata: dict | None = None
) -> IngestionRun:
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")
    if not source.strip():
        raise ValueError("source is required")
    row = IngestionRun(
        run_key=str(uuid4()), source=source.strip(), status="running",
        started_at=started_at, finished_at=None,
        checked=0, discovered=0, new_records=0, skipped_existing=0, evidence_rows=0,
        failures_json=[], config_json=dict(config), metadata_json=dict(metadata or {}),
    )
    db.add(row); db.flush(); return row


def finish_ingestion_run(db: Session, *, row: IngestionRun, finished_at: datetime, summary) -> IngestionRun:
    if finished_at.tzinfo is None:
        raise ValueError("finished_at must be timezone-aware")
    if finished_at < row.started_at:
        raise ValueError("finished_at cannot precede started_at")
    row.finished_at = finished_at
    row.checked = summary.checked
    row.discovered = summary.discovered
    row.new_records = summary.new_filings
    row.skipped_existing = summary.skipped_existing
    row.evidence_rows = summary.evidence_rows
    row.failures_json = list(summary.failures)
    row.status = "completed_with_errors" if summary.failures else "completed"
    db.flush(); return row


def fail_ingestion_run(db: Session, *, row: IngestionRun, finished_at: datetime, error: Exception) -> IngestionRun:
    if finished_at.tzinfo is None:
        raise ValueError("finished_at must be timezone-aware")
    row.finished_at = finished_at
    row.status = "failed"
    row.failures_json = [{"error": str(error), "type": type(error).__name__}]
    db.flush(); return row
