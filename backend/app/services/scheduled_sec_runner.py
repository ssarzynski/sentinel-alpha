from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.models import IngestionRun
from app.services.ingestion_runs import start_ingestion_run
from app.services.job_lock import advisory_job_lock
from app.services.sec_ingestion_job import execute_sec_form4_job


@dataclass(frozen=True)
class ScheduledRunResult:
    executed: bool
    reason: str
    run: IngestionRun | None


def run_scheduled_sec_form4(
    db: Session,
    *,
    items: list[SecWatchItem],
    fetch_text: Callable[[str], str],
    started_at: datetime,
    finished_at: Callable[[], datetime],
    metadata: dict | None = None,
) -> ScheduledRunResult:
    """Run the SEC job only when this process owns the database advisory lock."""
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")

    with advisory_job_lock(db, "SEC_FORM4") as acquired:
        if not acquired:
            row = start_ingestion_run(
                db,
                source="SEC_FORM4",
                started_at=started_at,
                config={"watchlist_size": len(items)},
                metadata={**(metadata or {}), "skip_reason": "overlap_lock_busy"},
            )
            row.status = "skipped_overlap"
            row.finished_at = finished_at()
            db.flush()
            return ScheduledRunResult(False, "overlap_lock_busy", row)

        row = execute_sec_form4_job(
            db,
            items=items,
            fetch_text=fetch_text,
            started_at=started_at,
            finished_at=finished_at,
            metadata={**(metadata or {}), "scheduler_lock": "SEC_FORM4"},
        )
        return ScheduledRunResult(True, "executed", row)
