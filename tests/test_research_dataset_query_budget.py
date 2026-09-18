"""Performance guardrail for research dataset construction.

The target architecture should construct a dataset from a bounded history
snapshot rather than issuing queries proportional to the number of anchors.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import event

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput
from sentinel_alpha.research_dataset import build_research_dataset

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def test_dataset_query_count_is_bounded(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'budget.db'}")
    Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db)
        for day in range(1, 31):
            moment = BASE + timedelta(days=day)
            warehouse.ingest(ObservationInput(
                symbol="NVDA", asset_type="equity", provider="TEST",
                source_family="MARKET", channel="daily", observed_at=moment,
                ingested_at=moment, price=100 + day,
                source_record_id=f"NVDA:{day}", metadata={"volume": 1000 + day},
            ))

    statements = 0
    def count_queries(*_args):
        nonlocal statements
        statements += 1

    event.listen(engine, "before_cursor_execute", count_queries)
    try:
        with session_scope(engine) as db:
            dataset = build_research_dataset(
                MarketWarehouse(db), "NVDA",
                dataset_known_by=BASE + timedelta(days=60),
                horizons=(1, 5), min_history=6,
            )
            assert len(dataset.examples) == 25
    finally:
        event.remove(engine, "before_cursor_execute", count_queries)
        engine.dispose()

    # Snapshot-based construction should remain essentially constant-query.
    assert statements <= 5, f"dataset construction issued {statements} SQL statements"
