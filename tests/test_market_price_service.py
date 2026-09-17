from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.market_data import PriceObservationInput
from app.services.market_prices import accepted_price_histories, accepted_price_history, persist_price_observation

T0 = datetime(2026, 9, 1, 20, 0, tzinfo=timezone.utc)


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def obs(price: float, source: str, family: str, record: str, when=T0):
    return PriceObservationInput("nvda", when, price, "usd", source, family, record)


def test_persist_is_idempotent_for_same_provider_record():
    db = db_session()
    first = persist_price_observation(db, obs(100, "A", "exchange", "1"))
    second = persist_price_observation(db, obs(100, "A", "exchange", "1"))
    assert second.id == first.id


def test_conflicting_persisted_duplicate_is_rejected():
    db = db_session()
    persist_price_observation(db, obs(100, "A", "exchange", "1"))
    with pytest.raises(ValueError, match="conflicting duplicate"):
        persist_price_observation(db, obs(101, "A", "exchange", "1"))


def test_history_uses_only_accepted_rows_and_median_consensus():
    db = db_session()
    persist_price_observation(db, obs(100, "A", "exchange", "1"))
    persist_price_observation(db, obs(102, "B", "institutional", "2"))
    persist_price_observation(db, obs(150, "C", "aggregator", "3"), quality_status="source_disagreement")
    history = accepted_price_history(db, "NVDA")
    assert len(history) == 1
    assert history[0][1] == pytest.approx(101.0)


def test_history_time_window_and_multi_asset_shape():
    db = db_session()
    t1 = T0 + timedelta(days=1)
    t2 = T0 + timedelta(days=2)
    persist_price_observation(db, obs(100, "A", "exchange", "1", T0))
    persist_price_observation(db, obs(110, "A", "exchange", "2", t1))
    persist_price_observation(db, obs(120, "A", "exchange", "3", t2))
    btc = PriceObservationInput("BTC", t1, 50000, "USD", "X", "exchange", "btc-1")
    persist_price_observation(db, btc)

    history = accepted_price_history(db, "NVDA", start=t1, end=t2)
    assert [price for _, price in history] == [110.0, 120.0]
    histories = accepted_price_histories(db, ["nvda", "btc"], start=t1, end=t2)
    assert set(histories) == {"NVDA", "BTC"}
    assert histories["BTC"][0][1] == 50000.0
