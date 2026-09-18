from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput
from sentinel_alpha.research_examples import build_research_example

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def add(warehouse, day, price, ingested_day=None):
    warehouse.ingest(ObservationInput(
        symbol="NVDA", asset_type="equity", provider="TEST", source_family="MARKET",
        channel="daily", observed_at=BASE + timedelta(days=day),
        ingested_at=BASE + timedelta(days=ingested_day if ingested_day is not None else day),
        price=price, source_record_id=f"NVDA:{day}", metadata={"volume": 1000 + day},
    ))


def test_research_example_separates_feature_and_label_information(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'examples.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db)
        for day in range(1, 9): add(warehouse, day, 100 + day)
        example = build_research_example(
            warehouse, "nvda", anchor_at=BASE + timedelta(days=5),
            feature_known_by=BASE + timedelta(days=5),
            dataset_known_by=BASE + timedelta(days=20), horizons=(1, 3),
        )
        assert example.features.price == 105
        assert example.features.observations == 5
        assert example.outcomes[0].forward_return == pytest.approx(106 / 105 - 1)
        assert example.outcomes[1].forward_return == pytest.approx(108 / 105 - 1)
    engine.dispose()


def test_future_observation_cannot_enter_feature_vector(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'leak.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db)
        for day in range(1, 7): add(warehouse, day, 100 + day)
        example = build_research_example(
            warehouse, "NVDA", anchor_at=BASE + timedelta(days=5),
            feature_known_by=BASE + timedelta(days=5),
            dataset_known_by=BASE + timedelta(days=10), horizons=(1,),
        )
        assert example.features.price == 105
        assert example.outcomes[0].outcome_price == 106
    engine.dispose()


def test_anchor_must_match_latest_information_at_feature_time(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'anchor.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db); add(warehouse, 1, 101); add(warehouse, 2, 102)
        with pytest.raises(ValueError, match="latest observation"):
            build_research_example(
                warehouse, "NVDA", anchor_at=BASE + timedelta(days=1),
                feature_known_by=BASE + timedelta(days=2), dataset_known_by=BASE + timedelta(days=3),
            )
    engine.dispose()
