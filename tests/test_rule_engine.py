from pathlib import Path

import pytest

from app.scoring.rules import evaluate_rule, load_rule, validate_rule


RULE_PATH = Path("rules/confirmation/minimum_independent_confirmations_v1.yaml")


def test_rule_loads_and_passes_with_two_confirmations():
    rule = load_rule(RULE_PATH)
    result = evaluate_rule(
        rule,
        {"independent_confirmation_count": 2, "human_review_required": True},
    )
    assert result.passed is True
    assert result.rule_id == "minimum_independent_confirmations"
    assert result.output["auto_trade"] is False
    assert all(condition.passed for condition in result.conditions)


def test_rule_fails_with_only_one_confirmation():
    rule = load_rule(RULE_PATH)
    result = evaluate_rule(
        rule,
        {"independent_confirmation_count": 1, "human_review_required": True},
    )
    assert result.passed is False
    assert result.conditions[0].passed is False


def test_rule_fails_when_human_review_gate_is_removed():
    rule = load_rule(RULE_PATH)
    result = evaluate_rule(
        rule,
        {"independent_confirmation_count": 3, "human_review_required": False},
    )
    assert result.passed is False
    assert result.conditions[1].passed is False


def test_invalid_operator_is_rejected():
    rule = {
        "id": "bad",
        "version": "1",
        "enabled": True,
        "conditions": [{"field": "x", "operator": "execute_trade", "value": True}],
        "output": {},
    }
    with pytest.raises(ValueError, match="Unsupported operator"):
        validate_rule(rule)
