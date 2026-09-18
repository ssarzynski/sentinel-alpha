from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_outcomes import label_forward_outcomes
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def add(warehouse, day, price, ingested_day=None):
    warehouse.ingest(ObservationInput(
        symbol="NVDA", asset_type="equity", provider="TEST", source_family="MARKET",
        channel="daily", observed_at=BASE + timedelta(days=day),
        ingested_at=BASE + timedelta(days=ingested_day if ingested_day is not None else day),
        price=price, source_record_id=f"NVDA:{day}", metadata={},
    ))


def test_labels_forward_returns_by_observation_horizon(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'outcomes.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        for day in range(1, 8): add(warehouse, day, 100 + day)
        outcomes=label_forward_outcomes(warehouse,"nvda",anchor_at=BASE+timedelta(days=1),horizons=(1,5,10),dataset_known_by=BASE+timedelta(days=20))
        assert outcomes[0].forward_return == pytest.approx(102/101-1)
        assert outcomes[1].forward_return == pytest.approx(106/101-1)
        assert outcomes[2].forward_return is None
        assert outcomes[2].outcome_at is None
    engine.dispose()


def test_late_backfill_is_excluded_by_dataset_provenance_cutoff(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'cutoff.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        add(warehouse,1,100); add(warehouse,2,110)
        add(warehouse,3,999,ingested_day=1000)
        outcome=label_forward_outcomes(warehouse,"NVDA",anchor_at=BASE+timedelta(days=1),horizons=(2,),dataset_known_by=BASE+timedelta(days=10))[0]
        assert outcome.forward_return is None
    engine.dispose()


def test_anchor_must_exist_in_available_dataset(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'anchor.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db); add(warehouse,1,100,ingested_day=100)
        with pytest.raises(ValueError,match="anchor observation"):
            label_forward_outcomes(warehouse,"NVDA",anchor_at=BASE+timedelta(days=1),dataset_known_by=BASE+timedelta(days=2))
    engine.dispose()
