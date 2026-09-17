from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import Evidence, SecFiling
from app.services.insider_evidence import ingest_form4_evidence


@dataclass(frozen=True)
class Form4IngestionResult:
    accession_number: str
    source_url: str
    transaction_count: int
    evidence_rows: tuple[Evidence, ...]


def _validate_sec_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {"www.sec.gov", "sec.gov"}:
        raise ValueError("Form 4 source URL must be an HTTPS sec.gov URL")


def ingest_form4_filing(
    db: Session,
    *,
    filing: SecFiling,
    fetch_text: Callable[[str], str],
    observed_at: datetime,
) -> Form4IngestionResult:
    """Retrieve one known SEC Form 4 document and persist normalized evidence.

    Network I/O is injected so tests are deterministic and the SEC HTTP client can
    independently enforce User-Agent, throttling, retry, and timeout policy.
    """
    if filing.form not in {"4", "4/A"}:
        raise ValueError(f"filing is not Form 4 ownership data: {filing.form}")
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    _validate_sec_url(filing.filing_url)

    xml_text = fetch_text(filing.filing_url)
    if not xml_text.strip():
        raise ValueError("SEC returned an empty Form 4 document")

    rows = ingest_form4_evidence(
        db,
        xml_text=xml_text,
        accession_number=filing.accession_number,
        source_url=filing.filing_url,
        observed_at=observed_at,
        ticker=filing.ticker,
    )
    return Form4IngestionResult(
        accession_number=filing.accession_number,
        source_url=filing.filing_url,
        transaction_count=len(rows),
        evidence_rows=tuple(rows),
    )
