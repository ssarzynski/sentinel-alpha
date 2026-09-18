from datetime import datetime, timezone

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_adapters import ingest_alpha_vantage_daily
from sentinel_alpha.market_warehouse import MarketWarehouse


def test_alpha_vantage_daily_bar_enters_canonical_warehouse_once(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'adapter.db'}");Base.metadata.create_all(engine)
    observed=datetime(2026,9,17,tzinfo=timezone.utc);received=datetime(2026,9,18,13,tzinfo=timezone.utc)
    bar=DailyEquityBar(symbol="nvda",observed_at=observed,open=170.0,high=175.0,low=168.0,close=173.5,volume=123456)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        first,created=ingest_alpha_vantage_daily(warehouse,bar,ingested_at=received)
        second,created_again=ingest_alpha_vantage_daily(warehouse,bar,ingested_at=received)
        assert created is True;assert created_again is False;assert first.id==second.id
        assert first.price==173.5;assert first.metadata_json["volume"]==123456
        assert first.source.provider=="ALPHA_VANTAGE";assert first.asset.symbol=="NVDA"
    engine.dispose()


def test_adapter_preserves_observed_vs_ingested_time(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'times.db'}");Base.metadata.create_all(engine)
    observed=datetime(2020,3,20,tzinfo=timezone.utc);received=datetime(2026,9,18,tzinfo=timezone.utc)
    bar=DailyEquityBar(symbol="NVDA",observed_at=observed,open=50,high=52,low=48,close=51,volume=1000)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db);ingest_alpha_vantage_daily(warehouse,bar,ingested_at=received)
        assert warehouse.history("NVDA",known_by=datetime(2020,3,21,tzinfo=timezone.utc))==[]
        rows=warehouse.history("NVDA",known_by=received);assert len(rows)==1;assert rows[0].observed_at.replace(tzinfo=timezone.utc)==observed
    engine.dispose()
