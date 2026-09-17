from datetime import datetime, timezone

import pytest

from app.models import Prediction, PredictionOutcome
from app.services.accuracy import calibration_summary, confidence_bucket, filter_horizon, summarize_outcomes


def prediction(key: str, confidence: float) -> Prediction:
    return Prediction(
        id=abs(hash(key)) % 100000,
        prediction_key=key,
        asset="NVDA",
        direction="bullish",
        confidence=confidence,
        reference_price=100.0,
        reference_time=datetime(2026, 9, 1, tzinfo=timezone.utc),
        rule_evaluation_ids_json=[1],
        evidence_ids_json=[1, 2],
        human_review_status="pending",
        thesis_json={},
    )


def outcome(pid: int, correct: bool, asset_return: float, excess_return=None, horizon=5) -> PredictionOutcome:
    return PredictionOutcome(
        prediction_id=pid,
        horizon_days=horizon,
        target_time=datetime(2026, 9, 6, tzinfo=timezone.utc),
        observed_time=datetime(2026, 9, 6, tzinfo=timezone.utc),
        observed_price=100.0 * (1 + asset_return),
        asset_return=asset_return,
        benchmark_asset="SPY" if excess_return is not None else None,
        benchmark_return=(asset_return - excess_return) if excess_return is not None else None,
        excess_return=excess_return,
        direction_correct=correct,
        price_source="TEST",
        source_record_id=f"outcome-{pid}",
    )


def test_accuracy_summary_calculates_core_metrics():
    rows = [outcome(1, True, 0.10, 0.08), outcome(2, False, -0.04, -0.05)]
    result = summarize_outcomes(rows)
    assert result.sample_size == 2
    assert result.accuracy == pytest.approx(0.5)
    assert result.average_return == pytest.approx(0.03)
    assert result.average_excess_return == pytest.approx(0.015)
    assert result.false_positive_rate == pytest.approx(0.5)


def test_calibration_groups_predictions_and_measures_error():
    p1, p2 = prediction("a", 0.72), prediction("b", 0.78)
    rows = [(p1, outcome(p1.id, True, 0.1)), (p2, outcome(p2.id, False, -0.1))]
    result = calibration_summary(rows)
    assert len(result) == 1
    assert result[0].bucket_low == pytest.approx(0.7)
    assert result[0].sample_size == 2
    assert result[0].mean_confidence == pytest.approx(0.75)
    assert result[0].observed_accuracy == pytest.approx(0.5)
    assert result[0].calibration_error == pytest.approx(-0.25)


def test_confidence_one_belongs_to_last_bucket():
    assert confidence_bucket(1.0) == pytest.approx((0.9, 1.0))


def test_horizon_filter_and_validation():
    rows = [outcome(1, True, 0.01, horizon=1), outcome(2, True, 0.02, horizon=5)]
    assert len(filter_horizon(rows, 1)) == 1
    with pytest.raises(ValueError, match="unsupported horizon"):
        filter_horizon(rows, 7)


def test_empty_summary_is_rejected_and_empty_calibration_is_safe():
    with pytest.raises(ValueError, match="at least one outcome"):
        summarize_outcomes([])
    assert calibration_summary([]) == []
