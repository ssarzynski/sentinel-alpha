import json
from datetime import timezone
from email.message import Message

import pytest

from sentinel_alpha.sec_ingestion import (
    MAX_DOCUMENT_BYTES,
    SecEdgarClient,
    filing_to_record,
    normalize_cik,
    parse_recent_filings,
    submissions_url,
)


SEC_PAYLOAD = {
    "cik": "1045810",
    "filings": {
        "recent": {
            "accessionNumber": ["0001045810-26-000001", "0001045810-26-000002", "0001045810-26-000003"],
            "filingDate": ["2026-09-17", "2026-09-16", "2026-09-15"],
            "acceptanceDateTime": ["2026-09-17T12:00:00Z", "2026-09-16T11:00:00Z", "2026-09-15T10:00:00Z"],
            "form": ["8-K", "4", "10-Q"],
            "primaryDocument": ["nvda-8k.htm", "ownership.xml", "nvda-10q.htm"],
        }
    },
}


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "text/html", content_length: int | None = None):
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_cik_is_zero_padded_for_submissions_api():
    assert normalize_cik(1045810) == "0001045810"
    assert submissions_url(1045810).endswith("CIK0001045810.json")


def test_recent_parser_keeps_watched_8k_and_form4():
    filings = parse_recent_filings(SEC_PAYLOAD)
    assert [filing.form for filing in filings] == ["8-K", "4"]
    assert filings[0].archive_reference.endswith("/000104581026000001/nvda-8k.htm")


def test_sec_filing_normalizes_into_high_quality_provenance():
    filing = parse_recent_filings(SEC_PAYLOAD)[0]
    record = filing_to_record(filing, "NVDA")
    assert record.observation.asset == "NVDA"
    assert record.observation.metric == "material_filing"
    assert record.observation.quality == "high"
    assert record.source.independence_key == "sec"
    assert record.observation.observed_at.tzinfo == timezone.utc


def test_form4_is_classified_as_insider_filing():
    record = filing_to_record(parse_recent_filings(SEC_PAYLOAD)[1], "NVDA")
    assert record.observation.metric == "insider_filing"


def test_inconsistent_sec_columns_are_rejected():
    broken = json.loads(json.dumps(SEC_PAYLOAD))
    broken["filings"]["recent"]["form"].pop()
    with pytest.raises(ValueError, match="columns are inconsistent"):
        parse_recent_filings(broken)


def test_client_requires_declared_contact_email():
    with pytest.raises(ValueError, match="contact email"):
        SecEdgarClient("sentinel-alpha")


def test_fetch_document_declares_user_agent_and_bounds_read():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(b"<html>Item 8.01</html>")

    client = SecEdgarClient("Sentinel Alpha admin@example.com", opener=opener)
    filing = parse_recent_filings(SEC_PAYLOAD)[0]
    assert client.fetch_filing_document(filing) == "<html>Item 8.01</html>"
    assert captured["request"].get_header("User-agent") == "Sentinel Alpha admin@example.com"
    assert captured["request"].full_url == filing.archive_reference
    assert captured["timeout"] == 15


def test_fetch_document_rejects_declared_oversize():
    def opener(request, timeout):
        return FakeResponse(b"small", content_length=MAX_DOCUMENT_BYTES + 1)

    client = SecEdgarClient("Sentinel Alpha admin@example.com", opener=opener)
    with pytest.raises(ValueError, match="exceeds size limit"):
        client.fetch_filing_document(parse_recent_filings(SEC_PAYLOAD)[0])


def test_fetch_document_rejects_streamed_oversize():
    def opener(request, timeout):
        return FakeResponse(b"x" * (MAX_DOCUMENT_BYTES + 1))

    client = SecEdgarClient("Sentinel Alpha admin@example.com", opener=opener)
    with pytest.raises(ValueError, match="exceeds size limit"):
        client.fetch_filing_document(parse_recent_filings(SEC_PAYLOAD)[0])


def test_fetch_document_rejects_binary_content_type():
    def opener(request, timeout):
        return FakeResponse(b"binary", content_type="application/octet-stream")

    client = SecEdgarClient("Sentinel Alpha admin@example.com", opener=opener)
    with pytest.raises(ValueError, match="unsupported SEC filing content type"):
        client.fetch_filing_document(parse_recent_filings(SEC_PAYLOAD)[0])
