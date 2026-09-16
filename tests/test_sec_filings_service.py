from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.ingestion.sec_edgar import SecFiling as IngestedFiling
from app.models import SecFiling
from app.services.sec_filings import latest_filings, sync_company_filings


class FakeSecClient:
    def recent_filings(self, cik: str, limit: int = 50):
        return [
            IngestedFiling(
                cik=cik,
                accession_number="0001045810-26-000001",
                form="8-K",
                filing_date="2026-08-26",
                report_date="2026-08-26",
                primary_document="nvda-20260826.htm",
                primary_doc_description="FORM 8-K",
            )
        ]


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_sync_persists_and_deduplicates_filings():
    db = make_session()
    first = sync_company_filings(db, "NVDA", client=FakeSecClient())
    second = sync_company_filings(db, "nvda", client=FakeSecClient())

    assert first == {"ticker": "NVDA", "created": 1, "existing": 0}
    assert second == {"ticker": "NVDA", "created": 0, "existing": 1}
    assert db.query(SecFiling).count() == 1


def test_latest_filings_filters_by_ticker():
    db = make_session()
    sync_company_filings(db, "NVDA", client=FakeSecClient())
    results = latest_filings(db, ticker="nvda")

    assert len(results) == 1
    assert results[0].ticker == "NVDA"
    assert results[0].form == "8-K"
