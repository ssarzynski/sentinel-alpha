from datetime import datetime, timedelta, timezone

from sentinel_alpha.database import Base, build_engine, session_scope
from sentinel_alpha.evidence_gate import EvidencePolicy
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput
from sentinel_alpha.research_pipeline import run_research_pipeline

BASE=datetime(2020,1,1,tzinfo=timezone.utc)


def ingest_series(warehouse, prices):
    for day, price in enumerate(prices, start=1):
        moment=BASE+timedelta(days=day)
        warehouse.ingest(ObservationInput(
            symbol="NVDA",asset_type="equity",provider="TEST",source_family="MARKET",channel="daily",
            observed_at=moment,ingested_at=moment,price=float(price),source_record_id=f"NVDA:{day}",
            metadata={"volume":1000+day},
        ))


def test_pipeline_runs_full_chain_and_reports_resources(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'pipeline.db'}"); Base.metadata.create_all(engine)
    # Smooth persistent growth gives a simple deterministic integration fixture.
    prices=[100*(1.01**day) for day in range(1,81)]
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        ingest_series(warehouse,prices)
        result=run_research_pipeline(
            warehouse,"nvda",hypothesis="positive five period trend",
            condition=lambda x: x.features.trend_5 is not None and x.features.trend_5>0,
            dataset_known_by=BASE+timedelta(days=100),horizons=(5,),min_history=6,
            min_train=30,test_size=10,
            policy=EvidencePolicy(min_test_folds=2,min_test_samples=10,min_direction_agreement=0.5,min_effect_retention=0.1),
        )
        assert result.symbol=="NVDA"
        assert result.examples>30
        assert result.folds>=2
        assert result.resources["sql_statements"]==1
        assert result.resources["provider_calls"]==0
        assert len(result.decisions)==1
        assert result.decisions[0].horizon==5
    engine.dispose()


def test_pipeline_fails_closed_when_condition_has_no_unseen_evidence(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'failure.db'}"); Base.metadata.create_all(engine)
    prices=[100+day for day in range(1,61)]
    with session_scope(engine) as db:
        warehouse=MarketWarehouse(db)
        ingest_series(warehouse,prices)
        result=run_research_pipeline(
            warehouse,"NVDA",hypothesis="impossible negative price condition",
            condition=lambda x: x.features.price<0,
            dataset_known_by=BASE+timedelta(days=80),horizons=(5,),min_history=6,min_train=25,test_size=10,
        )
        assert result.decisions[0].sufficient is False
        assert "too_few_test_samples" in result.decisions[0].reasons
        assert result.candidates[0].sufficient is False
    engine.dispose()
