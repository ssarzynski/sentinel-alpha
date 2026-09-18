from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_models import MarketAsset, MarketObservation, MarketSource


def setup_engine(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'market.db'}")
    Base.metadata.create_all(engine)
    return engine


def test_market_schema_preserves_observation_and_ingestion_time(tmp_path):
    engine=setup_engine(tmp_path)
    with session_scope(engine) as db:
        asset=MarketAsset(symbol="NVDA",asset_type="equity",currency="USD",created_at=datetime.now(timezone.utc))
        source=MarketSource(provider="TEST",source_family="MARKET",channel="daily",created_at=datetime.now(timezone.utc))
        db.add_all([asset,source]);db.flush()
        observed=datetime(2020,3,20,20,tzinfo=timezone.utc);ingested=datetime(2026,9,18,14,tzinfo=timezone.utc)
        db.add(MarketObservation(asset_id=asset.id,source_id=source.id,observed_at=observed,ingested_at=ingested,price=50.0,source_record_id="nvda-20200320",quality_status="accepted",metadata_json={"interval":"1d"}))
    with session_scope(engine) as db:
        row=db.query(MarketObservation).one()
        assert row.observed_at.replace(tzinfo=timezone.utc)==observed
        assert row.ingested_at.replace(tzinfo=timezone.utc)==ingested
    engine.dispose()


def test_provider_record_identity_is_idempotent(tmp_path):
    engine=setup_engine(tmp_path)
    now=datetime.now(timezone.utc)
    with session_scope(engine) as db:
        asset=MarketAsset(symbol="BTC",asset_type="crypto",currency="USD",created_at=now);source=MarketSource(provider="TEST",source_family="MARKET",channel="daily",created_at=now)
        db.add_all([asset,source]);db.flush()
        common=dict(asset_id=asset.id,source_id=source.id,observed_at=now,ingested_at=now,price=100.0,source_record_id="same",quality_status="accepted",metadata_json={})
        db.add(MarketObservation(**common))
    with pytest.raises(IntegrityError):
        with session_scope(engine) as db:
            asset=db.query(MarketAsset).filter_by(symbol="BTC").one();source=db.query(MarketSource).one()
            db.add(MarketObservation(asset_id=asset.id,source_id=source.id,observed_at=now,ingested_at=now,price=101.0,source_record_id="same",quality_status="accepted",metadata_json={}))
    engine.dispose()


def test_duplicate_asset_symbol_is_rejected(tmp_path):
    engine=setup_engine(tmp_path);now=datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        with session_scope(engine) as db:
            db.add_all([MarketAsset(symbol="NVDA",asset_type="equity",currency="USD",created_at=now),MarketAsset(symbol="NVDA",asset_type="equity",currency="USD",created_at=now)])
    engine.dispose()
