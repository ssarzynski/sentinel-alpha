from datetime import datetime, timezone

import pytest

from sentinel_alpha.btc_slice import BTC, BtcEvidenceBundle, evaluate_btc_candidate
from sentinel_alpha.evidence_roles import ClassifiedEvidence, EvidenceRole
from sentinel_alpha.provenance import SourceIdentity, normalize_record

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def record(provider: str = "Messari", source_id: str = "messari", asset: str = BTC):
    return normalize_record(
        asset=asset,
        metric="price_return_1h",
        value={"return_pct": 3.0},
        source=SourceIdentity(source_id, provider, "fixture"),
        observed_at=NOW,
        statement=f"BTC observation from {provider}",
    )


def test_raw_btc_market_data_does_not_create_confirmation():
    result = evaluate_btc_candidate(
        BtcEvidenceBundle((record(),)),
        stop_loss_defined=True,
        new_entries_this_week=0,
    )
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False
    assert result.risk.blocked is True
    assert result.risk.requires_human_approval is True


def test_one_provider_cannot_manufacture_two_confirmations():
    first = record()
    second = record(source_id="messari")
    support = (
        ClassifiedEvidence(first, EvidenceRole.SUPPORT, "test semantic support"),
        ClassifiedEvidence(second, EvidenceRole.SUPPORT, "test semantic support"),
    )
    result = evaluate_btc_candidate(
        BtcEvidenceBundle((first, second), classified_evidence=support),
        stop_loss_defined=True,
        new_entries_this_week=0,
    )
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False


def test_btc_candidate_requires_stop_loss():
    result = evaluate_btc_candidate(
        BtcEvidenceBundle((record(),)),
        stop_loss_defined=False,
        new_entries_this_week=0,
    )
    assert "risk_control_required_before_entry" in result.risk.reasons


def test_weekly_entry_cap_applies_to_btc():
    result = evaluate_btc_candidate(
        BtcEvidenceBundle((record(),)),
        stop_loss_defined=True,
        new_entries_this_week=2,
    )
    assert "weekly_entry_limit_reached" in result.risk.reasons


def test_non_btc_evidence_fails_closed():
    with pytest.raises(ValueError, match="non-BTC evidence"):
        evaluate_btc_candidate(
            BtcEvidenceBundle((record(asset="ETH"),)),
            stop_loss_defined=True,
            new_entries_this_week=0,
        )
