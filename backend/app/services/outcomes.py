from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Prediction, PredictionOutcome

SUPPORTED_HORIZONS = {1, 5, 30, 90}


def target_time(prediction: Prediction, horizon_days: int) -> datetime:
    if horizon_days not in SUPPORTED_HORIZONS:
        raise ValueError(f"unsupported horizon: {horizon_days}")
    return prediction.reference_time + timedelta(days=horizon_days)


def _direction_correct(direction: str, asset_return: float) -> bool:
    if direction == "bullish":
        return asset_return > 0
    if direction == "bearish":
        return asset_return < 0
    if direction == "neutral":
        return asset_return == 0
    raise ValueError(f"unsupported prediction direction: {direction}")


def record_outcome(
    db: Session,
    *,
    prediction: Prediction,
    horizon_days: int,
    observed_time: datetime,
    observed_price: float,
    price_source: str,
    source_record_id: str,
    benchmark_asset: str | None = None,
    benchmark_reference_price: float | None = None,
    benchmark_observed_price: float | None = None,
) -> PredictionOutcome:
    if prediction.id is None:
        raise ValueError("prediction must be persisted before recording outcomes")
    due = target_time(prediction, horizon_days)
    if observed_time.tzinfo is None:
        raise ValueError("observed_time must be timezone-aware")
    if observed_time < due:
        raise ValueError("cannot record an outcome before its target horizon")
    if observed_price <= 0:
        raise ValueError("observed_price must be positive")
    if not price_source.strip() or not source_record_id.strip():
        raise ValueError("outcome requires price source provenance")

    existing = db.scalar(
        select(PredictionOutcome).where(
            PredictionOutcome.prediction_id == prediction.id,
            PredictionOutcome.horizon_days == horizon_days,
        )
    )
    if existing:
        return existing

    asset_return = observed_price / prediction.reference_price - 1.0
    benchmark_return = None
    excess_return = None
    if benchmark_asset is not None:
        if not benchmark_reference_price or not benchmark_observed_price:
            raise ValueError("benchmark prices are required when benchmark_asset is supplied")
        benchmark_return = benchmark_observed_price / benchmark_reference_price - 1.0
        excess_return = asset_return - benchmark_return

    row = PredictionOutcome(
        prediction_id=prediction.id,
        horizon_days=horizon_days,
        target_time=due,
        observed_time=observed_time,
        observed_price=observed_price,
        asset_return=asset_return,
        benchmark_asset=benchmark_asset.upper() if benchmark_asset else None,
        benchmark_reference_price=benchmark_reference_price,
        benchmark_observed_price=benchmark_observed_price,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
        direction_correct=_direction_correct(prediction.direction, asset_return),
        price_source=price_source,
        source_record_id=source_record_id,
    )
    db.add(row)
    db.flush()
    return row
