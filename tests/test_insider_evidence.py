from datetime import datetime, timezone

from app.services.insider_evidence import ingest_form4_evidence


FORM4 = """<ownershipDocument>
<issuer><issuerName>Example Corp</issuerName><issuerTradingSymbol>EXM</issuerTradingSymbol></issuer>
<reportingOwner>
 <reportingOwnerId><rptOwnerName>JANE DOE</rptOwnerName></reportingOwnerId>
 <reportingOwnerRelationship><isOfficer>1</isOfficer><officerTitle>CEO</officerTitle></reportingOwnerRelationship>
</reportingOwner>
<nonDerivativeTable>
 <nonDerivativeTransaction>
  <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
  <transactionAmounts>
   <transactionShares><value>100</value></transactionShares>
   <transactionPricePerShare><value>25.50</value></transactionPricePerShare>
   <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
  </transactionAmounts>
  <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
 </nonDerivativeTransaction>
</nonDerivativeTable>
</ownershipDocument>"""


class FakeSession:
    def __init__(self, existing=None): self.existing = existing; self.added = []
    def scalar(self, _query): return self.existing
    def add(self, row): self.added.append(row)
    def flush(self): return None


def test_form4_xml_becomes_classified_evidence():
    db = FakeSession()
    rows = ingest_form4_evidence(
        db, xml_text=FORM4, accession_number="0001-26-000001",
        source_url="https://www.sec.gov/example.xml",
        observed_at=datetime(2026, 9, 17, 14, 0, tzinfo=timezone.utc),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.asset == "EXM"
    assert row.category == "insider_transaction"
    assert row.source_family == "SEC"
    assert row.payload_json["economic_type"] == "open_market_purchase"
    assert row.payload_json["direction"] == "buy"
    assert row.payload_json["signal_eligible"] is True
    assert row.payload_json["transaction_value"] == "2550.00"
    assert row.payload_json["owner_name"] == "JANE DOE"
    assert db.added == [row]


def test_same_accession_owner_and_index_is_idempotent():
    first = FakeSession()
    row = ingest_form4_evidence(
        first, xml_text=FORM4, accession_number="0001-26-000001",
        source_url="https://www.sec.gov/example.xml",
        observed_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )[0]
    second = FakeSession(existing=row)
    rows = ingest_form4_evidence(
        second, xml_text=FORM4, accession_number="0001-26-000001",
        source_url="https://www.sec.gov/example.xml",
        observed_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert rows == [row]
    assert second.added == []
