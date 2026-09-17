from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import fsum
from typing import Iterable


@dataclass(frozen=True)
class PositionInput:
    asset: str
    asset_class: str
    market_value: float
    price_observed_at: datetime


@dataclass(frozen=True)
class PositionAnalytics:
    asset: str
    asset_class: str
    market_value: float
    weight: float
    stale_price: bool


@dataclass(frozen=True)
class PortfolioAnalytics:
    nav: float
    gross_exposure: float
    net_exposure: float
    largest_position_weight: float
    herfindahl_index: float
    stale_assets: tuple[str, ...]
    asset_class_exposure: dict[str, float]
    positions: tuple[PositionAnalytics, ...]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def analyze_portfolio(
    positions: Iterable[PositionInput],
    *,
    as_of: datetime | None = None,
    stale_after: timedelta = timedelta(minutes=30),
) -> PortfolioAnalytics:
    """Calculate deterministic exposure and concentration metrics.

    Signed market values are supported: long positions are positive and short
    positions negative. Portfolio weights use absolute exposure so concentration
    remains meaningful for long/short books. This function is analytics-only;
    it does not generate orders or authorize trades.
    """
    if stale_after.total_seconds() <= 0:
        raise ValueError("stale_after must be positive")

    now = _utc(as_of or datetime.now(timezone.utc))
    rows = tuple(positions)
    gross = fsum(abs(float(row.market_value)) for row in rows)
    net = fsum(float(row.market_value) for row in rows)

    class_exposure: defaultdict[str, float] = defaultdict(float)
    analyzed: list[PositionAnalytics] = []
    stale_assets: list[str] = []

    for row in rows:
        value = float(row.market_value)
        weight = abs(value) / gross if gross else 0.0
        stale = now - _utc(row.price_observed_at) > stale_after
        if stale:
            stale_assets.append(row.asset)
        class_exposure[row.asset_class] += value
        analyzed.append(
            PositionAnalytics(
                asset=row.asset,
                asset_class=row.asset_class,
                market_value=value,
                weight=weight,
                stale_price=stale,
            )
        )

    weights = [row.weight for row in analyzed]
    return PortfolioAnalytics(
        nav=net,
        gross_exposure=gross,
        net_exposure=net,
        largest_position_weight=max(weights, default=0.0),
        herfindahl_index=fsum(weight * weight for weight in weights),
        stale_assets=tuple(sorted(stale_assets)),
        asset_class_exposure=dict(sorted(class_exposure.items())),
        positions=tuple(sorted(analyzed, key=lambda row: (-row.weight, row.asset))),
    )
