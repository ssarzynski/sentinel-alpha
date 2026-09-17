from datetime import datetime, timezone

from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole, classify_sec_record
from sentinel_alpha.pipeline import evaluate_records
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.risk_gate import TradeProposal

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def record(provider: str, group: str, metric: str = "price"):
    return normalize_record(
        asset="NVDA",
        metric=metric,
        value="1",
        statement=f"{provider} observation",
        reference=f"https://example.test/{provider}",
        observed_at=NOW,
        source=SourceIdentity(provider, provider, "api", group),
    )


def run(records, classified):
    return evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=records,
        classified_evidence=classified,
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
    )


def classified(item, role, rationale=None):
    return ClassifiedEvidence(item, role, rationale or role.value)


def test_two_context_sources_cannot_create_strong_alert():
    a, b = record("a", "a"), record("b", "b")
    result = run([a, b], [classified(a, EvidenceRole.CONTEXT), classified(b, EvidenceRole.CONTEXT)])
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False


def test_one_support_plus_context_is_one_confirmation():
    a, b = record("a", "a"), record("b", "b")
    result = run([a, b], [classified(a, EvidenceRole.SUPPORT), classified(b, EvidenceRole.CONTEXT)])
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False


def test_two_independent_support_records_meet_confirmation_threshold():
    a, b = record("a", "a"), record("b", "b")
    result = run([a, b], [classified(a, EvidenceRole.SUPPORT), classified(b, EvidenceRole.SUPPORT)])
    assert result.decision.confirmation_count == 2
    assert result.decision.strong_alert is True
    assert result.decision.requires_human_approval is True


def test_warning_does_not_count_as_confirmation():
    a, b = record("a", "a"), record("b", "b")
    result = run([a, b], [classified(a, EvidenceRole.SUPPORT), classified(b, EvidenceRole.WARNING)])
    assert result.decision.confirmation_count == 1


def test_conflict_blocks_candidate():
    a, b = record("a", "a"), record("b", "b")
    result = run([a, b], [classified(a, EvidenceRole.SUPPORT), classified(b, EvidenceRole.CONFLICT, "bearish contradiction")])
    assert result.decision.blocked is True
    assert "bearish contradiction" in result.signal.conflicts


def test_unclassified_records_fail_closed():
    a, b = record("a", "a"), record("b", "b")
    result = evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=[a, b],
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
    )
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False


def test_raw_sec_filing_defaults_to_context_and_retains_provenance():
    sec = record("sec", "sec", metric="material_filing")
    item = classify_sec_record(sec)
    assert item.role is EvidenceRole.CONTEXT
    assert item.record is sec
    assert item.record.source.independence_key == "sec"
