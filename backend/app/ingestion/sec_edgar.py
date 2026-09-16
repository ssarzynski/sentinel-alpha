import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

SEC_BASE_URL = "https://data.sec.gov"
DEFAULT_FORMS = {"8-K", "10-K", "10-Q", "4"}


@dataclass(frozen=True)
class SecFiling:
    cik: str
    accession_number: str
    form: str
    filing_date: str
    report_date: str | None
    primary_document: str
    primary_doc_description: str | None

    @property
    def filing_url(self) -> str:
        cik_number = str(int(self.cik))
        accession_compact = self.accession_number.replace("-", "")
        return (
            f"https://www.sec.gov/Archives/edgar/data/{cik_number}/"
            f"{accession_compact}/{self.primary_document}"
        )


class SecEdgarClient:
    """Small SEC submissions API client with an explicit identifying User-Agent."""

    def __init__(self, user_agent: str | None = None, timeout: float = 20.0) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT", "SentinelAlpha research@example.com")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def get_submissions(self, cik: str) -> dict[str, Any]:
        padded_cik = str(cik).zfill(10)
        url = f"{SEC_BASE_URL}/submissions/CIK{padded_cik}.json"
        with httpx.Client(timeout=self.timeout, headers=self._headers()) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def recent_filings(self, cik: str, forms: set[str] | None = None, limit: int = 50) -> list[SecFiling]:
        payload = self.get_submissions(cik)
        recent = payload.get("filings", {}).get("recent", {})
        wanted = forms or DEFAULT_FORMS
        results: list[SecFiling] = []
        count = len(recent.get("accessionNumber", []))
        for index in range(count):
            form = recent.get("form", [])[index]
            if form not in wanted:
                continue
            results.append(
                SecFiling(
                    cik=str(payload.get("cik", cik)),
                    accession_number=recent["accessionNumber"][index],
                    form=form,
                    filing_date=recent.get("filingDate", [""] * count)[index],
                    report_date=(recent.get("reportDate", [None] * count)[index] or None),
                    primary_document=recent.get("primaryDocument", [""] * count)[index],
                    primary_doc_description=(recent.get("primaryDocDescription", [None] * count)[index] or None),
                )
            )
            if len(results) >= limit:
                break
        return results


def utc_now() -> datetime:
    return datetime.now().astimezone()
