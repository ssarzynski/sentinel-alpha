"""Deterministic point-in-time market feature extraction.

Features are descriptive inputs for later research. This module does not score,
predict, recommend, size positions, or trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import pstdev

from sentinel_alpha.market_warehouse import MarketWarehouse


@dataclass(frozen=True)
class MarketFeatures:
    symbol: str
    as_of: datetime | None
    observations: int
    price: float | None
    return_1: float | None
    return_5: float | None
    volatility_5: float | None
    volume_change_1: float | None
    trend_5: float | None


def _pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return current / previous - 1.0


def extract_market_features(
    warehouse: MarketWarehouse,
    symbol: str,
    *,
    known_by: datetime,
) -> MarketFeatures:
    """Build features solely from observations available by ``known_by``."""
    rows = warehouse.history(symbol, known_by=known_by)
    normalized = symbol.strip().upper()
    if not rows:
        return MarketFeatures(normalized, None, 0, None, None, None, None, None, None)

    closes = [float(row.price) for row in rows]
    one = _pct_change(closes[-1], closes[-2]) if len(closes) >= 2 else None
    five = _pct_change(closes[-1], closes[-6]) if len(closes) >= 6 else None

    daily_returns = [
        change
        for current, previous in zip(closes[-5:], closes[-6:-1])
        if (change := _pct_change(current, previous)) is not None
    ] if len(closes) >= 6 else []
    volatility = pstdev(daily_returns) * sqrt(252) if len(daily_returns) == 5 else None

    def volume(row):
        value = (row.metadata_json or {}).get("volume")
        return float(value) if value is not None else None

    current_volume = volume(rows[-1])
    prior_volume = volume(rows[-2]) if len(rows) >= 2 else None
    volume_change = (
        _pct_change(current_volume, prior_volume)
        if current_volume is not None and prior_volume is not None
        else None
    )

    trend = None
    if len(closes) >= 5:
        mean_5 = sum(closes[-5:]) / 5
        trend = _pct_change(closes[-1], mean_5)

    return MarketFeatures(
        symbol=normalized,
        as_of=rows[-1].observed_at,
        observations=len(rows),
        price=closes[-1],
        return_1=one,
        return_5=five,
        volatility_5=volatility,
        volume_change_1=volume_change,
        trend_5=trend,
    )
