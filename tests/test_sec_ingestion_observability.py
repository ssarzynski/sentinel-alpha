import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.ingestion.sec_edgar import SecFiling as RemoteFiling
from app.services.sec_filings import sync_company_filings

XML='''<ownershipDocument><issuer><issuerCik>0001045810</issuerCik><issuerName>NVIDIA CORP</issuerName><issuerTradingSymbol>NVDA</issuerTradingSymbol></issuer><reportingOwner><reportingOwnerId><rptOwnerCik>1</rptOwnerCik><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId><reportingOwnerRelationship><isDirector>0</isDirector><isOfficer>1</isOfficer><isTenPercentOwner>0</isTenPercentOwner><isOther>0</isOther></reportingOwnerRelationship></reportingOwner><nonDerivativeTable><nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>10</value></transactionShares><transactionPricePerShare><value>100</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts><ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>'''

class Client:
    def __init__(self,error=None): self.error=error
    def recent_filings(self,cik,limit=50): return [RemoteFiling(cik="1045810",accession_number="0001045810-26-000009",form="4",filing_date="2026-09-18",report_date=None,primary_document="form4.xml",primary_doc_description="FORM 4")]
    def get_filing_document(self,filing):
        if self.error: raise self.error
        return XML

def db():
    engine=create_engine("sqlite:///:memory:");Base.metadata.create_all(engine);return Session(engine)

def messages(caplog): return [record.getMessage() for record in caplog.records if "sec_ingestion" in record.getMessage()]

def test_success_emits_traceable_lifecycle_events(caplog):
    caplog.set_level(logging.INFO,"app.services.sec_filings")
    sync_company_filings(db(),"NVDA",Client())
    text="\n".join(messages(caplog))
    assert "event=sync_started" in text
    assert "event=filing_created" in text
    assert "event=form4_parsed" in text
    assert "accession=0001045810-26-000009" in text
    assert "transactions=1" in text
    assert "event=sync_completed" in text

def test_failure_emits_stage_and_error_type_without_document_body(caplog):
    caplog.set_level(logging.INFO,"app.services.sec_filings")
    sync_company_filings(db(),"NVDA",Client(error=RuntimeError("upstream unavailable")))
    text="\n".join(messages(caplog))
    assert "event=form4_failed" in text
    assert "stage=form4_document" in text
    assert "error_type=RuntimeError" in text
    assert "accession=0001045810-26-000009" in text
    assert "<ownershipDocument" not in text
