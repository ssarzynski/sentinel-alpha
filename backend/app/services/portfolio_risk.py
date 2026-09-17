from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.market_data import build_aligned_returns
from app.models import Portfolio
from app.portfolio_risk import RiskAnalytics, analyze_return_risk
from app.services.market_prices import accepted_price_histories
from app.services.portfolios import portfolio_positions


def portfolio_historical_risk(
    db: Session,
    portfolio: Portfolio,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    periods_per_year: int = 252,
    min_observations: int = 20,
) -> RiskAnalytics:
    positions = portfolio_positions(db, portfolio)
    if not positions:
        raise ValueError("portfolio has no positions")

    gross = sum(abs(float(row.market_value)) for row in positions)
    if gross <= 0:
        raise ValueError("portfolio gross exposure must be positive")

    assets = [row.asset for row in positions]
    histories = accepted_price_histories(db, assets, start=start, end=end)
    missing = sorted(asset for asset, history in histories.items() if len(history) < 2)
    if missing:
        raise ValueError(f"insufficient accepted price history for: {', '.join(missing)}")

    returns = build_aligned_returns(histories)
    weights = {row.asset: float(row.market_value) / gross for row in positions}
    return analyze_return_risk(
        returns,
        weights,
        periods_per_year=periods_per_year,
        min_observations=min_observations,
    )
