from datetime import datetime, timezone

import pytest

from sentinel_alpha.evidence_roles import EvidenceRole
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.sec_parsed_evidence import classify_sec_document

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)
SEC = SourceIdentity("sec-filings", "SEC", "filing", "sec")


def record(metric: str) -> object:
    return normalize_record(
        asset="NVDA",
        metric=metric,
        value="filing",
        source=SEC,
        observed_at=NOW,
        statement="SEC filing",
    )


def assert_no_support(classified: tuple) -> None:
    assert all(item.role is not EvidenceRole.SUPPORT for item in classified)


def test_form4_sale_becomes_warning_and_not_support():
    xml = (
        "<ownershipDocument><nonDerivativeTransaction><transactionCoding>"
        "<transactionCode>S</transactionCode></transactionCoding>"
        "</nonDerivativeTransaction></ownershipDocument>"
    )
    classified = classify_sec_document(record("insider_filing"), form="4", document=xml)
    assert [item.role for item in classified] == [EvidenceRole.WARNING]
    assert_no_support(classified)


def test_form4_purchase_remains_context_and_not_support():
    xml = (
        "<ownershipDocument><nonDerivativeTransaction><transactionCoding>"
        "<transactionCode>P</transactionCode></transactionCoding>"
        "</nonDerivativeTransaction></ownershipDocument>"
    )
    classified = classify_sec_document(record("insider_filing"), form="4", document=xml)
    assert [item.role for item in classified] == [EvidenceRole.CONTEXT]
    assert_no_support(classified)


def test_adverse_8k_becomes_conflict_and_not_support():
    classified = classify_sec_document(
        record("material_filing"),
        form="8-K",
        document="Item 4.02 Non-Reliance on Previously Issued Financial Statements",
    )
    assert [item.role for item in classified] == [EvidenceRole.CONFLICT]
    assert_no_support(classified)


def test_unknown_8k_item_remains_context():
    classified = classify_sec_document(
        record("material_filing"), form="8-K", document="Item 8.01 Other Events"
    )
    assert [item.role for item in classified] == [EvidenceRole.CONTEXT]
    assert_no_support(classified)


def test_malformed_or_unparsed_document_falls_back_to_raw_context():
    classified = classify_sec_document(record("insider_filing"), form="4", document="<broken")
    assert [item.role for item in classified] == [EvidenceRole.CONTEXT]
    assert_no_support(classified)


def test_non_sec_record_is_rejected():
    other = normalize_record(
        asset="NVDA",
        metric="daily_close",
        value=100,
        source=SourceIdentity("market", "Market", "api", "market"),
        observed_at=NOW,
        statement="market",
    )
    with pytest.raises(ValueError):
        classify_sec_document(other, form="4", document="<ownershipDocument />")
