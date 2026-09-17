from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from statistics import median
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class PriceObservationInput:
    asset: str
    observed_at: datetime
    price: float
    currency: str
    source: str
    source_family: str
    source_record_id: str
    source_url: str | None = None


@dataclass(frozen=True)
class PriceQualityResult:
    asset: str
    observed_at: datetime
    consensus_price: float
    independent_source_families: int
    max_relative_deviation: float
    quality_status: str
    accepted: tuple[PriceObservationInput, ...]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_observation(row: PriceObservationInput) -> PriceObservationInput:
    asset = row.asset.upper().strip()
    currency = row.currency.upper().strip()
    source = row.source.strip()
    family = row.source_family.strip()
    record_id = row.source_record_id.strip()
    price = float(row.price)
    if not asset or not source or not family or not record_id:
        raise ValueError("asset, source, source_family and source_record_id are required")
    if not currency:
        raise ValueError("currency is required")
    if not isfinite(price) or price <= 0:
        raise ValueError("price must be finite and positive")
    return PriceObservationInput(asset, _utc(row.observed_at), price, currency, source, family, record_id, row.source_url)


def deduplicate_observations(rows: Iterable[PriceObservationInput]) -> tuple[PriceObservationInput, ...]:
    unique: dict[tuple[str, str, str], PriceObservationInput] = {}
    for raw in rows:
        row = normalize_observation(raw)
        key = (row.asset, row.source, row.source_record_id)
        existing = unique.get(key)
        if existing is not None and existing != row:
            raise ValueError(f"conflicting duplicate source record: {key}")
        unique[key] = row
    return tuple(sorted(unique.values(), key=lambda r: (r.asset, r.observed_at, r.source, r.source_record_id)))


def assess_cross_source_quality(
    rows: Iterable[PriceObservationInput],
    *,
    disagreement_threshold: float = 0.02,
    minimum_independent_families: int = 2,
) -> PriceQualityResult:
    if disagreement_threshold <= 0:
        raise ValueError("disagreement_threshold must be positive")
    if minimum_independent_families < 1:
        raise ValueError("minimum_independent_families must be at least 1")
    accepted = deduplicate_observations(rows)
    if not accepted:
        raise ValueError("at least one price observation is required")
    assets = {r.asset for r in accepted}
    timestamps = {r.observed_at for r in accepted}
    currencies = {r.currency for r in accepted}
    if len(assets) != 1 or len(timestamps) != 1 or len(currencies) != 1:
        raise ValueError("quality comparison requires one asset, timestamp and currency")
    consensus = float(median(r.price for r in accepted))
    max_deviation = max(abs(r.price - consensus) / consensus for r in accepted)
    families = len({r.source_family for r in accepted})
    if families < minimum_independent_families:
        status = "insufficient_independence"
    elif max_deviation > disagreement_threshold:
        status = "source_disagreement"
    else:
        status = "accepted"
    first = accepted[0]
    return PriceQualityResult(first.asset, first.observed_at, consensus, families, max_deviation, status, accepted)


def build_aligned_returns(price_history: Mapping[str, Sequence[tuple[datetime, float]]]) -> dict[str, list[float]]:
    """Build simple period returns only on timestamps shared by every asset."""
    if not price_history:
        raise ValueError("price_history is required")
    normalized: dict[str, dict[datetime, float]] = {}
    for asset, rows in price_history.items():
        points: dict[datetime, float] = {}
        for timestamp, raw_price in rows:
            price = float(raw_price)
            if not isfinite(price) or price <= 0:
                raise ValueError(f"invalid price for {asset}")
            ts = _utc(timestamp)
            if ts in points and points[ts] != price:
                raise ValueError(f"conflicting price for {asset} at {ts.isoformat()}")
            points[ts] = price
        normalized[asset.upper().strip()] = points
    shared = set.intersection(*(set(points) for points in normalized.values()))
    ordered = sorted(shared)
    if len(ordered) < 2:
        raise ValueError("at least two aligned price timestamps are required")
    returns: dict[str, list[float]] = {}
    for asset, points in sorted(normalized.items()):
        prices = [points[ts] for ts in ordered]
        returns[asset] = [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]
    return returns
