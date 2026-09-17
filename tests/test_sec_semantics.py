from datetime import datetime, timezone

import pytest

from sentinel_alpha.evidence_roles import EvidenceRole
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.sec_semantics import (
    SEC_SEMANTIC_RULE_VERSION,
    EightKEvent,
    EightKEventKind,
    Form4Transaction,
    Form4TransactionKind,
    classify_8k,
    classify_form4,
)

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)
SEC = SourceIdentity("sec-filings", "SEC", "filing", "sec")


def sec_record(metric="insider_filing"):
    return normalize_record(
        asset="NVDA",
        metric=metric,
        value="filing",
        source=SEC,
        observed_at=NOW,
        statement="SEC filing",
        reference="https://www.sec.gov/example",
    )


def test_rule_is_versioned():
    assert SEC_SEMANTIC_RULE_VERSION == "sec-v1"


def test_form4_sale_is_warning_only():
    item = classify_form4(sec_record(), Form4Transaction(Form4TransactionKind.SALE, "S"))
    assert item.role is EvidenceRole.WARNING
    assert "sale" in item.rationale


def test_form4_purchase_is_context_until_calibrated_support_rule_exists():
    item = classify_form4(sec_record(), Form4Transaction(Form4TransactionKind.PURCHASE, "P"))
    assert item.role is EvidenceRole.CONTEXT


def test_form4_award_is_context():
    item = classify_form4(sec_record(), Form4Transaction(Form4TransactionKind.AWARD, "A"))
    assert item.role is EvidenceRole.CONTEXT


def test_negative_8k_event_is_conflict():
    item = classify_8k(sec_record("material_filing"), EightKEvent(EightKEventKind.NEGATIVE, "2.04"))
    assert item.role is EvidenceRole.CONFLICT


def test_positive_8k_event_does_not_become_support_without_event_rule():
    item = classify_8k(sec_record("material_filing"), EightKEvent(EightKEventKind.POSITIVE, "8.01"))
    assert item.role is EvidenceRole.CONTEXT


def test_unknown_8k_event_fails_closed_to_context():
    item = classify_8k(sec_record("material_filing"), EightKEvent(EightKEventKind.UNKNOWN, "unknown"))
    assert item.role is EvidenceRole.CONTEXT


def test_non_sec_evidence_is_rejected():
    other = normalize_record(
        asset="NVDA",
        metric="daily_close",
        value=100,
        source=SourceIdentity("market", "Market", "api", "market"),
        observed_at=NOW,
        statement="market",
    )
    with pytest.raises(ValueError):
        classify_form4(other, Form4Transaction(Form4TransactionKind.SALE, "S"))
