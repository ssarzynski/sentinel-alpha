from datetime import datetime, timedelta, timezone

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput
from sentinel_alpha.research_dataset import build_research_dataset

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def add(warehouse, day, price):
    moment = BASE + timedelta(days=day)
    warehouse.ingest(ObservationInput(
        symbol="NVDA", asset_type="equity", provider="TEST", source_family="MARKET",
        channel="daily", observed_at=moment, ingested_at=moment, price=price,
        source_record_id=f"NVDA:{day}", metadata={"volume": 1000 + day},
    ))


def test_dataset_builds_multiple_time_separated_examples(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'dataset.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        for day in range(1, 11): add(warehouse, day, 100 + day)
        dataset=build_research_dataset(warehouse,"nvda",dataset_known_by=BASE+timedelta(days=20),horizons=(1,),min_history=3)
        assert dataset.symbol == "NVDA"
        assert len(dataset.examples) == 8
        assert dataset.skipped == 2
        assert dataset.examples[0].features.observations == 3
        assert dataset.examples[0].outcomes[0].forward_return is not None


def test_dataset_respects_hard_example_limit(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'limit.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        for day in range(1, 20): add(warehouse, day, 100 + day)
        dataset=build_research_dataset(warehouse,"NVDA",dataset_known_by=BASE+timedelta(days=30),horizons=(1,),min_history=2,max_examples=4)
        assert len(dataset.examples) == 4
    engine.dispose()
