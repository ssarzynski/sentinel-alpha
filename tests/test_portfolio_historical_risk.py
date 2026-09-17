from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.market_data import PriceObservationInput
from app.models import User
from app.services.market_prices import persist_price_observation
from app.services.portfolio_risk import portfolio_historical_risk
from app.services.portfolios import create_portfolio, upsert_position

T0 = datetime(2026, 8, 1, 20, 0, tzinfo=timezone.utc)


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup_portfolio(db):
    user = User(email="risk@example.com", password_hash="test")
    db.add(user)
    db.commit()
    db.refresh(user)
    portfolio = create_portfolio(db, user, name="Risk")
    upsert_position(db, portfolio, asset="NVDA", asset_class="equity", quantity=6, cost_basis=None, mark_price=100, currency="USD", price_source="TEST", price_observed_at=T0)
    upsert_position(db, portfolio, asset="BTC", asset_class="crypto", quantity=1, cost_basis=None, mark_price=400, currency="USD", price_source="TEST", price_observed_at=T0)
    return portfolio


def save_history(db, asset, prices, source, family, quality="accepted"):
    for index, price in enumerate(prices):
        persist_price_observation(
            db,
            PriceObservationInput(asset, T0 + timedelta(days=index), price, "USD", source, family, f"{asset}-{index}"),
            quality_status=quality,
        )


def test_risk_uses_only_accepted_provenance_history():
    db = db_session()
    portfolio = setup_portfolio(db)
    nvda = [100 + index + (index % 2) for index in range(22)]
    btc = [200 + 2 * index - (index % 3) for index in range(22)]
    save_history(db, "NVDA", nvda, "A", "exchange")
    save_history(db, "BTC", btc, "B", "institutional")
    save_history(db, "NVDA", [1000 + index for index in range(22)], "BAD", "aggregator", quality="source_disagreement")

    result = portfolio_historical_risk(db, portfolio, min_observations=20)
    assert result.assets == ("BTC", "NVDA")
    assert result.observations == 21
    assert result.annualized_portfolio_volatility >= 0
    assert set(result.correlation_matrix) == {"BTC", "NVDA"}


def test_risk_rejects_asset_without_accepted_history():
    db = db_session()
    portfolio = setup_portfolio(db)
    save_history(db, "NVDA", [100 + i for i in range(22)], "A", "exchange")
    save_history(db, "BTC", [200 + i for i in range(22)], "B", "institutional", quality="source_disagreement")

    with pytest.raises(ValueError, match="insufficient accepted price history for: BTC"):
        portfolio_historical_risk(db, portfolio, min_observations=20)
