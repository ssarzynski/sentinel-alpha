from datetime import datetime, timezone

from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole
from sentinel_alpha.ingestion_pipeline import EvaluationPolicy, IngestionEvaluationBridge
from sentinel_alpha.provenance import SourceIdentity, normalize_record


def record(asset: str, provider: str, channel: str):
    return normalize_record(asset=asset, metric="signal", value=True, source=SourceIdentity(f"{provider}-{channel}", provider, channel), observed_at=datetime.now(timezone.utc), statement="confirmation")


def support(*records):
    return [ClassifiedEvidence(item, EvidenceRole.SUPPORT, "test semantic support") for item in records]


def test_unclassified_record_cannot_become_strong_alert():
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True))
    result = bridge.process([record("NVDA", "SEC", "filings")])[0]
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False


def test_two_explicit_independent_support_sources_can_reach_review_stage():
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True))
    a, b = record("NVDA", "SEC", "filings"), record("NVDA", "Finviz", "screening")
    result = bridge.process_classified(support(a, b))[0]
    assert result.decision.confirmation_count == 2
    assert result.decision.strong_alert is True
    assert result.risk.eligible_for_review is True
    assert result.risk.requires_human_approval is True


def test_records_are_grouped_by_asset_before_evaluation():
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True))
    a = record("NVDA", "SEC", "filings")
    b = record("AAPL", "SEC", "filings")
    c = record("NVDA", "Finviz", "screening")
    results = bridge.process_classified(support(a, b, c))
    by_asset = {result.signal.asset: result for result in results}
    assert by_asset["NVDA"].decision.confirmation_count == 2
    assert by_asset["AAPL"].decision.confirmation_count == 1


def test_default_policy_keeps_risk_control_block_in_place():
    bridge = IngestionEvaluationBridge()
    a, b = record("NVDA", "SEC", "filings"), record("NVDA", "Finviz", "screening")
    result = bridge.process_classified(support(a, b))[0]
    assert result.decision.strong_alert is True
    assert result.risk.blocked is True
    assert "risk_control_required_before_entry" in result.risk.reasons


def test_results_can_be_forwarded_to_journal_or_alert_handler():
    captured = []
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True), on_result=captured.append)
    results = bridge.process([record("NVDA", "SEC", "filings")])
    assert captured == results
