from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_models import MarketBackfillRun


def test_backfill_run_schema_and_defaults(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'runs.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with session_scope(engine) as db:
        run = MarketBackfillRun(
            provider="ALPHA_VANTAGE",
            symbol="NVDA",
            channel="daily",
            status="running",
            processed=0,
            inserted=0,
            existing=0,
            started_at=now,
            updated_at=now,
        )
        db.add(run)
    columns = {column["name"] for column in inspect(engine).get_columns("market_backfill_runs")}
    assert {"checkpoint_at", "processed", "inserted", "existing", "error_message"} <= columns
    engine.dispose()


def test_only_one_durable_run_exists_per_stream(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'unique.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        with session_scope(engine) as db:
            common = dict(
                provider="ALPHA_VANTAGE",
                symbol="NVDA",
                channel="daily",
                status="running",
                processed=0,
                inserted=0,
                existing=0,
                started_at=now,
                updated_at=now,
            )
            db.add_all([MarketBackfillRun(**common), MarketBackfillRun(**common)])
    engine.dispose()
