from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ingestion.sec_watchlist_worker import SecWatchItem
from app.models import IngestionRun
from app.services.sec_ingestion_job import execute_sec_form4_job


@dataclass(frozen=True)
class SchedulerDecision:
    due: bool
    reason: str
    next_due_at: datetime | None


def sec_form4_schedule_decision(
    db: Session,
    *,
    now: datetime,
    interval_minutes: int = 15,
    max_running_minutes: int = 30,
) -> SchedulerDecision:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if interval_minutes < 1 or max_running_minutes < 1:
        raise ValueError("scheduler intervals must be positive")

    latest = db.scalar(
        select(IngestionRun)
        .where(IngestionRun.source == "SEC_FORM4")
        .order_by(desc(IngestionRun.started_at))
        .limit(1)
    )
    if latest is None:
        return SchedulerDecision(True, "never_run", now)

    if latest.status == "running":
        running_until = latest.started_at + timedelta(minutes=max_running_minutes)
        if now < running_until:
            return SchedulerDecision(False, "run_in_progress", running_until)
        return SchedulerDecision(True, "stale_running_run", now)

    terminal = latest.finished_at or latest.started_at
    next_due = terminal + timedelta(minutes=interval_minutes)
    if now >= next_due:
        return SchedulerDecision(True, "interval_elapsed", next_due)
    return SchedulerDecision(False, "waiting_for_interval", next_due)


def run_scheduled_sec_form4_cycle(
    db: Session,
    *,
    items: list[SecWatchItem],
    fetch_text,
    now: datetime,
    finished_at,
    interval_minutes: int = 15,
    max_running_minutes: int = 30,
    metadata: dict | None = None,
) -> tuple[SchedulerDecision, IngestionRun | None]:
    decision = sec_form4_schedule_decision(
        db,
        now=now,
        interval_minutes=interval_minutes,
        max_running_minutes=max_running_minutes,
    )
    if not decision.due:
        return decision, None
    row = execute_sec_form4_job(
        db,
        items=items,
        fetch_text=fetch_text,
        started_at=now,
        finished_at=finished_at,
        metadata={"scheduler": "sec_form4", "interval_minutes": interval_minutes, **(metadata or {})},
    )
    return decision, row
