from __future__ import annotations

from dataclasses import dataclass
from math import fsum, sqrt
from statistics import mean
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RiskAnalytics:
    assets: tuple[str, ...]
    observations: int
    correlation_matrix: dict[str, dict[str, float]]
    annualized_asset_volatility: dict[str, float]
    annualized_portfolio_volatility: float
    diversification_ratio: float


def _validate_series(series: Mapping[str, Sequence[float]], min_observations: int) -> tuple[str, ...]:
    if min_observations < 2:
        raise ValueError("min_observations must be at least 2")
    if not series:
        raise ValueError("at least one return series is required")
    assets = tuple(sorted(series))
    lengths = {len(series[asset]) for asset in assets}
    if len(lengths) != 1:
        raise ValueError("return series must be aligned and equal length")
    observations = next(iter(lengths))
    if observations < min_observations:
        raise ValueError(f"insufficient return history: need at least {min_observations} observations")
    return assets


def _sample_covariance(left: Sequence[float], right: Sequence[float]) -> float:
    left_mean, right_mean = mean(left), mean(right)
    return fsum((x - left_mean) * (y - right_mean) for x, y in zip(left, right)) / (len(left) - 1)


def _sample_variance(values: Sequence[float]) -> float:
    return _sample_covariance(values, values)


def analyze_return_risk(
    return_series: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
    *,
    periods_per_year: int = 252,
    min_observations: int = 20,
) -> RiskAnalytics:
    """Analyze covariance/correlation and portfolio volatility from aligned returns.

    Returns must be decimal period returns (0.01 == 1%). Weights may be signed
    for hedged portfolios. This function provides diagnostics only and does not
    generate or execute portfolio changes.
    """
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    assets = _validate_series(return_series, min_observations)
    missing = set(assets) - set(weights)
    extra = set(weights) - set(assets)
    if missing or extra:
        raise ValueError("weights must contain exactly the assets in return_series")

    covariance: dict[str, dict[str, float]] = {asset: {} for asset in assets}
    correlation: dict[str, dict[str, float]] = {asset: {} for asset in assets}
    variance = {asset: _sample_variance(return_series[asset]) for asset in assets}

    for left in assets:
        for right in assets:
            cov = _sample_covariance(return_series[left], return_series[right])
            covariance[left][right] = cov
            denom = sqrt(max(variance[left], 0.0) * max(variance[right], 0.0))
            correlation[left][right] = cov / denom if denom else (1.0 if left == right else 0.0)

    period_variance = fsum(
        float(weights[left]) * float(weights[right]) * covariance[left][right]
        for left in assets
        for right in assets
    )
    portfolio_vol = sqrt(max(period_variance, 0.0) * periods_per_year)
    asset_vol = {asset: sqrt(max(variance[asset], 0.0) * periods_per_year) for asset in assets}
    weighted_standalone = fsum(abs(float(weights[asset])) * asset_vol[asset] for asset in assets)
    diversification_ratio = weighted_standalone / portfolio_vol if portfolio_vol else 0.0

    return RiskAnalytics(
        assets=assets,
        observations=len(return_series[assets[0]]),
        correlation_matrix=correlation,
        annualized_asset_volatility=asset_vol,
        annualized_portfolio_volatility=portfolio_vol,
        diversification_ratio=diversification_ratio,
    )
