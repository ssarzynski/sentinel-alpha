from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.market_data import PriceObservationInput
from app.services.market_prices import persist_price_observation
from app.services.market_provenance import market_provenance_summary

NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def save(db, asset, source, family, record, quality="accepted", minutes=5):
    persist_price_observation(db, PriceObservationInput(asset, NOW-timedelta(minutes=minutes), 100, "USD", source, family, record), quality_status=quality)


def test_provenance_counts_independent_families_and_quality_states():
    db=db_session(); save(db,"NVDA","A","exchange","1"); save(db,"NVDA","B","institutional","2"); save(db,"NVDA","C","aggregator","3","source_disagreement")
    row=market_provenance_summary(db,["nvda"],now=NOW)[0]
    assert row["accepted_observations"]==2
    assert row["rejected_observations"]==1
    assert row["independent_source_families"]==2
    assert row["confirmation_gap"] is False
    assert row["quality_status_counts"]["source_disagreement"]==1


def test_same_family_exposes_confirmation_gap():
    db=db_session(); save(db,"BTC","A","aggregator","1"); save(db,"BTC","B","aggregator","2")
    row=market_provenance_summary(db,["BTC"],now=NOW)[0]
    assert row["independent_source_families"]==1
    assert row["confirmation_gap"] is True


def test_freshness_uses_latest_accepted_observation_only():
    db=db_session(); save(db,"ETH","A","exchange","1",minutes=120); save(db,"ETH","B","institutional","2","source_disagreement",minutes=1)
    row=market_provenance_summary(db,["ETH"],now=NOW,stale_after_minutes=60)[0]
    assert row["fresh"] is False
    assert row["age_minutes"]==120


def test_missing_asset_is_explicit_gap():
    row=market_provenance_summary(db_session(),["MSFT"],now=NOW)[0]
    assert row["accepted_observations"]==0
    assert row["fresh"] is False
    assert row["confirmation_gap"] is True
