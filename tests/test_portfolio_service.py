from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User
from app.services.portfolios import (
    create_portfolio,
    list_portfolios,
    owned_portfolio,
    portfolio_analytics,
    portfolio_positions,
    upsert_position,
)


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def user(db, email: str) -> User:
    row = User(email=email, password_hash="test")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_portfolio_ownership_and_listing_are_isolated():
    db = session()
    alice = user(db, "alice@example.com")
    bob = user(db, "bob@example.com")
    portfolio = create_portfolio(db, alice, name="Core", policy={"max_position_weight": 0.25})

    assert owned_portfolio(db, alice, portfolio.portfolio_key).id == portfolio.id
    assert owned_portfolio(db, bob, portfolio.portfolio_key) is None
    assert [p.portfolio_key for p in list_portfolios(db, alice)] == [portfolio.portfolio_key]
    assert list_portfolios(db, bob) == []


def test_position_upsert_normalizes_and_recomputes_market_value():
    db = session()
    owner = user(db, "owner@example.com")
    portfolio = create_portfolio(db, owner, name="Core")
    observed = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)

    first = upsert_position(db, portfolio, asset="nvda", asset_class="Equity", quantity=2, cost_basis=180, mark_price=220, currency="usd", price_source="TEST", price_observed_at=observed)
    assert first.asset == "NVDA"
    assert first.asset_class == "equity"
    assert first.market_value == 440

    second = upsert_position(db, portfolio, asset="NVDA", asset_class="equity", quantity=3, cost_basis=180, mark_price=225, currency="USD", price_source="TEST2", price_observed_at=observed)
    assert second.id == first.id
    assert second.market_value == 675
    assert second.price_source == "TEST2"
    assert len(portfolio_positions(db, portfolio)) == 1


def test_persisted_positions_feed_portfolio_analytics():
    db = session()
    owner = user(db, "analytics@example.com")
    portfolio = create_portfolio(db, owner, name="Analytics")
    observed = datetime(2026, 9, 17, 17, 55, tzinfo=timezone.utc)
    as_of = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)

    upsert_position(db, portfolio, asset="NVDA", asset_class="equity", quantity=2, cost_basis=None, mark_price=300, currency="USD", price_source="TEST", price_observed_at=observed)
    upsert_position(db, portfolio, asset="BTC", asset_class="crypto", quantity=1, cost_basis=None, mark_price=400, currency="USD", price_source="TEST", price_observed_at=observed)

    result = portfolio_analytics(db, portfolio, as_of=as_of)
    assert result.nav == 1000
    assert result.gross_exposure == 1000
    assert result.largest_position_weight == 0.6
    assert result.asset_class_exposure == {"crypto": 400.0, "equity": 600.0}
    assert result.stale_assets == ()
