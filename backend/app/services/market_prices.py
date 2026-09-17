from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median

from sqlalchemy.orm import Session

from app.market_data import PriceObservationInput, normalize_observation
from app.models import MarketPriceObservation


def persist_price_observation(db: Session, raw: PriceObservationInput, *, quality_status: str = "accepted", metadata: dict | None = None) -> MarketPriceObservation:
    row = normalize_observation(raw)
    existing = db.query(MarketPriceObservation).filter(
        MarketPriceObservation.asset == row.asset,
        MarketPriceObservation.source == row.source,
        MarketPriceObservation.source_record_id == row.source_record_id,
    ).first()
    if existing is not None:
        same = (
            existing.observed_at == row.observed_at
            and existing.price == row.price
            and existing.currency == row.currency
            and existing.source_family == row.source_family
        )
        if not same:
            raise ValueError("conflicting duplicate market price observation")
        return existing
    saved = MarketPriceObservation(
        asset=row.asset,
        observed_at=row.observed_at,
        price=row.price,
        currency=row.currency,
        source=row.source,
        source_family=row.source_family,
        source_record_id=row.source_record_id,
        source_url=row.source_url,
        quality_status=quality_status,
        metadata_json=metadata or {},
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


def accepted_price_history(db: Session, asset: str, *, start: datetime | None = None, end: datetime | None = None) -> list[tuple[datetime, float]]:
    query = db.query(MarketPriceObservation).filter(
        MarketPriceObservation.asset == asset.upper().strip(),
        MarketPriceObservation.quality_status == "accepted",
    )
    if start is not None:
        query = query.filter(MarketPriceObservation.observed_at >= start)
    if end is not None:
        query = query.filter(MarketPriceObservation.observed_at <= end)
    rows = query.order_by(MarketPriceObservation.observed_at.asc()).all()
    by_time: defaultdict[datetime, list[float]] = defaultdict(list)
    for row in rows:
        by_time[row.observed_at].append(row.price)
    return [(timestamp, float(median(prices))) for timestamp, prices in sorted(by_time.items())]


def accepted_price_histories(db: Session, assets: list[str], *, start: datetime | None = None, end: datetime | None = None) -> dict[str, list[tuple[datetime, float]]]:
    return {asset.upper().strip(): accepted_price_history(db, asset, start=start, end=end) for asset in assets}
