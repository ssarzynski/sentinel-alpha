from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sec_edgar import SecEdgarClient
from app.models import SecFiling


COMPANIES = {
    "NVDA": {"cik": "1045810", "name": "NVIDIA CORP"},
}


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def sync_company_filings(
    db: Session,
    ticker: str,
    client: SecEdgarClient | None = None,
    limit: int = 50,
) -> dict[str, int | str]:
    symbol = ticker.upper()
    company = COMPANIES.get(symbol)
    if not company:
        raise ValueError(f"Unsupported ticker: {symbol}")

    sec = client or SecEdgarClient()
    filings = sec.recent_filings(company["cik"], limit=limit)
    created = 0
    existing = 0

    for filing in filings:
        found = db.scalar(
            select(SecFiling).where(SecFiling.accession_number == filing.accession_number)
        )
        if found:
            existing += 1
            continue

        db.add(
            SecFiling(
                cik=str(filing.cik).zfill(10),
                ticker=symbol,
                company_name=company["name"],
                accession_number=filing.accession_number,
                form=filing.form,
                filing_date=_parse_date(filing.filing_date),
                report_date=_parse_date(filing.report_date),
                primary_document=filing.primary_document,
                filing_url=filing.filing_url,
                source="SEC_EDGAR",
            )
        )
        created += 1

    db.commit()
    return {"ticker": symbol, "created": created, "existing": existing}


def latest_filings(db: Session, ticker: str | None = None, limit: int = 50) -> list[SecFiling]:
    query = select(SecFiling)
    if ticker:
        query = query.where(SecFiling.ticker == ticker.upper())
    query = query.order_by(SecFiling.filing_date.desc(), SecFiling.id.desc()).limit(limit)
    return list(db.scalars(query).all())
