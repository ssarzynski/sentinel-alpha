from datetime import datetime, timezone

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput


def _item(record_id, observed, ingested, price=100.0):
    return ObservationInput(symbol=" nvda ",asset_type="equity",provider="test",source_family="market",channel="daily",observed_at=observed,ingested_at=ingested,price=price,source_record_id=record_id)


def test_ingest_is_idempotent_and_normalizes_identity(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'warehouse.db'}");Base.metadata.create_all(engine)
    observed=datetime(2026,1,2,tzinfo=timezone.utc);ingested=datetime(2026,1,3,tzinfo=timezone.utc)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        first,created=warehouse.ingest(_item("r1",observed,ingested))
        second,created_again=warehouse.ingest(_item("r1",observed,ingested,999.0))
        assert created is True;assert created_again is False;assert first.id==second.id;assert first.asset.symbol=="NVDA";assert first.source.provider=="TEST"
    engine.dispose()


def test_known_by_prevents_historical_lookahead(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'point_in_time.db'}");Base.metadata.create_all(engine)
    jan1=datetime(2020,1,1,tzinfo=timezone.utc);jan2=datetime(2020,1,2,tzinfo=timezone.utc);late=datetime(2026,9,18,tzinfo=timezone.utc)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        warehouse.ingest(_item("known",jan1,jan2,10.0))
        warehouse.ingest(_item("backfill",jan2,late,11.0))
        rows=warehouse.history("NVDA",known_by=datetime(2020,1,3,tzinfo=timezone.utc))
        assert [row.source_record_id for row in rows]==["known"]
    engine.dispose()


def test_history_orders_by_market_time(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'order.db'}");Base.metadata.create_all(engine)
    t1=datetime(2024,1,1,tzinfo=timezone.utc);t2=datetime(2024,1,2,tzinfo=timezone.utc);ingested=datetime(2026,1,1,tzinfo=timezone.utc)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db);warehouse.ingest(_item("later",t2,ingested));warehouse.ingest(_item("earlier",t1,ingested))
        assert [row.source_record_id for row in warehouse.history("nvda")]==["earlier","later"]
    engine.dispose()
