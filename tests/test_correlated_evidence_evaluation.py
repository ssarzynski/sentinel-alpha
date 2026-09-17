from datetime import datetime, timedelta, timezone

from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole
from sentinel_alpha.evidence_store import EvidenceStore
from sentinel_alpha.ingestion_pipeline import EvaluationPolicy, IngestionEvaluationBridge
from sentinel_alpha.providers import MESSARI_RESEARCH, SEC_FILINGS


def record(provider, asset, metric, when, reference):
    return provider.normalize({"asset": asset, "metric": metric, "value": 1, "statement": f"{provider.source.provider} evidence", "reference": reference, "quality": "high"}, when)


def support(item):
    return ClassifiedEvidence(item, EvidenceRole.SUPPORT, "test semantic support")


def test_bridge_correlates_independent_support_across_cycles(tmp_path):
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True, evidence_window_hours=24), evidence_store=EvidenceStore(tmp_path / "evidence.db"), clock=lambda: now)
    sec = record(SEC_FILINGS, "BTC", "filing_event", now - timedelta(hours=2), "sec:1")
    first = bridge.process_classified([support(sec)])[0]
    assert first.decision.confirmation_count == 1
    messari = record(MESSARI_RESEARCH, "BTC", "price_reaction", now, "messari:1")
    second = bridge.process_classified([support(messari)])[0]
    assert second.decision.confirmation_count == 2
    assert second.decision.strong_alert is True
    assert second.risk.requires_human_approval is True


def test_bridge_excludes_stale_support(tmp_path):
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True, evidence_window_hours=24), evidence_store=EvidenceStore(tmp_path / "evidence.db"), clock=lambda: now)
    old = record(SEC_FILINGS, "ETH", "filing_event", now - timedelta(hours=25), "sec:old")
    bridge.process_classified([support(old)])
    fresh = record(MESSARI_RESEARCH, "ETH", "price_reaction", now, "messari:new")
    result = bridge.process_classified([support(fresh)])[0]
    assert result.decision.confirmation_count == 1


def test_same_provider_support_across_cycles_counts_once(tmp_path):
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True), evidence_store=EvidenceStore(tmp_path / "evidence.db"), clock=lambda: now)
    first = record(MESSARI_RESEARCH, "BTC", "metric_a", now - timedelta(hours=1), "messari:a")
    second = record(MESSARI_RESEARCH, "BTC", "metric_b", now, "messari:b")
    bridge.process_classified([support(first)])
    result = bridge.process_classified([support(second)])[0]
    assert result.decision.confirmation_count == 1


def test_unclassified_single_cycle_records_fail_closed():
    now = datetime(2026, 9, 17, 18, tzinfo=timezone.utc)
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True))
    result = bridge.process([record(SEC_FILINGS, "BTC", "filing_event", now, "sec:1"), record(MESSARI_RESEARCH, "BTC", "price_reaction", now, "messari:1")])[0]
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False
