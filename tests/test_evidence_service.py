from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Evidence, SecFiling
from app.services.evidence import create_evidence_from_sec_filing, sec_evidence_key


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def filing() -> SecFiling:
    return SecFiling(
        cik="0001045810",
        ticker="NVDA",
        company_name="NVIDIA CORP",
        accession_number="0001045810-26-000001",
        form="8-K",
        filing_date=date(2026, 8, 26),
        report_date=date(2026, 8, 26),
        primary_document="nvda-20260826.htm",
        filing_url="https://www.sec.gov/Archives/example.htm",
        source="SEC_EDGAR",
    )


def test_evidence_key_is_deterministic():
    assert sec_evidence_key("abc") == sec_evidence_key("abc")
    assert sec_evidence_key("abc") != sec_evidence_key("def")


def test_sec_filing_creates_one_idempotent_evidence_row():
    db = make_session()
    record = filing()
    db.add(record)
    db.flush()

    first, first_created = create_evidence_from_sec_filing(db, record)
    second, second_created = create_evidence_from_sec_filing(db, record)
    db.commit()

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert db.query(Evidence).count() == 1
    assert first.asset == "NVDA"
    assert first.source_family == "SEC"
    assert first.payload_json["form"] == "8-K"
