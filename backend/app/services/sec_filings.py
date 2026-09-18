from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.form4_xml import parse_form4_xml
from app.ingestion.sec_edgar import SecEdgarClient
from app.models import SecFiling
from app.services.evidence import create_evidence_from_sec_filing, create_form4_transaction_evidence

COMPANIES={"NVDA":{"cik":"1045810","name":"NVIDIA CORP"}}

def _parse_date(value:str|None)->date|None:return date.fromisoformat(value) if value else None

def sync_company_filings(db:Session,ticker:str,client:SecEdgarClient|None=None,limit:int=50)->dict[str,int|str|list[dict[str,str]]]:
    symbol=ticker.upper();company=COMPANIES.get(symbol)
    if not company:raise ValueError(f"Unsupported ticker: {symbol}")
    sec=client or SecEdgarClient();filings=sec.recent_filings(company["cik"],limit=limit)
    created=existing=evidence_created=transaction_evidence_created=0;failures=[]
    for filing in filings:
        found=db.scalar(select(SecFiling).where(SecFiling.accession_number==filing.accession_number))
        if found:
            existing+=1;record=found
        else:
            record=SecFiling(cik=str(filing.cik).zfill(10),ticker=symbol,company_name=company["name"],accession_number=filing.accession_number,form=filing.form,filing_date=_parse_date(filing.filing_date),report_date=_parse_date(filing.report_date),primary_document=filing.primary_document,filing_url=filing.filing_url,source="SEC_EDGAR")
            db.add(record);db.flush();created+=1
        _,made=create_evidence_from_sec_filing(db,record);evidence_created+=int(made)
        if filing.form=="4":
            try:
                xml=sec.get_filing_document(filing);transactions=parse_form4_xml(xml,ticker=symbol)
                transaction_evidence_created+=create_form4_transaction_evidence(db,record,transactions)
            except Exception as exc:
                # Metadata remains valid evidence, but failed document parsing must never
                # fabricate transaction facts. Keep a bounded operational failure record.
                failures.append({"accession_number":filing.accession_number,"stage":"form4_document","error":f"{type(exc).__name__}: {str(exc)[:200]}"})
    db.commit()
    return {"ticker":symbol,"created":created,"existing":existing,"evidence_created":evidence_created,"transaction_evidence_created":transaction_evidence_created,"form4_failures":failures}

def latest_filings(db:Session,ticker:str|None=None,limit:int=50)->list[SecFiling]:
    query=select(SecFiling)
    if ticker:query=query.where(SecFiling.ticker==ticker.upper())
    return list(db.scalars(query.order_by(SecFiling.filing_date.desc(),SecFiling.id.desc()).limit(limit)).all())
