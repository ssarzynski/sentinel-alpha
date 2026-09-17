from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Portfolio, PortfolioPosition, User
from app.portfolio import PositionInput, analyze_portfolio


def create_portfolio(db: Session, user: User, *, name: str, base_currency: str = "USD", policy: dict | None = None) -> Portfolio:
    row = Portfolio(
        portfolio_key=str(uuid4()),
        name=name.strip(),
        base_currency=base_currency.upper().strip(),
        owner_user_id=user.id,
        policy_json=policy or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def owned_portfolio(db: Session, user: User, portfolio_key: str) -> Portfolio | None:
    return db.query(Portfolio).filter(Portfolio.portfolio_key == portfolio_key, Portfolio.owner_user_id == user.id).first()


def list_portfolios(db: Session, user: User) -> list[Portfolio]:
    return db.query(Portfolio).filter(Portfolio.owner_user_id == user.id).order_by(Portfolio.created_at.desc()).all()


def upsert_position(
    db: Session,
    portfolio: Portfolio,
    *,
    asset: str,
    asset_class: str,
    quantity: float,
    cost_basis: float | None,
    mark_price: float,
    currency: str,
    price_source: str,
    price_observed_at: datetime,
    metadata: dict | None = None,
) -> PortfolioPosition:
    normalized_asset = asset.upper().strip()
    row = db.query(PortfolioPosition).filter(
        PortfolioPosition.portfolio_id == portfolio.id,
        PortfolioPosition.asset == normalized_asset,
    ).first()
    market_value = float(quantity) * float(mark_price)
    values = {
        "asset_class": asset_class.lower().strip(),
        "quantity": float(quantity),
        "cost_basis": float(cost_basis) if cost_basis is not None else None,
        "mark_price": float(mark_price),
        "market_value": market_value,
        "currency": currency.upper().strip(),
        "price_source": price_source.strip(),
        "price_observed_at": price_observed_at,
        "metadata_json": metadata or {},
    }
    if row is None:
        row = PortfolioPosition(portfolio_id=portfolio.id, asset=normalized_asset, **values)
        db.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def portfolio_positions(db: Session, portfolio: Portfolio) -> list[PortfolioPosition]:
    return db.query(PortfolioPosition).filter(PortfolioPosition.portfolio_id == portfolio.id).order_by(PortfolioPosition.asset.asc()).all()


def portfolio_analytics(db: Session, portfolio: Portfolio, *, as_of: datetime, stale_after_minutes: int = 30):
    rows = portfolio_positions(db, portfolio)
    return analyze_portfolio(
        [PositionInput(asset=r.asset, asset_class=r.asset_class, market_value=r.market_value, price_observed_at=r.price_observed_at) for r in rows],
        as_of=as_of,
        stale_after=timedelta(minutes=stale_after_minutes),
    )
