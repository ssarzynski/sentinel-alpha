from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_backfill import backfill_alpha_vantage_daily
from sentinel_alpha.market_warehouse import MarketWarehouse

BASE=datetime(2020,1,1,tzinfo=timezone.utc)


def bar(day):
    return DailyEquityBar(symbol="NVDA",observed_at=BASE+timedelta(days=day),open=100+day,high=102+day,low=99+day,close=101+day,volume=1000+day)


def test_backfill_is_bounded_and_resumable(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'backfill.db'}");Base.metadata.create_all(engine)
    received=datetime(2026,9,18,tzinfo=timezone.utc)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        first=backfill_alpha_vantage_daily(warehouse,[bar(3),bar(1),bar(2)],ingested_at=received,batch_limit=2)
        assert first.processed==2;assert first.inserted==2;assert first.checkpoint==bar(2).observed_at
        second=backfill_alpha_vantage_daily(warehouse,[bar(1),bar(2),bar(3)],ingested_at=received,after=first.checkpoint,batch_limit=2)
        assert second.processed==1;assert second.inserted==1;assert second.checkpoint==bar(3).observed_at
        assert len(warehouse.history("NVDA"))==3
    engine.dispose()


def test_replay_is_idempotent(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'replay.db'}");Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db);backfill_alpha_vantage_daily(warehouse,[bar(1)],ingested_at=BASE+timedelta(days=10))
        replay=backfill_alpha_vantage_daily(warehouse,[bar(1)],ingested_at=BASE+timedelta(days=11))
        assert replay.inserted==0;assert replay.existing==1;assert len(warehouse.history("NVDA"))==1
    engine.dispose()


def test_backfill_rejects_unbounded_configuration(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'limit.db'}");Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        with pytest.raises(ValueError,match="batch_limit"):
            backfill_alpha_vantage_daily(MarketWarehouse(db),[bar(1)],batch_limit=5001)
    engine.dispose()
