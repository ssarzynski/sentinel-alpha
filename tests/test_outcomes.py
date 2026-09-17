from datetime import datetime, timedelta, timezone

import pytest

from app.models import Prediction
from app.services.outcomes import record_outcome, target_time


class FakeSession:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
    def scalar(self, _query): return self.existing
    def add(self, row): self.added.append(row)
    def flush(self): return None


def prediction(direction="bullish"):
    return Prediction(
        id=11,
        prediction_key="prediction-1",
        asset="NVDA",
        direction=direction,
        confidence=0.75,
        reference_price=100.0,
        reference_time=datetime(2026, 9, 1, 14, 30, tzinfo=timezone.utc),
        market_regime="cautious",
        rule_evaluation_ids_json=[7], evidence_ids_json=[1, 2],
        human_review_status="pending", thesis_json={},
    )


def test_supported_horizons_are_exact():
    p = prediction()
    assert target_time(p, 1) == p.reference_time + timedelta(days=1)
    assert target_time(p, 90) == p.reference_time + timedelta(days=90)
    with pytest.raises(ValueError, match="unsupported horizon"):
        target_time(p, 7)


def test_records_bullish_outcome_with_benchmark_excess_return():
    p = prediction("bullish")
    db = FakeSession()
    row = record_outcome(
        db, prediction=p, horizon_days=5,
        observed_time=target_time(p, 5), observed_price=110.0,
        price_source="PRIMARY_MARKET_DATA", source_record_id="nvda-5d-close",
        benchmark_asset="SPY", benchmark_reference_price=500.0,
        benchmark_observed_price=510.0,
    )
    assert row.asset_return == pytest.approx(0.10)
    assert row.benchmark_return == pytest.approx(0.02)
    assert row.excess_return == pytest.approx(0.08)
    assert row.direction_correct is True
    assert db.added == [row]


def test_bearish_direction_is_scored_correctly():
    p = prediction("bearish")
    row = record_outcome(
        FakeSession(), prediction=p, horizon_days=1,
        observed_time=target_time(p, 1), observed_price=95.0,
        price_source="PRIMARY_MARKET_DATA", source_record_id="nvda-1d-close",
    )
    assert row.direction_correct is True


def test_future_horizon_cannot_be_filled_early():
    p = prediction()
    with pytest.raises(ValueError, match="before its target horizon"):
        record_outcome(
            FakeSession(), prediction=p, horizon_days=30,
            observed_time=p.reference_time + timedelta(days=29), observed_price=105.0,
            price_source="PRIMARY_MARKET_DATA", source_record_id="early",
        )


def test_existing_outcome_is_idempotent():
    existing = object()
    p = prediction()
    result = record_outcome(
        FakeSession(existing=existing), prediction=p, horizon_days=1,
        observed_time=target_time(p, 1), observed_price=101.0,
        price_source="PRIMARY_MARKET_DATA", source_record_id="same",
    )
    assert result is existing
