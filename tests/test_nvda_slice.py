from datetime import datetime, timezone

import pytest

from sentinel_alpha.evidence_roles import EvidenceRole
from sentinel_alpha.nvda_slice import (
    NVDA_CIK,
    NvdaEvidenceBundle,
    evaluate_nvda_candidate,
    load_nvda_sec_classified_evidence,
)
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.sec_ingestion import SecFiling

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def record(provider: str, source_id: str, asset: str = "NVDA"):
    return normalize_record(asset=asset, metric="signal", value=True, source=SourceIdentity(source_id, provider, "fixture"), observed_at=NOW, statement=f"NVDA observation from {provider}")


class FakeSecClient:
    def __init__(self, filing: SecFiling, document: str | Exception):
        self.filing = filing
        self.document = document

    def recent_watched_filings(self, cik):
        assert cik == NVDA_CIK
        return [self.filing]

    def fetch_filing_document(self, filing):
        assert filing is self.filing
        if isinstance(self.document, Exception):
            raise self.document
        return self.document


def filing(form: str, primary_document: str = "filing.htm") -> SecFiling:
    return SecFiling(
        cik=NVDA_CIK,
        accession_number="0001045810-26-000001",
        form=form,
        filing_date="2026-09-17",
        primary_document=primary_document,
        accepted_at="2026-09-17T12:00:00Z",
    )


def test_nvda_cik_is_explicit():
    assert NVDA_CIK == "0001045810"


def test_raw_independent_nvda_sources_do_not_create_confirmations():
    result = evaluate_nvda_candidate(NvdaEvidenceBundle((record("SEC", "sec"), record("Finviz", "finviz"))), stop_loss_defined=True, new_entries_this_week=0)
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False
    assert result.risk.blocked is True
    assert result.risk.requires_human_approval is True


def test_one_raw_nvda_source_cannot_become_strong_alert():
    result = evaluate_nvda_candidate(NvdaEvidenceBundle((record("SEC", "sec"),)), stop_loss_defined=True, new_entries_this_week=0)
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False


def test_nvda_candidate_requires_stop_loss_before_review():
    result = evaluate_nvda_candidate(NvdaEvidenceBundle((record("SEC", "sec"), record("Finviz", "finviz"))), stop_loss_defined=False, new_entries_this_week=0)
    assert result.risk.blocked is True
    assert "risk_control_required_before_entry" in result.risk.reasons


def test_weekly_entry_cap_blocks_nvda_candidate():
    result = evaluate_nvda_candidate(NvdaEvidenceBundle((record("SEC", "sec"), record("Finviz", "finviz"))), stop_loss_defined=True, new_entries_this_week=2)
    assert result.risk.blocked is True
    assert "weekly_entry_limit_reached" in result.risk.reasons


def test_non_nvda_evidence_fails_closed():
    with pytest.raises(ValueError, match="non-NVDA evidence"):
        evaluate_nvda_candidate(NvdaEvidenceBundle((record("SEC", "sec", asset="AMD"),)), stop_loss_defined=True, new_entries_this_week=0)


def test_form4_sale_flows_to_warning_without_confirmation():
    xml = "<ownershipDocument><nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode></transactionCoding></nonDerivativeTransaction></ownershipDocument>"
    records, classified = load_nvda_sec_classified_evidence(FakeSecClient(filing("4", "ownership.xml"), xml))
    assert [item.role for item in classified] == [EvidenceRole.WARNING]
    result = evaluate_nvda_candidate(NvdaEvidenceBundle(records, classified_evidence=classified), stop_loss_defined=True, new_entries_this_week=0)
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False


def test_item_only_8k_flows_to_context_without_confirmation_or_conflict():
    records, classified = load_nvda_sec_classified_evidence(FakeSecClient(filing("8-K"), "Item 4.02 Non-Reliance on Previously Issued Financial Statements"))
    assert [item.role for item in classified] == [EvidenceRole.CONTEXT]
    result = evaluate_nvda_candidate(NvdaEvidenceBundle(records, classified_evidence=classified), stop_loss_defined=True, new_entries_this_week=0)
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False
    assert not result.signal.conflicts


def test_sec_fetch_failure_falls_back_to_context():
    records, classified = load_nvda_sec_classified_evidence(FakeSecClient(filing("8-K"), OSError("network down")))
    assert [item.role for item in classified] == [EvidenceRole.CONTEXT]
    result = evaluate_nvda_candidate(NvdaEvidenceBundle(records, classified_evidence=classified), stop_loss_defined=True, new_entries_this_week=0)
    assert result.decision.confirmation_count == 0
    assert result.decision.strong_alert is False
