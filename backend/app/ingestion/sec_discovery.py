from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DiscoveredForm4:
    cik: str
    ticker: str | None
    company_name: str | None
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None
    primary_document: str
    filing_url: str


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _archive_url(cik: str, accession: str, primary_document: str) -> str:
    cik_number = str(int(cik))
    accession_compact = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_number}/{accession_compact}/{primary_document}"


def discover_form4_filings(submissions_text: str, *, ticker: str | None = None) -> list[DiscoveredForm4]:
    try:
        payload = json.loads(submissions_text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid SEC submissions JSON") from exc

    cik = str(payload.get("cik") or "").strip()
    if not cik:
        raise ValueError("SEC submissions payload is missing CIK")
    company_name = payload.get("name")
    recent = payload.get("filings", {}).get("recent", {})
    required = ["accessionNumber", "filingDate", "form", "primaryDocument"]
    if any(not isinstance(recent.get(field), list) for field in required):
        raise ValueError("SEC submissions payload has invalid recent filing arrays")

    lengths = {len(recent[field]) for field in required}
    if len(lengths) != 1:
        raise ValueError("SEC recent filing arrays have inconsistent lengths")

    report_dates = recent.get("reportDate") or [""] * len(recent["form"])
    if len(report_dates) != len(recent["form"]):
        raise ValueError("SEC reportDate array has inconsistent length")

    results: list[DiscoveredForm4] = []
    for i, form in enumerate(recent["form"]):
        if form not in {"4", "4/A"}:
            continue
        accession = recent["accessionNumber"][i]
        primary_document = recent["primaryDocument"][i]
        results.append(
            DiscoveredForm4(
                cik=cik.zfill(10), ticker=ticker.upper() if ticker else None,
                company_name=company_name, accession_number=accession, form=form,
                filing_date=_date(recent["filingDate"][i]), report_date=_date(report_dates[i]),
                primary_document=primary_document,
                filing_url=_archive_url(cik, accession, primary_document),
            )
        )
    return results
