from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sec_discovery import discover_form4_filings
from app.ingestion.sec_form4_orchestrator import ingest_form4_filing
from app.models import SecFiling

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecWatchItem:
    cik: str
    ticker: str


@dataclass
class SecWatchRun:
    checked: int = 0
    discovered: int = 0
    new_filings: int = 0
    evidence_rows: int = 0
    skipped_existing: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)


def submissions_url(cik: str) -> str:
    digits = "".join(ch for ch in cik if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain digits")
    return f"https://data.sec.gov/submissions/CIK{digits.zfill(10)}.json"


def _event(event: str, **fields) -> None:
    logger.info("sec_ingestion event=%s %s", event, " ".join(f"{key}={value}" for key, value in sorted(fields.items())))


def run_form4_watchlist(db: Session, *, items: list[SecWatchItem], fetch_text: Callable[[str], str], observed_at: datetime) -> SecWatchRun:
    """Run the scheduled SEC Form 4 watchlist through the canonical parser/evidence path.

    Per-company failures are isolated so one bad SEC response does not suppress the
    remaining watchlist. Evidence creation remains idempotent downstream.
    """
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    run = SecWatchRun()
    _event("watchlist_started", items=len(items))
    for item in items:
        run.checked += 1
        try:
            submissions = fetch_text(submissions_url(item.cik))
            filings = discover_form4_filings(submissions, ticker=item.ticker)
            run.discovered += len(filings)
            _event("company_discovered", ticker=item.ticker.upper(), cik=item.cik, filings=len(filings))
            for found in filings:
                existing = db.scalar(select(SecFiling).where(SecFiling.accession_number == found.accession_number))
                if existing:
                    run.skipped_existing += 1
                    _event("filing_existing", ticker=item.ticker.upper(), accession=found.accession_number, form=found.form)
                    continue
                filing = SecFiling(cik=found.cik, ticker=found.ticker, company_name=found.company_name, accession_number=found.accession_number, form=found.form, filing_date=found.filing_date, report_date=found.report_date, primary_document=found.primary_document, filing_url=found.filing_url, source="SEC_EDGAR")
                db.add(filing); db.flush(); run.new_filings += 1
                _event("filing_created", ticker=item.ticker.upper(), accession=found.accession_number, form=found.form)
                result = ingest_form4_filing(db, filing=filing, fetch_text=fetch_text, observed_at=observed_at)
                run.evidence_rows += result.transaction_count
                _event("form4_parsed", ticker=item.ticker.upper(), accession=result.accession_number, transactions=result.transaction_count)
        except Exception as exc:
            failure={"ticker":item.ticker,"cik":item.cik,"stage":"watchlist_company","error_type":type(exc).__name__,"error":str(exc)[:200]}
            run.failures.append(failure)
            logger.warning("sec_ingestion event=company_failed ticker=%s cik=%s stage=watchlist_company error_type=%s error=%s", item.ticker, item.cik, type(exc).__name__, str(exc)[:200])
    _event("watchlist_completed", checked=run.checked, discovered=run.discovered, new_filings=run.new_filings, skipped_existing=run.skipped_existing, evidence_rows=run.evidence_rows, failures=len(run.failures))
    return run
