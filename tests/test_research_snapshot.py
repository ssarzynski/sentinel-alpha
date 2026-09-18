from datetime import datetime, timedelta, timezone

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput
from sentinel_alpha.research_dataset import build_research_dataset
from sentinel_alpha.research_snapshot import build_research_dataset_snapshot

BASE=datetime(2020,1,1,tzinfo=timezone.utc)


def add(warehouse, day, price):
    moment=BASE+timedelta(days=day)
    warehouse.ingest(ObservationInput(symbol="NVDA",asset_type="equity",provider="TEST",source_family="MARKET",channel="daily",observed_at=moment,ingested_at=moment,price=price,source_record_id=f"NVDA:{day}",metadata={"volume":1000+day}))


def signature(dataset):
    return [(
        item.symbol,item.anchor_at,item.features.observations,item.features.price,
        item.features.return_1,item.features.return_5,item.features.volatility_5,
        item.features.volume_change_1,item.features.trend_5,
        tuple((o.horizon,o.outcome_price,o.forward_return) for o in item.outcomes),
    ) for item in dataset.examples]


def test_snapshot_builder_matches_reference_builder(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'equivalence.db'}");Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        for day,price in enumerate([100,102,101,104,106,108,107,111,113,112,116,118],start=1): add(warehouse,day,price)
        kwargs=dict(dataset_known_by=BASE+timedelta(days=30),horizons=(1,3,5),min_history=6,max_examples=100)
        reference=build_research_dataset(warehouse,"NVDA",**kwargs)
        snapshot=build_research_dataset_snapshot(warehouse,"NVDA",**kwargs)
        assert snapshot.skipped==reference.skipped
        assert signature(snapshot)==signature(reference)
    engine.dispose()


def test_snapshot_builder_respects_example_limit(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'bounded.db'}");Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        for day in range(1,25): add(warehouse,day,100+day)
        dataset=build_research_dataset_snapshot(warehouse,"NVDA",dataset_known_by=BASE+timedelta(days=40),horizons=(1,),min_history=2,max_examples=3)
        assert len(dataset.examples)==3
    engine.dispose()
