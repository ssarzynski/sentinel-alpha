from datetime import datetime, timedelta, timezone

import pytest

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_features import extract_market_features
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput

BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


def add(warehouse, day, price, volume, ingested_day=None):
    observed = BASE + timedelta(days=day)
    ingested = BASE + timedelta(days=ingested_day if ingested_day is not None else day)
    warehouse.ingest(ObservationInput(
        symbol="NVDA", asset_type="equity", provider="TEST", source_family="MARKET",
        channel="daily", observed_at=observed, ingested_at=ingested, price=price,
        source_record_id=f"NVDA:{day}", metadata={"volume": volume},
    ))


def test_features_use_only_information_known_at_decision_time(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'features.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db)
        for day, price in enumerate([100, 102, 101, 104, 106, 108], start=1):
            add(warehouse, day, price, 1000 + day * 100)
        # Historical-looking record arrived years later and must not contaminate this feature vector.
        add(warehouse, 0, 10000, 999999, ingested_day=1000)
        features = extract_market_features(warehouse, "nvda", known_by=BASE + timedelta(days=6))
        assert features.observations == 6
        assert features.price == 108
        assert features.return_1 == pytest.approx(108 / 106 - 1)
        assert features.return_5 == pytest.approx(108 / 100 - 1)
        assert features.trend_5 == pytest.approx(108 / ((102 + 101 + 104 + 106 + 108) / 5) - 1)
        assert features.volatility_5 is not None
        assert features.volume_change_1 == pytest.approx(1600 / 1500 - 1)
    engine.dispose()


def test_insufficient_history_returns_missing_features_not_invented_values(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'short.db'}"); Base.metadata.create_all(engine)
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db); add(warehouse, 1, 100, 1000)
        features = extract_market_features(warehouse, "NVDA", known_by=BASE + timedelta(days=1))
        assert features.price == 100
        assert features.return_1 is None
        assert features.return_5 is None
        assert features.volatility_5 is None
        assert features.volume_change_1 is None
    engine.dispose()
