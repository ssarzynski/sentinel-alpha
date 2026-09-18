from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import pstdev
from typing import Sequence

from app.models import MarketPriceObservation


@dataclass(frozen=True)
class MarketFeatures:
    asset: str
    observations: int
    latest_price: float
    return_1: float | None
    return_5: float | None
    return_20: float | None
    volatility_20: float | None
    drawdown_from_peak: float
    trend_20: str


def _return(prices: Sequence[float], periods: int) -> float | None:
    if len(prices) <= periods or prices[-periods - 1] <= 0:
        return None
    return prices[-1] / prices[-periods - 1] - 1.0


def _daily_returns(prices: Sequence[float]) -> list[float]:
    return [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices)) if prices[i - 1] > 0]


def compute_market_features(rows: Sequence[MarketPriceObservation]) -> MarketFeatures:
    """Compute descriptive features using only rows supplied by the caller.

    Callers must provide a point-in-time bounded history. No future observations
    are fetched here, preventing this layer from silently introducing look-ahead.
    """
    if not rows:
        raise ValueError("at least one market observation is required")
    asset = rows[0].asset.upper()
    if any(row.asset.upper() != asset for row in rows):
        raise ValueError("all observations must belong to one asset")
    ordered = sorted(rows, key=lambda row: (row.observed_at, row.id or 0))
    prices = [float(row.price) for row in ordered]
    if any(price <= 0 for price in prices):
        raise ValueError("market prices must be positive")

    recent = prices[-21:]
    daily = _daily_returns(recent)
    vol20 = pstdev(daily) * sqrt(252) if len(daily) >= 2 else None
    peak = max(prices)
    drawdown = prices[-1] / peak - 1.0
    r20 = _return(prices, 20)
    trend = "insufficient_history" if r20 is None else "up" if r20 > 0 else "down" if r20 < 0 else "flat"

    return MarketFeatures(
        asset=asset,
        observations=len(prices),
        latest_price=prices[-1],
        return_1=_return(prices, 1),
        return_5=_return(prices, 5),
        return_20=r20,
        volatility_20=vol20,
        drawdown_from_peak=drawdown,
        trend_20=trend,
    )
