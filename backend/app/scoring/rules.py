from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "in"}


@dataclass(frozen=True)
class ConditionResult:
    field: str
    operator: str
    expected: Any
    actual: Any
    passed: bool


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    version: str
    passed: bool
    conditions: tuple[ConditionResult, ...]
    output: dict[str, Any]


def load_rule(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        rule = yaml.safe_load(handle)
    validate_rule(rule)
    return rule


def validate_rule(rule: dict[str, Any]) -> None:
    required = {"id", "version", "enabled", "conditions", "output"}
    missing = required - set(rule)
    if missing:
        raise ValueError(f"Rule missing required fields: {sorted(missing)}")
    if not isinstance(rule["conditions"], list) or not rule["conditions"]:
        raise ValueError("Rule conditions must be a non-empty list")
    for condition in rule["conditions"]:
        if not {"field", "operator", "value"}.issubset(condition):
            raise ValueError("Each condition requires field, operator, and value")
        if condition["operator"] not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator: {condition['operator']}")


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq": return actual == expected
    if operator == "ne": return actual != expected
    if operator == "gt": return actual is not None and actual > expected
    if operator == "gte": return actual is not None and actual >= expected
    if operator == "lt": return actual is not None and actual < expected
    if operator == "lte": return actual is not None and actual <= expected
    if operator == "in": return actual in expected
    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_rule(rule: dict[str, Any], facts: dict[str, Any]) -> RuleResult:
    validate_rule(rule)
    if not rule["enabled"]:
        return RuleResult(rule["id"], str(rule["version"]), False, tuple(), rule["output"])

    results = tuple(
        ConditionResult(
            field=condition["field"],
            operator=condition["operator"],
            expected=condition["value"],
            actual=facts.get(condition["field"]),
            passed=_compare(facts.get(condition["field"]), condition["operator"], condition["value"]),
        )
        for condition in rule["conditions"]
    )
    return RuleResult(
        rule_id=rule["id"],
        version=str(rule["version"]),
        passed=all(result.passed for result in results),
        conditions=results,
        output=rule["output"],
    )
