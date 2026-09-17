import json

import pytest

from app.ingestion.sec_discovery import discover_form4_filings


def payload():
    return json.dumps({
        "cik": "1045810", "name": "NVIDIA CORP",
        "filings": {"recent": {
            "accessionNumber": ["0001045810-26-000111", "0001045810-26-000112", "0001045810-26-000113"],
            "filingDate": ["2026-09-15", "2026-09-16", "2026-09-17"],
            "reportDate": ["2026-09-14", "2026-09-15", "2026-09-16"],
            "form": ["8-K", "4", "4/A"],
            "primaryDocument": ["earnings.htm", "ownership.xml", "ownership-amendment.xml"]
        }}
    })


def test_discovers_only_form4_and_amendments():
    rows = discover_form4_filings(payload(), ticker="nvda")
    assert len(rows) == 2
    assert [row.form for row in rows] == ["4", "4/A"]
    assert rows[0].ticker == "NVDA"
    assert rows[0].cik == "0001045810"
    assert rows[0].filing_url == "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000112/ownership.xml"


def test_invalid_json_and_missing_cik_fail_closed():
    with pytest.raises(ValueError, match="invalid SEC submissions JSON"):
        discover_form4_filings("not json")
    with pytest.raises(ValueError, match="missing CIK"):
        discover_form4_filings(json.dumps({"filings": {"recent": {}}}))


def test_inconsistent_required_arrays_are_rejected():
    data = json.loads(payload())
    data["filings"]["recent"]["form"].pop()
    with pytest.raises(ValueError, match="inconsistent lengths"):
        discover_form4_filings(json.dumps(data))
