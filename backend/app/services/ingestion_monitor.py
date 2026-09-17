from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import IngestionRun


def latest_ingestion_runs(db: Session, *, source: str | None = None, limit: int = 50) -> list[IngestionRun]:
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")
    stmt = select(IngestionRun)
    if source:
        stmt = stmt.where(IngestionRun.source == source)
    stmt = stmt.order_by(desc(IngestionRun.started_at)).limit(limit)
    return list(db.scalars(stmt).all())


def ingestion_health(db: Session, *, source: str, now: datetime, stale_after_minutes: int = 60) -> dict[str, object]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if stale_after_minutes < 1:
        raise ValueError("stale_after_minutes must be positive")
    latest = db.scalar(
        select(IngestionRun).where(IngestionRun.source == source).order_by(desc(IngestionRun.started_at)).limit(1)
    )
    if latest is None:
        return {"source": source, "status": "never_run", "healthy": False, "latest_run": None}
    terminal_time = latest.finished_at or latest.started_at
    stale = now.astimezone(timezone.utc) - terminal_time.astimezone(timezone.utc) > timedelta(minutes=stale_after_minutes)
    healthy = latest.status == "completed" and not stale
    status = "stale" if stale else latest.status
    return {
        "source": source, "status": status, "healthy": healthy, "stale": stale,
        "latest_run": latest.run_key, "started_at": latest.started_at,
        "finished_at": latest.finished_at, "failures": len(latest.failures_json or []),
    }
