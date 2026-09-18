from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_backfill import backfill_alpha_vantage_daily
from sentinel_alpha.market_models import MarketBackfillRun
from sentinel_alpha.market_warehouse import MarketWarehouse

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def bar(day: int, symbol: str = "NVDA") -> DailyEquityBar:
    return DailyEquityBar(
        symbol=symbol,
        observed_at=BASE + timedelta(days=day),
        open=100 + day,
        high=102 + day,
        low=99 + day,
        close=101 + day,
        volume=1000 + day,
    )


def test_durable_checkpoint_survives_new_session_and_resumes(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'restart.db'}")
    Base.metadata.create_all(engine)
    received = datetime(2026, 9, 18, tzinfo=timezone.utc)

    with session_scope(engine) as db:
        result = backfill_alpha_vantage_daily(
            MarketWarehouse(db),
            [bar(1), bar(2), bar(3)],
            ingested_at=received,
            batch_limit=2,
            persist_progress=True,
        )
        assert result.processed == 2
        assert result.checkpoint == bar(2).observed_at

    # A fresh transaction simulates a process/server restart.
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db)
        result = backfill_alpha_vantage_daily(
            warehouse,
            [bar(1), bar(2), bar(3), bar(4)],
            ingested_at=received + timedelta(hours=1),
            batch_limit=2,
            persist_progress=True,
        )
        assert result.processed == 2
        assert result.inserted == 2
        assert result.checkpoint == bar(4).observed_at
        assert [row.source_record_id for row in warehouse.history("NVDA")] == [
            "NVDA:2020-01-02:daily-close",
            "NVDA:2020-01-03:daily-close",
            "NVDA:2020-01-04:daily-close",
            "NVDA:2020-01-05:daily-close",
        ]
        run = db.scalar(select(MarketBackfillRun))
        assert run.processed == 4
        assert run.inserted == 4
        assert run.existing == 0
        assert run.checkpoint_at.replace(tzinfo=timezone.utc) == bar(4).observed_at

    engine.dispose()


def test_mixed_symbol_batch_is_rejected_without_progress(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'mixed.db'}")
    Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        with pytest.raises(ValueError, match="exactly one symbol"):
            backfill_alpha_vantage_daily(
                MarketWarehouse(db), [bar(1), bar(2, "AAPL")], persist_progress=True
            )
        assert db.scalar(select(MarketBackfillRun)) is None
    engine.dispose()
