from datetime import datetime, timedelta, timezone

from sentinel_alpha.evidence_store import EvidenceStore
from sentinel_alpha.ingestion_pipeline import EvaluationPolicy, IngestionEvaluationBridge
from sentinel_alpha.providers import MESSARI_RESEARCH, SEC_FILINGS


def record(provider, asset, metric, when, reference):
    return provider.normalize(
        {
            "asset": asset,
            "metric": metric,
            "value": 1,
            "statement": f"{provider.source.provider} evidence",
            "reference": reference,
            "quality": "high",
        },
        when,
    )


def test_bridge_correlates_independent_sources_across_cycles(tmp_path):
    now = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)
    store = EvidenceStore(tmp_path / "evidence.db")
    bridge = IngestionEvaluationBridge(
        EvaluationPolicy(stop_loss_defined=True, evidence_window_hours=24),
        evidence_store=store,
        clock=lambda: now,
    )

    first = bridge.process([record(SEC_FILINGS, "BTC", "filing_event", now - timedelta(hours=2), "sec:1")])
    assert first[0].decision.confirmation_count == 1
    assert first[0].decision.strong_alert is False

    second = bridge.process([record(MESSARI_RESEARCH, "BTC", "price_reaction", now, "messari:1")])
    assert second[0].decision.confirmation_count == 2
    assert second[0].decision.strong_alert is True
    assert second[0].risk.requires_human_approval is True


def test_bridge_excludes_stale_evidence(tmp_path):
    now = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)
    store = EvidenceStore(tmp_path / "evidence.db")
    bridge = IngestionEvaluationBridge(
        EvaluationPolicy(stop_loss_defined=True, evidence_window_hours=24),
        evidence_store=store,
        clock=lambda: now,
    )

    bridge.process([record(SEC_FILINGS, "ETH", "filing_event", now - timedelta(hours=25), "sec:old")])
    result = bridge.process([record(MESSARI_RESEARCH, "ETH", "price_reaction", now, "messari:new")])[0]
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False


def test_same_provider_across_cycles_counts_once(tmp_path):
    now = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)
    store = EvidenceStore(tmp_path / "evidence.db")
    bridge = IngestionEvaluationBridge(
        EvaluationPolicy(stop_loss_defined=True),
        evidence_store=store,
        clock=lambda: now,
    )

    bridge.process([record(MESSARI_RESEARCH, "BTC", "metric_a", now - timedelta(hours=1), "messari:a")])
    result = bridge.process([record(MESSARI_RESEARCH, "BTC", "metric_b", now, "messari:b")])[0]
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False


def test_bridge_without_store_preserves_existing_single_cycle_behavior():
    now = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)
    bridge = IngestionEvaluationBridge(EvaluationPolicy(stop_loss_defined=True))
    result = bridge.process(
        [
            record(SEC_FILINGS, "BTC", "filing_event", now, "sec:1"),
            record(MESSARI_RESEARCH, "BTC", "price_reaction", now, "messari:1"),
        ]
    )[0]
    assert result.decision.confirmation_count == 2
    assert result.risk.requires_human_approval is True
