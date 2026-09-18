"""Controlled historical market backfill orchestration.

Provider acquisition stays outside this module. Batches are bounded and durable
progress can resume from the last committed market-time checkpoint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable

from sqlalchemy import select

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.market_adapters import ingest_alpha_vantage_daily
from sentinel_alpha.market_models import MarketBackfillRun
from sentinel_alpha.market_warehouse import MarketWarehouse
from sentinel_alpha.time_utils import as_utc

if TYPE_CHECKING:
    from sentinel_alpha.resource_metrics import ResourceMetrics


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    inserted: int
    existing: int
    checkpoint: datetime | None


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
            provider="ALPHA_VANTAGE", symbol=normalized, channel="daily",
            status="running", processed=0, inserted=0, existing=0,
            started_at=received, updated_at=received,
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
    metrics: "ResourceMetrics | None" = None,
) -> BackfillResult:
    """Store one bounded batch and optionally report compact usage counters.

    Provider acquisition occurs before this function, so provider-call accounting
    belongs at the acquisition boundary rather than being guessed here.
    """
    if batch_limit < 1 or batch_limit > 5000:
        raise ValueError("batch_limit must be between 1 and 5000")
    received = as_utc(ingested_at or datetime.now(timezone.utc))
    assert received is not None
    materialized = list(bars)
    if not materialized:
        return BackfillResult(0, 0, 0, as_utc(after))
    symbols = {bar.symbol.strip().upper() for bar in materialized}
    if len(symbols) != 1:
        raise ValueError("one backfill batch must contain exactly one symbol")

    run = _run(warehouse, next(iter(symbols)), received) if persist_progress else None
    checkpoint = as_utc(after if after is not None else (run.checkpoint_at if run is not None else None))
    candidates = sorted(
        (bar for bar in materialized if checkpoint is None or as_utc(bar.observed_at) > checkpoint),
        key=lambda bar: as_utc(bar.observed_at),
    )[:batch_limit]
    inserted = existing = 0
    for bar in candidates:
        _, created = ingest_alpha_vantage_daily(warehouse, bar, ingested_at=received)
        inserted += int(created)
        existing += int(not created)
        checkpoint = as_utc(bar.observed_at)

    if run is not None:
        run.status = "running" if len(candidates) == batch_limit else "complete"
        run.checkpoint_at = checkpoint
        run.processed += len(candidates)
        run.inserted += inserted
        run.existing += existing
        run.updated_at = received
        run.error_message = None
        warehouse.session.flush()

    if metrics is not None:
        metrics.record_records(len(candidates))
        # Count durable canonical rows, not Python object size or derived data.
        # Byte growth is intentionally left for the storage boundary where it can
        # be measured accurately rather than estimated here.

    return BackfillResult(len(candidates), inserted, existing, checkpoint)
