import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.form4_xml import parse_form4_xml
from app.ingestion.sec_edgar import SecEdgarClient
from app.models import SecFiling
from app.services.evidence import create_evidence_from_sec_filing, create_form4_transaction_evidence

logger = logging.getLogger(__name__)
COMPANIES={"NVDA":{"cik":"1045810","name":"NVIDIA CORP"}}

def _parse_date(value:str|None)->date|None:return date.fromisoformat(value) if value else None

def _event(event: str, **fields) -> None:
    """Emit one searchable SEC-ingestion event without remote document bodies or secrets."""
    logger.info("sec_ingestion event=%s %s", event, " ".join(f"{key}={value}" for key,value in sorted(fields.items())))

def sync_company_filings(db:Session,ticker:str,client:SecEdgarClient|None=None,limit:int=50)->dict[str,int|str|list[dict[str,str]]]:
    symbol=ticker.upper();company=COMPANIES.get(symbol)
    if not company:raise ValueError(f"Unsupported ticker: {symbol}")
    sec=client or SecEdgarClient();filings=sec.recent_filings(company["cik"],limit=limit)
    created=existing=evidence_created=transaction_evidence_created=0;failures=[]
    _event("sync_started",ticker=symbol,cik=company["cik"],filings=len(filings))
    for filing in filings:
        found=db.scalar(select(SecFiling).where(SecFiling.accession_number==filing.accession_number))
        if found:
            existing+=1;record=found;_event("filing_existing",ticker=symbol,form=filing.form,accession=filing.accession_number)
        else:
            record=SecFiling(cik=str(filing.cik).zfill(10),ticker=symbol,company_name=company["name"],accession_number=filing.accession_number,form=filing.form,filing_date=_parse_date(filing.filing_date),report_date=_parse_date(filing.report_date),primary_document=filing.primary_document,filing_url=filing.filing_url,source="SEC_EDGAR")
            db.add(record);db.flush();created+=1;_event("filing_created",ticker=symbol,form=filing.form,accession=filing.accession_number)
        _,made=create_evidence_from_sec_filing(db,record);evidence_created+=int(made)
        if filing.form=="4":
            try:
                xml=sec.get_filing_document(filing);transactions=parse_form4_xml(xml,ticker=symbol)
                made_transactions=create_form4_transaction_evidence(db,record,transactions);transaction_evidence_created+=made_transactions
                _event("form4_parsed",ticker=symbol,accession=filing.accession_number,transactions=len(transactions),transaction_evidence_created=made_transactions)
            except Exception as exc:
                error=f"{type(exc).__name__}: {str(exc)[:200]}";failure={"accession_number":filing.accession_number,"stage":"form4_document","error":error};failures.append(failure)
                logger.warning("sec_ingestion event=form4_failed ticker=%s accession=%s stage=form4_document error_type=%s error=%s",symbol,filing.accession_number,type(exc).__name__,str(exc)[:200])
    db.commit()
    summary={"ticker":symbol,"created":created,"existing":existing,"evidence_created":evidence_created,"transaction_evidence_created":transaction_evidence_created,"form4_failures":failures}
    _event("sync_completed",ticker=symbol,created=created,existing=existing,evidence_created=evidence_created,transaction_evidence_created=transaction_evidence_created,failures=len(failures))
    return summary

def latest_filings(db:Session,ticker:str|None=None,limit:int=50)->list[SecFiling]:
    query=select(SecFiling)
    if ticker:query=query.where(SecFiling.ticker==ticker.upper())
    return list(db.scalars(query.order_by(SecFiling.filing_date.desc(),SecFiling.id.desc()).limit(limit)).all())
