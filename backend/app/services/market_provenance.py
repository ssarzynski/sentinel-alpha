from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import MarketPriceObservation


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def market_provenance_summary(db: Session, assets: list[str], *, now: datetime | None = None, stale_after_minutes: int = 60) -> list[dict]:
    if stale_after_minutes < 1:
        raise ValueError("stale_after_minutes must be positive")
    now = _utc(now or datetime.now(timezone.utc))
    normalized = sorted({asset.upper().strip() for asset in assets if asset.strip()})
    if not normalized:
        return []
    rows = db.query(MarketPriceObservation).filter(MarketPriceObservation.asset.in_(normalized)).order_by(MarketPriceObservation.observed_at.desc()).all()
    grouped: defaultdict[str, list[MarketPriceObservation]] = defaultdict(list)
    for row in rows:
        grouped[row.asset].append(row)
    output = []
    for asset in normalized:
        observations = grouped.get(asset, [])
        accepted = [row for row in observations if row.quality_status == "accepted"]
        rejected = [row for row in observations if row.quality_status != "accepted"]
        latest = max((_utc(row.observed_at) for row in accepted), default=None)
        age_minutes = ((now - latest).total_seconds() / 60.0) if latest else None
        families = sorted({row.source_family for row in accepted})
        sources = sorted({row.source for row in accepted})
        statuses: defaultdict[str, int] = defaultdict(int)
        for row in observations:
            statuses[row.quality_status] += 1
        output.append({
            "asset": asset,
            "accepted_observations": len(accepted),
            "rejected_observations": len(rejected),
            "quality_status_counts": dict(sorted(statuses.items())),
            "independent_source_families": len(families),
            "source_families": families,
            "sources": sources,
            "latest_accepted_at": latest,
            "age_minutes": age_minutes,
            "fresh": age_minutes is not None and age_minutes <= stale_after_minutes,
            "confirmation_gap": len(families) < 2,
        })
    return output
