from datetime import date, datetime, timezone

import pytest

from app.models import SecFiling
from app.ingestion.sec_form4_orchestrator import ingest_form4_filing


XML = """<ownershipDocument>
<issuer><issuerName>Example</issuerName><issuerTradingSymbol>EXM</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerId><rptOwnerName>JANE DOE</rptOwnerName></reportingOwnerId>
<reportingOwnerRelationship><isDirector>1</isDirector></reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction>
<transactionCoding><transactionCode>P</transactionCode></transactionCoding>
<transactionAmounts><transactionShares><value>10</value></transactionShares>
<transactionPricePerShare><value>20</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""


class FakeSession:
    def __init__(self): self.added = []
    def scalar(self, _query): return None
    def add(self, row): self.added.append(row)
    def flush(self): return None


def filing(form="4", url="https://www.sec.gov/Archives/example.xml"):
    return SecFiling(
        cik="1045810", ticker="EXM", company_name="Example", accession_number="0001-26-000001",
        form=form, filing_date=date(2026, 9, 17), report_date=None,
        primary_document="xslF345X05/example.xml", filing_url=url, source="SEC_EDGAR",
    )


def test_orchestrator_fetches_and_creates_evidence():
    calls = []
    result = ingest_form4_filing(
        FakeSession(), filing=filing(), fetch_text=lambda url: calls.append(url) or XML,
        observed_at=datetime(2026, 9, 17, 15, 0, tzinfo=timezone.utc),
    )
    assert calls == ["https://www.sec.gov/Archives/example.xml"]
    assert result.transaction_count == 1
    assert result.evidence_rows[0].payload_json["economic_type"] == "open_market_purchase"


def test_non_form4_is_rejected_before_network_access():
    called = False
    def fetch(_url):
        nonlocal called; called = True; return XML
    with pytest.raises(ValueError, match="not Form 4"):
        ingest_form4_filing(FakeSession(), filing=filing(form="8-K"), fetch_text=fetch,
                            observed_at=datetime.now(timezone.utc))
    assert called is False


def test_non_sec_source_is_rejected_before_fetch():
    with pytest.raises(ValueError, match="HTTPS sec.gov"):
        ingest_form4_filing(FakeSession(), filing=filing(url="https://evil.example/form4.xml"),
                            fetch_text=lambda _: XML, observed_at=datetime.now(timezone.utc))


def test_empty_sec_response_fails_closed():
    with pytest.raises(ValueError, match="empty Form 4"):
        ingest_form4_filing(FakeSession(), filing=filing(), fetch_text=lambda _: "  ",
                            observed_at=datetime.now(timezone.utc))
