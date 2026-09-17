from datetime import datetime, timezone

import pytest

from sentinel_alpha.nvda_slice import NVDA_CIK, NvdaEvidenceBundle, evaluate_nvda_candidate
from sentinel_alpha.provenance import SourceIdentity, normalize_record

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def record(provider: str, source_id: str, asset: str = "NVDA"):
    return normalize_record(
        asset=asset,
        metric="signal",
        value=True,
        source=SourceIdentity(source_id, provider, "fixture"),
        observed_at=NOW,
        statement=f"NVDA confirmation from {provider}",
    )


def test_nvda_cik_is_explicit():
    assert NVDA_CIK == "0001045810"


def test_two_independent_nvda_sources_reach_human_review_only():
    result = evaluate_nvda_candidate(
        NvdaEvidenceBundle((record("SEC", "sec"), record("Finviz", "finviz"))),
        stop_loss_defined=True,
        new_entries_this_week=0,
    )
    assert result.decision.confirmation_count == 2
    assert result.decision.strong_alert is True
    assert result.risk.eligible_for_review is True
    assert result.risk.requires_human_approval is True


def test_one_nvda_source_cannot_become_strong_alert():
    result = evaluate_nvda_candidate(
        NvdaEvidenceBundle((record("SEC", "sec"),)),
        stop_loss_defined=True,
        new_entries_this_week=0,
    )
    assert result.decision.confirmation_count == 1
    assert result.decision.strong_alert is False
    assert result.risk.blocked is True


def test_nvda_candidate_requires_stop_loss_before_review():
    result = evaluate_nvda_candidate(
        NvdaEvidenceBundle((record("SEC", "sec"), record("Finviz", "finviz"))),
        stop_loss_defined=False,
        new_entries_this_week=0,
    )
    assert result.risk.blocked is True
    assert "risk_control_required_before_entry" in result.risk.reasons


def test_weekly_entry_cap_blocks_nvda_candidate():
    result = evaluate_nvda_candidate(
        NvdaEvidenceBundle((record("SEC", "sec"), record("Finviz", "finviz"))),
        stop_loss_defined=True,
        new_entries_this_week=2,
    )
    assert result.risk.blocked is True
    assert "weekly_entry_limit_reached" in result.risk.reasons


def test_non_nvda_evidence_fails_closed():
    with pytest.raises(ValueError, match="non-NVDA evidence"):
        evaluate_nvda_candidate(
            NvdaEvidenceBundle((record("SEC", "sec", asset="AMD"),)),
            stop_loss_defined=True,
            new_entries_this_week=0,
        )
