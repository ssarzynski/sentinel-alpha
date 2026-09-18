from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.market_warehouse import MarketObservationInput, market_history_as_known, store_market_observations


@pytest.fixture
def db_session():
    engine=create_engine("sqlite+pysqlite:///:memory:");Base.metadata.create_all(engine);db=sessionmaker(bind=engine)()
    try: yield db
    finally: db.close();engine.dispose()


def obs(record, when, price=100.0, source="TEST"):
    return MarketObservationInput(asset="nvda",observed_at=datetime.fromisoformat(when).replace(tzinfo=timezone.utc),price=price,source=source,source_family="MARKET",source_record_id=record,metadata={"interval":"1d"})


def test_stores_current_and_historical_observations_in_time_order(db_session):
    result=store_market_observations(db_session,[obs("new","2026-09-18T12:00:00",120),obs("old","2020-03-20T20:00:00",50)])
    assert result=={"inserted":2,"skipped_existing":0,"rejected":0}
    rows=market_history_as_known(db_session,"NVDA")
    assert [r.source_record_id for r in rows]==["old","new"]
    assert [r.price for r in rows]==[50,120]


def test_duplicate_provider_record_is_idempotent(db_session):
    item=obs("same","2026-09-18T12:00:00")
    store_market_observations(db_session,[item]);result=store_market_observations(db_session,[item])
    assert result["skipped_existing"]==1
    assert len(market_history_as_known(db_session,"NVDA"))==1


def test_invalid_prices_are_rejected_not_learned(db_session):
    result=store_market_observations(db_session,[obs("bad","2026-09-18T12:00:00",0)])
    assert result["rejected"]==1
    assert market_history_as_known(db_session,"NVDA")==[]


def test_naive_timestamp_is_rejected_at_ingestion_boundary(db_session):
    item=MarketObservationInput(asset="NVDA",observed_at=datetime(2026,9,18,12),price=100,source="TEST",source_family="MARKET",source_record_id="naive")
    with pytest.raises(ValueError,match="timezone-aware"):
        store_market_observations(db_session,[item])


def test_point_in_time_window_prevents_future_leakage(db_session):
    store_market_observations(db_session,[obs("past","2020-01-01T20:00:00",10),obs("future","2021-01-01T20:00:00",20)])
    rows=market_history_as_known(db_session,"NVDA",end=datetime(2020,6,1,tzinfo=timezone.utc))
    assert [r.source_record_id for r in rows]==["past"]
