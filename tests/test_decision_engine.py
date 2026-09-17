from datetime import datetime, timezone

from sentinel_alpha.decision_engine import evaluate_signal
from sentinel_alpha.models import Evidence, Signal


def test_two_independent_confirmations_allow_strong_alert():
    signal = Signal(asset="NVDA", status="confirmed", confirmations=["sec", "finviz"])
    decision = evaluate_signal(signal)
    assert decision.strong_alert is True
    assert decision.blocked is False
    assert decision.confirmation_count == 2
    assert decision.requires_human_approval is True


def test_duplicate_source_does_not_count_twice():
    signal = Signal(asset="BTC", status="confirmed", confirmations=["messari", "messari"])
    decision = evaluate_signal(signal)
    assert decision.strong_alert is False
    assert decision.blocked is True
    assert decision.confirmation_count == 1


def test_conflict_blocks_escalation_even_with_confirmations():
    evidence = Evidence(
        source="sec",
        statement="Example evidence",
        observed_at=datetime.now(timezone.utc),
    )
    signal = Signal(
        asset="NVDA",
        status="confirmed",
        confirmations=["sec", "finviz"],
        conflicts=["material_source_conflict"],
        evidence=[evidence],
    )
    decision = evaluate_signal(signal)
    assert decision.strong_alert is False
    assert decision.blocked is True
    assert "conflicting_evidence" in decision.reasons
