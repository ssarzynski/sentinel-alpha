from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Prediction, RuleEvaluation

ALLOWED_DIRECTIONS = {"bullish", "bearish", "neutral"}
ALLOWED_REVIEW_STATUSES = {"pending", "approved", "rejected"}


def create_prediction(
    db: Session,
    *,
    asset: str,
    direction: str,
    confidence: float,
    reference_price: float,
    reference_time: datetime,
    rule_evaluations: list[RuleEvaluation],
    evidence_ids: list[int],
    thesis: dict,
    market_regime: str | None = None,
) -> Prediction:
    direction = direction.lower()
    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError(f"Unsupported direction: {direction}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if reference_price <= 0:
        raise ValueError("reference_price must be positive")
    if reference_time.tzinfo is None:
        raise ValueError("reference_time must be timezone-aware")
    if not rule_evaluations:
        raise ValueError("prediction requires at least one rule evaluation")
    if not all(row.passed for row in rule_evaluations):
        raise ValueError("all linked rule evaluations must have passed")
    if not all(row.human_review_required for row in rule_evaluations):
        raise ValueError("linked rule evaluations must preserve human review")

    row = Prediction(
        prediction_key=str(uuid4()),
        asset=asset.upper(),
        direction=direction,
        confidence=confidence,
        reference_price=reference_price,
        reference_time=reference_time,
        market_regime=market_regime,
        rule_evaluation_ids_json=[item.id for item in rule_evaluations],
        evidence_ids_json=sorted(set(evidence_ids)),
        human_review_status="pending",
        thesis_json=dict(thesis),
    )
    db.add(row)
    db.flush()
    return row
