from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.ingestion.sec_edgar import SecFiling as RemoteFiling
from app.models import Evidence
from app.services.sec_filings import sync_company_filings

XML='''<ownershipDocument><issuer><issuerCik>0001045810</issuerCik><issuerName>NVIDIA CORP</issuerName><issuerTradingSymbol>NVDA</issuerTradingSymbol></issuer><reportingOwner><reportingOwnerId><rptOwnerCik>0000000001</rptOwnerCik><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId><reportingOwnerRelationship><isDirector>0</isDirector><isOfficer>1</isOfficer><isTenPercentOwner>0</isTenPercentOwner><isOther>0</isOther><officerTitle>CEO</officerTitle></reportingOwnerRelationship></reportingOwner><nonDerivativeTable><nonDerivativeTransaction><transactionCoding><transactionCode>S</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>10</value></transactionShares><transactionPricePerShare><value>100</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts><ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>'''

class Client:
    def __init__(self, document=XML, error=None): self.document=document; self.error=error
    def recent_filings(self,cik,limit=50):
        return [RemoteFiling(cik="1045810",accession_number="0001045810-26-000001",form="4",filing_date="2026-09-18",report_date=None,primary_document="xslF345X05/form4.xml",primary_doc_description="FORM 4")]
    def get_filing_document(self,filing):
        if self.error: raise self.error
        return self.document

def db_session():
    engine=create_engine("sqlite:///:memory:");Base.metadata.create_all(engine);return sessionmaker(bind=engine)()

def test_form4_sync_persists_traceable_transaction_evidence():
    db=db_session(); result=sync_company_filings(db,"NVDA",Client())
    assert result["transaction_evidence_created"]==1
    rows=list(db.scalars(select(Evidence).where(Evidence.source_record_id.like("%:tx:%"))).all())
    assert len(rows)==1
    payload=rows[0].payload_json
    assert payload["accession_number"]=="0001045810-26-000001"
    assert payload["economic_type"]=="open_market_sale"
    assert payload["signal_eligible"] is True

def test_repeated_sync_is_idempotent_for_transaction_evidence():
    db=db_session(); first=sync_company_filings(db,"NVDA",Client()); second=sync_company_filings(db,"NVDA",Client())
    assert first["transaction_evidence_created"]==1
    assert second["transaction_evidence_created"]==0

def test_unavailable_document_records_failure_and_creates_no_transaction_evidence():
    db=db_session(); result=sync_company_filings(db,"NVDA",Client(error=RuntimeError("upstream unavailable")))
    assert result["transaction_evidence_created"]==0
    assert result["form4_failures"][0]["stage"]=="form4_document"
    assert list(db.scalars(select(Evidence).where(Evidence.source_record_id.like("%:tx:%"))).all())==[]

def test_malformed_document_records_failure_and_creates_no_transaction_evidence():
    db=db_session(); result=sync_company_filings(db,"NVDA",Client(document="<ownershipDocument>"))
    assert result["transaction_evidence_created"]==0
    assert len(result["form4_failures"])==1
