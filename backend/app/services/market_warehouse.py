from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketPriceObservation


@dataclass(frozen=True)
class MarketObservationInput:
    asset: str
    observed_at: datetime
    price: float
    source: str
    source_family: str
    source_record_id: str
    currency: str = "USD"
    source_url: str | None = None
    quality_status: str = "accepted"
    metadata: dict | None = None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("market timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def store_market_observations(db: Session, observations: Iterable[MarketObservationInput]) -> dict[str, int]:
    """Idempotently persist current or historical market observations.

    Source provenance is retained so research can reconstruct exactly which
    observations were available. This function stores data only; it never
    changes production rules, creates trades, or labels causality.
    """
    inserted = skipped = rejected = 0
    for item in observations:
        asset = item.asset.upper().strip()
        if not asset or item.price <= 0 or not item.source.strip() or not item.source_record_id.strip():
            rejected += 1
            continue
        observed_at = _utc(item.observed_at)
        exists = db.scalar(select(MarketPriceObservation.id).where(
            MarketPriceObservation.asset == asset,
            MarketPriceObservation.source == item.source,
            MarketPriceObservation.source_record_id == item.source_record_id,
        ))
        if exists is not None:
            skipped += 1
            continue
        db.add(MarketPriceObservation(
            asset=asset, observed_at=observed_at, price=item.price,
            currency=item.currency.upper().strip(), source=item.source.strip(),
            source_family=item.source_family.upper().strip(),
            source_record_id=item.source_record_id.strip(), source_url=item.source_url,
            quality_status=item.quality_status, metadata_json=item.metadata or {},
        ))
        inserted += 1
    db.commit()
    return {"inserted": inserted, "skipped_existing": skipped, "rejected": rejected}


def market_history_as_known(db: Session, asset: str, *, start: datetime | None = None, end: datetime | None = None, accepted_only: bool = True) -> list[MarketPriceObservation]:
    """Return chronologically ordered observations for point-in-time research."""
    target = asset.upper().strip()
    query = select(MarketPriceObservation).where(MarketPriceObservation.asset == target)
    if start is not None:
        query = query.where(MarketPriceObservation.observed_at >= _utc(start))
    if end is not None:
        query = query.where(MarketPriceObservation.observed_at <= _utc(end))
    if accepted_only:
        query = query.where(MarketPriceObservation.quality_status == "accepted")
    return list(db.scalars(query.order_by(MarketPriceObservation.observed_at.asc(), MarketPriceObservation.id.asc())).all())
