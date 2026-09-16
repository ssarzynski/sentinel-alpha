from app.ingestion.sec_edgar import SecEdgarClient


def test_recent_filings_filters_forms_and_builds_archive_url(monkeypatch):
    payload = {
        "cik": "1045810",
        "filings": {
            "recent": {
                "accessionNumber": ["0001045810-26-000001", "0001045810-26-000002"],
                "form": ["8-K", "DEF 14A"],
                "filingDate": ["2026-08-26", "2026-08-20"],
                "reportDate": ["2026-08-26", ""],
                "primaryDocument": ["nvda-20260826.htm", "proxy.htm"],
                "primaryDocDescription": ["FORM 8-K", "Proxy"],
            }
        },
    }
    client = SecEdgarClient(user_agent="SentinelAlpha tests@example.com")
    monkeypatch.setattr(client, "get_submissions", lambda cik: payload)

    filings = client.recent_filings("1045810", forms={"8-K"})

    assert len(filings) == 1
    assert filings[0].form == "8-K"
    assert filings[0].accession_number == "0001045810-26-000001"
    assert filings[0].filing_url.endswith("/000104581026000001/nvda-20260826.htm")


def test_cik_is_zero_padded(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"filings": {"recent": {"accessionNumber": []}}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, url):
            captured["url"] = url
            return Response()

    monkeypatch.setattr("app.ingestion.sec_edgar.httpx.Client", FakeClient)
    SecEdgarClient(user_agent="SentinelAlpha tests@example.com").get_submissions("1045810")
    assert captured["url"].endswith("CIK0001045810.json")
