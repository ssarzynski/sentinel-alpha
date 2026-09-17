import pytest

from app.services.research_journal import create_research_entry, create_research_version


class FakeSession:
    def __init__(self, latest=None): self.latest = latest; self.added = []
    def add(self, row): self.added.append(row)
    def flush(self): return None
    def scalar(self, _query): return self.latest


def new_entry(db=None):
    db = db or FakeSession()
    return create_research_entry(
        db, title="Two-session earnings confirmation",
        hypothesis="Holding a breakout for two sessions reduces false positives.",
        rationale="One-session confirmation reversed in observed cases.",
        methodology={"horizons": [1, 5, 30, 90], "baseline": "one-session"},
        evidence_ids=[2, 1, 2], prediction_ids=[8, 7, 8],
    )


def test_new_research_starts_proposed_and_cannot_authorize_rules():
    db = FakeSession(); row = new_entry(db)
    assert row.version == 1
    assert row.status == "proposed"
    assert row.decision is None
    assert row.production_rule_change_authorized is False
    assert row.linked_evidence_ids_json == [1, 2]
    assert db.added == [row]


def test_research_updates_create_new_version_not_mutation():
    prior = new_entry()
    db = FakeSession(latest=1)
    row = create_research_version(
        db, prior=prior, status="completed",
        metrics={"accuracy": 0.61}, results={"beats_baseline": True},
        limitations=["small sample"], decision="accepted",
    )
    assert row.research_key == prior.research_key
    assert row.version == 2
    assert prior.status == "proposed"
    assert row.status == "completed"
    assert row.production_rule_change_authorized is False


def test_decision_requires_completed_research():
    prior = new_entry()
    with pytest.raises(ValueError, match="requires completed"):
        create_research_version(
            FakeSession(), prior=prior, status="testing", metrics={}, results={},
            limitations=[], decision="accepted",
        )


def test_invalid_status_and_decision_are_rejected():
    prior = new_entry()
    with pytest.raises(ValueError, match="unsupported research status"):
        create_research_version(FakeSession(), prior=prior, status="production", metrics={}, results={}, limitations=[])
    with pytest.raises(ValueError, match="unsupported research decision"):
        create_research_version(FakeSession(), prior=prior, status="completed", metrics={}, results={}, limitations=[], decision="auto_promote")
