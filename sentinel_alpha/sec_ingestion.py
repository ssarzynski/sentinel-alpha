"""SEC EDGAR public submissions ingestion for Sentinel Alpha."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.request import Request, urlopen

from .provenance import NormalizedRecord
from .providers import SEC_FILINGS

SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
WATCHED_FORMS = frozenset({"8-K", "8-K/A", "4", "4/A"})
MAX_DOCUMENT_BYTES = 5_000_000
SEC_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class SecFiling:
    cik: str
    accession_number: str
    form: str
    filing_date: str
    primary_document: str
    accepted_at: str | None = None

    @property
    def archive_reference(self) -> str:
        accession = self.accession_number.replace("-", "")
        cik_number = str(int(self.cik))
        return (
            f"https://www.sec.gov/Archives/edgar/data/{cik_number}/"
            f"{accession}/{self.primary_document}"
        )


def normalize_cik(cik: str | int) -> str:
    digits = str(cik).strip()
    if not digits.isdigit() or len(digits) > 10:
        raise ValueError("CIK must contain at most 10 digits")
    return digits.zfill(10)


def submissions_url(cik: str | int) -> str:
    return f"{SEC_SUBMISSIONS_BASE}/CIK{normalize_cik(cik)}.json"


def parse_recent_filings(payload: dict[str, Any], forms: set[str] | frozenset[str] = WATCHED_FORMS) -> list[SecFiling]:
    cik = normalize_cik(payload["cik"])
    recent = payload.get("filings", {}).get("recent", {})
    required = ("accessionNumber", "filingDate", "form", "primaryDocument")
    columns = [recent.get(name, []) for name in required]
    if not columns or any(len(column) != len(columns[0]) for column in columns):
        raise ValueError("SEC recent filing columns are inconsistent")
    accepted = recent.get("acceptanceDateTime", [])
    filings: list[SecFiling] = []
    for index, (accession, filing_date, form, primary_document) in enumerate(zip(*columns)):
        if form not in forms:
            continue
        accepted_at = accepted[index] if index < len(accepted) else None
        filings.append(
            SecFiling(
                cik=cik,
                accession_number=accession,
                form=form,
                filing_date=filing_date,
                primary_document=primary_document,
                accepted_at=accepted_at,
            )
        )
    return filings


def filing_to_record(filing: SecFiling, asset: str) -> NormalizedRecord:
    observed_at = datetime.now(timezone.utc)
    if filing.accepted_at:
        try:
            observed_at = datetime.fromisoformat(filing.accepted_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    metric = "insider_filing" if filing.form.startswith("4") else "material_filing"
    return SEC_FILINGS.normalize(
        {
            "asset": asset,
            "metric": metric,
            "value": filing.form,
            "statement": f"SEC {filing.form} filing {filing.accession_number}",
            "reference": filing.archive_reference,
            "quality": "high",
        },
        observed_at,
    )


class SecEdgarClient:
    """Minimal public-data client; caller must supply a declared SEC User-Agent."""

    def __init__(self, user_agent: str, opener: Callable[..., Any] = urlopen) -> None:
        if not user_agent.strip() or "@" not in user_agent:
            raise ValueError("SEC user_agent must identify an application and contact email")
        self.user_agent = user_agent.strip()
        self.opener = opener

    def _request(self, url: str, accept: str) -> Request:
        return Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": accept,
                "Accept-Encoding": "gzip, deflate",
            },
        )

    def fetch_submissions(self, cik: str | int) -> dict[str, Any]:
        request = self._request(submissions_url(cik), "application/json")
        with self.opener(request, timeout=SEC_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("SEC submissions response must be a JSON object")
        return payload

    def fetch_filing_document(self, filing: SecFiling) -> str:
        """Fetch a primary filing document with bounded memory and fail-closed checks."""
        request = self._request(
            filing.archive_reference,
            "text/html, application/xhtml+xml, application/xml, text/xml, text/plain",
        )
        with self.opener(request, timeout=SEC_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get_content_type().lower()
            if content_type not in {
                "text/html",
                "application/xhtml+xml",
                "application/xml",
                "text/xml",
                "text/plain",
            }:
                raise ValueError(f"unsupported SEC filing content type: {content_type}")
            declared_length = response.headers.get("Content-Length")
            if declared_length is not None and int(declared_length) > MAX_DOCUMENT_BYTES:
                raise ValueError("SEC filing document exceeds size limit")
            body = response.read(MAX_DOCUMENT_BYTES + 1)
        if len(body) > MAX_DOCUMENT_BYTES:
            raise ValueError("SEC filing document exceeds size limit")
        return body.decode("utf-8", errors="replace")

    def recent_watched_filings(self, cik: str | int) -> list[SecFiling]:
        return parse_recent_filings(self.fetch_submissions(cik))
