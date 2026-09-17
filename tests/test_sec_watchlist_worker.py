import json
from datetime import datetime, timezone

from app.ingestion.sec_watchlist_worker import SecWatchItem, run_form4_watchlist, submissions_url


XML = """<ownershipDocument><issuer><issuerName>Example</issuerName><issuerTradingSymbol>EXM</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerId><rptOwnerName>JANE DOE</rptOwnerName></reportingOwnerId><reportingOwnerRelationship><isDirector>1</isDirector></reportingOwnerRelationship></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction><transactionCoding><transactionCode>P</transactionCode></transactionCoding>
<transactionAmounts><transactionShares><value>10</value></transactionShares><transactionPricePerShare><value>20</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""


def submissions(cik="1045810"):
    return json.dumps({"cik": cik, "name": "Example", "filings": {"recent": {
        "accessionNumber": ["0001045810-26-000112"], "filingDate": ["2026-09-17"],
        "reportDate": ["2026-09-16"], "form": ["4"], "primaryDocument": ["ownership.xml"]
    }}})


class FakeSession:
    def __init__(self, existing=None): self.existing = existing; self.added = []
    def scalar(self, _query): return self.existing
    def add(self, row): self.added.append(row)
    def flush(self): return None


def test_submissions_url_normalizes_cik():
    assert submissions_url("1045810") == "https://data.sec.gov/submissions/CIK0001045810.json"


def test_worker_discovers_persists_and_ingests_new_form4():
    db = FakeSession()
    calls = []
    def fetch(url):
        calls.append(url)
        return submissions() if "submissions" in url else XML
    run = run_form4_watchlist(
        db, items=[SecWatchItem("1045810", "EXM")], fetch_text=fetch,
        observed_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert run.checked == 1
    assert run.discovered == 1
    assert run.new_filings == 1
    assert run.evidence_rows == 1
    assert run.skipped_existing == 0
    assert run.failures == []
    assert len(calls) == 2


def test_existing_accession_is_skipped_without_fetching_document():
    db = FakeSession(existing=object())
    calls = []
    def fetch(url): calls.append(url); return submissions()
    run = run_form4_watchlist(db, items=[SecWatchItem("1045810", "EXM")], fetch_text=fetch,
                              observed_at=datetime.now(timezone.utc))
    assert run.skipped_existing == 1
    assert run.new_filings == 0
    assert run.evidence_rows == 0
    assert len(calls) == 1


def test_one_company_failure_does_not_abort_remaining_watchlist():
    db = FakeSession()
    def fetch(url):
        if "0000000001" in url: raise RuntimeError("simulated SEC failure")
        return submissions("2") if "submissions" in url else XML
    run = run_form4_watchlist(
        db, items=[SecWatchItem("1", "BAD"), SecWatchItem("2", "GOOD")], fetch_text=fetch,
        observed_at=datetime.now(timezone.utc),
    )
    assert run.checked == 2
    assert len(run.failures) == 1
    assert run.failures[0]["ticker"] == "BAD"
    assert run.new_filings == 1
