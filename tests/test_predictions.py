from datetime import datetime, timezone

import pytest

from app.models import RuleEvaluation
from app.services.predictions import create_prediction


class FakeSession:
    def __init__(self): self.added = []
    def add(self, row): self.added.append(row)
    def flush(self): return None


def evaluation(passed=True, human_review_required=True):
    return RuleEvaluation(
        id=7,
        evaluation_key="eval-1",
        rule_id="confirmation",
        rule_version="1",
        asset="NVDA",
        passed=passed,
        human_review_required=human_review_required,
        independent_confirmation_count=2,
        facts_json={}, conditions_json=[], output_json={},
        evidence_ids_json=[1, 2], evidence_categories_json=["fundamental", "technical"],
        source_families_json=["SEC", "MARKET"],
    )


def valid_kwargs():
    return dict(
        asset="nvda", direction="bullish", confidence=0.72,
        reference_price=200.0, reference_time=datetime.now(timezone.utc),
        rule_evaluations=[evaluation()], evidence_ids=[2, 1, 2],
        thesis={"summary": "test"}, market_regime="cautious",
    )


def test_prediction_is_created_pending_human_review():
    db = FakeSession()
    row = create_prediction(db, **valid_kwargs())
    assert row.asset == "NVDA"
    assert row.direction == "bullish"
    assert row.human_review_status == "pending"
    assert row.evidence_ids_json == [1, 2]
    assert row.rule_evaluation_ids_json == [7]
    assert db.added == [row]


def test_prediction_rejects_failed_rule():
    kwargs = valid_kwargs(); kwargs["rule_evaluations"] = [evaluation(passed=False)]
    with pytest.raises(ValueError, match="must have passed"):
        create_prediction(FakeSession(), **kwargs)


def test_prediction_rejects_missing_human_review_guardrail():
    kwargs = valid_kwargs(); kwargs["rule_evaluations"] = [evaluation(human_review_required=False)]
    with pytest.raises(ValueError, match="preserve human review"):
        create_prediction(FakeSession(), **kwargs)


def test_prediction_validates_confidence_price_and_timezone():
    for field, value, message in [
        ("confidence", 1.2, "confidence"),
        ("reference_price", 0, "reference_price"),
        ("reference_time", datetime.now(), "timezone-aware"),
    ]:
        kwargs = valid_kwargs(); kwargs[field] = value
        with pytest.raises(ValueError, match=message):
            create_prediction(FakeSession(), **kwargs)
