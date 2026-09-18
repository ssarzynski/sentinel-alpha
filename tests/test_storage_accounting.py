from datetime import datetime, timezone

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput
from sentinel_alpha.resource_metrics import ResourceMetrics
from sentinel_alpha.storage_accounting import canonical_observation_bytes

NOW = datetime(2026, 9, 18, tzinfo=timezone.utc)


def item():
    return ObservationInput(
        symbol="NVDA", asset_type="equity", provider="TEST",
        source_family="MARKET", channel="daily", observed_at=NOW,
        ingested_at=NOW, price=180.25, source_record_id="NVDA:2026-09-18",
        metadata={"volume": 123456},
    )


def test_only_new_canonical_rows_add_logical_storage_bytes(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path/'storage.db'}")
    Base.metadata.create_all(engine)
    metrics = ResourceMetrics()
    with session_scope(engine) as db:
        warehouse = MarketWarehouse(db, metrics=metrics)
        observation = item()
        _, first_created = warehouse.ingest(observation)
        first_bytes = metrics.canonical_bytes_added
        _, second_created = warehouse.ingest(observation)
        assert first_created is True
        assert second_created is False
        assert first_bytes == canonical_observation_bytes(observation)
        assert metrics.canonical_bytes_added == first_bytes
    engine.dispose()


def test_storage_accounting_is_deterministic_and_positive():
    observation = item()
    assert canonical_observation_bytes(observation) > 0
    assert canonical_observation_bytes(observation) == canonical_observation_bytes(observation)
