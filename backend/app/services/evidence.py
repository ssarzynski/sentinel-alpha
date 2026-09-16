import hashlib
from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Evidence, SecFiling


def sec_evidence_key(accession_number: str) -> str:
    raw = f"SEC_EDGAR:{accession_number}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def create_evidence_from_sec_filing(db: Session, filing: SecFiling) -> tuple[Evidence, bool]:
    """Create one append-only Evidence row for a filing, idempotently."""
    key = sec_evidence_key(filing.accession_number)
    existing = db.scalar(select(Evidence).where(Evidence.evidence_key == key))
    if existing:
        return existing, False

    observed_at = datetime.combine(filing.filing_date, time.min, tzinfo=timezone.utc)
    evidence = Evidence(
        evidence_key=key,
        asset=filing.ticker,
        category="regulatory_filing",
        source="SEC_EDGAR",
        source_family="SEC",
        source_record_id=filing.accession_number,
        title=f"{filing.ticker or filing.company_name or filing.cik} {filing.form} filing",
        source_url=filing.filing_url,
        observed_at=observed_at,
        payload_json={
            "cik": filing.cik,
            "ticker": filing.ticker,
            "company_name": filing.company_name,
            "accession_number": filing.accession_number,
            "form": filing.form,
            "filing_date": filing.filing_date.isoformat(),
            "report_date": filing.report_date.isoformat() if filing.report_date else None,
            "primary_document": filing.primary_document,
        },
    )
    db.add(evidence)
    db.flush()
    return evidence, True


def backfill_sec_evidence(db: Session, ticker: str | None = None) -> dict[str, int]:
    query = select(SecFiling)
    if ticker:
        query = query.where(SecFiling.ticker == ticker.upper())
    filings = list(db.scalars(query).all())
    created = 0
    existing = 0
    for filing in filings:
        _, was_created = create_evidence_from_sec_filing(db, filing)
        created += int(was_created)
        existing += int(not was_created)
    db.commit()
    return {"created": created, "existing": existing}


def latest_evidence(db: Session, asset: str | None = None, limit: int = 50) -> list[Evidence]:
    query = select(Evidence)
    if asset:
        query = query.where(Evidence.asset == asset.upper())
    query = query.order_by(Evidence.observed_at.desc(), Evidence.id.desc()).limit(limit)
    return list(db.scalars(query).all())
