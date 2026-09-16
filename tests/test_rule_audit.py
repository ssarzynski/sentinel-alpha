from datetime import datetime, timezone

from app.models import Evidence
from app.scoring.rules import evaluate_rule
from app.services.rule_audit import independent_confirmation_count, persist_rule_evaluation


def evidence(source_family: str, category: str, record: str) -> Evidence:
    return Evidence(
        id=abs(hash((source_family, category, record))) % 100000,
        evidence_key=f"{source_family}:{record}",
        asset="NVDA",
        category=category,
        source=source_family,
        source_family=source_family,
        source_record_id=record,
        title=record,
        source_url=f"https://example.test/{record}",
        observed_at=datetime.now(timezone.utc),
        payload_json={},
    )


def test_duplicate_reporting_does_not_inflate_confirmation():
    items = [
        evidence("SEC_EDGAR", "fundamental", "8k-1"),
        evidence("SEC_EDGAR", "fundamental", "8k-2"),
        evidence("MARKET_DATA", "technical", "bars-1"),
    ]
    assert independent_confirmation_count(items) == 2


def test_same_family_can_confirm_distinct_evidence_categories():
    items = [
        evidence("PRIMARY_SOURCE", "fundamental", "earnings"),
        evidence("PRIMARY_SOURCE", "insider", "form4"),
    ]
    assert independent_confirmation_count(items) == 2


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, row):
        self.added.append(row)

    def flush(self):
        return None


def test_persist_rule_evaluation_snapshots_inputs_and_result():
    rule = {
        "id": "confirmation-test",
        "version": "1",
        "enabled": True,
        "conditions": [{"field": "confirmations", "operator": "gte", "value": 2}],
        "output": {"signal": "watch"},
    }
    facts = {"confirmations": 2}
    result = evaluate_rule(rule, facts)
    items = [
        evidence("SEC_EDGAR", "fundamental", "8k"),
        evidence("MARKET_DATA", "technical", "bars"),
    ]
    db = FakeSession()

    row = persist_rule_evaluation(db, result=result, facts=facts, evidence=items, asset="NVDA")

    assert row.rule_id == "confirmation-test"
    assert row.rule_version == "1"
    assert row.passed is True
    assert row.independent_confirmation_count == 2
    assert row.facts_json == {"confirmations": 2}
    assert len(row.conditions_json) == 1
    assert row.human_review_required is True
    assert db.added == [row]
