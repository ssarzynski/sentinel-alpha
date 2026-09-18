"""Controlled historical market backfill orchestration.

Provider acquisition stays outside this module. Batches are bounded and durable
progress can resume from the last committed market-time checkpoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.market_adapters import ingest_alpha_vantage_daily
from sentinel_alpha.market_models import MarketBackfillRun
from sentinel_alpha.market_warehouse import MarketWarehouse


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    inserted: int
    existing: int
    checkpoint: datetime | None


def _as_utc(value: datetime | None) -> datetime | None:
    """Normalize database/provider datetimes to comparable UTC-aware values.

    SQLite can return a timezone-naive datetime even for DateTime(timezone=True).
    Sentinel stores UTC, so a naive persisted checkpoint is interpreted as UTC.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _run(warehouse: MarketWarehouse, symbol: str, received: datetime) -> MarketBackfillRun:
    session = warehouse.session
    normalized = symbol.strip().upper()
    run = session.scalar(
        select(MarketBackfillRun).where(
            MarketBackfillRun.provider == "ALPHA_VANTAGE",
            MarketBackfillRun.symbol == normalized,
            MarketBackfillRun.channel == "daily",
        )
    )
    if run is None:
        run = MarketBackfillRun(
            provider="ALPHA_VANTAGE",
            symbol=normalized,
            channel="daily",
            status="running",
            processed=0,
            inserted=0,
            existing=0,
            started_at=received,
            updated_at=received,
        )
        session.add(run)
        session.flush()
    return run


def backfill_alpha_vantage_daily(
    warehouse: MarketWarehouse,
    bars: Iterable[DailyEquityBar],
    *,
    ingested_at: datetime | None = None,
    after: datetime | None = None,
    batch_limit: int = 500,
    persist_progress: bool = False,
) -> BackfillResult:
    """Store one bounded batch, optionally resuming/updating durable progress."""
    if batch_limit < 1 or batch_limit > 5000:
        raise ValueError("batch_limit must be between 1 and 5000")
    received = _as_utc(ingested_at or datetime.now(timezone.utc))
    materialized = list(bars)
    if not materialized:
        return BackfillResult(0, 0, 0, _as_utc(after))
    symbols = {bar.symbol.strip().upper() for bar in materialized}
    if len(symbols) != 1:
        raise ValueError("one backfill batch must contain exactly one symbol")

    run = _run(warehouse, next(iter(symbols)), received) if persist_progress else None
    checkpoint = _as_utc(after if after is not None else (run.checkpoint_at if run is not None else None))
    candidates = sorted(
        (bar for bar in materialized if checkpoint is None or _as_utc(bar.observed_at) > checkpoint),
        key=lambda bar: _as_utc(bar.observed_at),
    )[:batch_limit]
    inserted = existing = 0
    for bar in candidates:
        _, created = ingest_alpha_vantage_daily(warehouse, bar, ingested_at=received)
        inserted += int(created)
        existing += int(not created)
        checkpoint = _as_utc(bar.observed_at)

    if run is not None:
        run.status = "running" if len(candidates) == batch_limit else "complete"
        run.checkpoint_at = checkpoint
        run.processed += len(candidates)
        run.inserted += inserted
        run.existing += existing
        run.updated_at = received
        run.error_message = None
        warehouse.session.flush()

    return BackfillResult(len(candidates), inserted, existing, checkpoint)
