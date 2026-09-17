from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from app.models import Prediction, PredictionOutcome


@dataclass(frozen=True)
class AccuracySummary:
    sample_size: int
    accuracy: float
    average_return: float
    average_excess_return: float | None
    false_positive_rate: float


@dataclass(frozen=True)
class CalibrationSummary:
    bucket_low: float
    bucket_high: float
    sample_size: int
    mean_confidence: float
    observed_accuracy: float
    calibration_error: float


def summarize_outcomes(outcomes: list[PredictionOutcome]) -> AccuracySummary:
    if not outcomes:
        raise ValueError("at least one outcome is required")
    correct = sum(1 for row in outcomes if row.direction_correct)
    excess = [row.excess_return for row in outcomes if row.excess_return is not None]
    return AccuracySummary(
        sample_size=len(outcomes),
        accuracy=correct / len(outcomes),
        average_return=mean(row.asset_return for row in outcomes),
        average_excess_return=mean(excess) if excess else None,
        false_positive_rate=(len(outcomes) - correct) / len(outcomes),
    )


def confidence_bucket(confidence: float, width: float = 0.1) -> tuple[float, float]:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if not 0.0 < width <= 1.0:
        raise ValueError("bucket width must be between 0 and 1")
    index = min(int(confidence / width), int(1.0 / width) - 1)
    low = round(index * width, 10)
    high = round(min(1.0, low + width), 10)
    return low, high


def calibration_summary(
    prediction_outcomes: list[tuple[Prediction, PredictionOutcome]],
    *,
    width: float = 0.1,
) -> list[CalibrationSummary]:
    if not prediction_outcomes:
        return []
    grouped: dict[tuple[float, float], list[tuple[Prediction, PredictionOutcome]]] = {}
    for prediction, outcome in prediction_outcomes:
        bucket = confidence_bucket(prediction.confidence, width)
        grouped.setdefault(bucket, []).append((prediction, outcome))

    summaries = []
    for (low, high), rows in sorted(grouped.items()):
        mean_confidence = mean(prediction.confidence for prediction, _ in rows)
        observed_accuracy = mean(1.0 if outcome.direction_correct else 0.0 for _, outcome in rows)
        summaries.append(
            CalibrationSummary(
                bucket_low=low,
                bucket_high=high,
                sample_size=len(rows),
                mean_confidence=mean_confidence,
                observed_accuracy=observed_accuracy,
                calibration_error=observed_accuracy - mean_confidence,
            )
        )
    return summaries


def filter_horizon(outcomes: list[PredictionOutcome], horizon_days: int) -> list[PredictionOutcome]:
    if horizon_days not in {1, 5, 30, 90}:
        raise ValueError(f"unsupported horizon: {horizon_days}")
    return [row for row in outcomes if row.horizon_days == horizon_days]
