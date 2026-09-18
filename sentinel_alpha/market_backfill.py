"""Controlled historical market backfill orchestration.

Provider acquisition stays outside this module. The orchestrator accepts verified
bars, processes bounded batches, and returns a checkpoint suitable for resuming.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.market_adapters import ingest_alpha_vantage_daily
from sentinel_alpha.market_warehouse import MarketWarehouse


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    inserted: int
    existing: int
    checkpoint: datetime | None


def backfill_alpha_vantage_daily(
    warehouse: MarketWarehouse,
    bars: Iterable[DailyEquityBar],
    *,
    ingested_at: datetime | None = None,
    after: datetime | None = None,
    batch_limit: int = 500,
) -> BackfillResult:
    """Store a deterministic bounded batch and report the newest market-time checkpoint."""
    if batch_limit < 1 or batch_limit > 5000:
        raise ValueError("batch_limit must be between 1 and 5000")
    received = ingested_at or datetime.now(timezone.utc)
    candidates = sorted(
        (bar for bar in bars if after is None or bar.observed_at > after),
        key=lambda bar: bar.observed_at,
    )[:batch_limit]
    inserted = existing = 0
    checkpoint = after
    for bar in candidates:
        _, created = ingest_alpha_vantage_daily(warehouse, bar, ingested_at=received)
        if created:
            inserted += 1
        else:
            existing += 1
        checkpoint = bar.observed_at
    return BackfillResult(len(candidates), inserted, existing, checkpoint)
