from __future__ import annotations

from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.ingestion.sec_watchlist_worker import SecWatchItem, run_form4_watchlist
from app.models import IngestionRun
from app.services.ingestion_runs import fail_ingestion_run, finish_ingestion_run, start_ingestion_run


def execute_sec_form4_job(
    db: Session,
    *,
    items: list[SecWatchItem],
    fetch_text: Callable[[str], str],
    started_at: datetime,
    finished_at: Callable[[], datetime],
    metadata: dict | None = None,
) -> IngestionRun:
    """Execute one observable SEC Form 4 ingestion cycle.

    The run row is created before external work begins and always receives a
    terminal status when execution returns or raises. Transaction commit/rollback
    remains the responsibility of the caller/job runner.
    """
    row = start_ingestion_run(
        db,
        source="SEC_FORM4",
        started_at=started_at,
        config={"watchlist_size": len(items)},
        metadata=metadata,
    )
    try:
        summary = run_form4_watchlist(
            db, items=items, fetch_text=fetch_text, observed_at=started_at
        )
        return finish_ingestion_run(
            db, row=row, finished_at=finished_at(), summary=summary
        )
    except Exception as exc:
        fail_ingestion_run(db, row=row, finished_at=finished_at(), error=exc)
        raise
