import json

import pytest

from sentinel_alpha.sec_ingestion import SecEdgarClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_sec_client_requests_plain_json_without_compression():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(json.dumps({"cik": "1045810"}).encode())

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener)
    payload = client.fetch_submissions("1045810")
    headers = {key.lower(): value for key, value in captured["request"].header_items()}
    assert payload["cik"] == "1045810"
    assert headers["accept"] == "application/json"
    assert "accept-encoding" not in headers
    assert captured["timeout"] == 15


def test_non_object_json_is_rejected():
    def opener(request, timeout):
        return FakeResponse(b"[]")

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener)
    with pytest.raises(ValueError, match="JSON object"):
        client.fetch_submissions("1045810")


def test_malformed_json_is_not_silently_accepted():
    def opener(request, timeout):
        return FakeResponse(b"not-json")

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener)
    with pytest.raises(json.JSONDecodeError):
        client.fetch_submissions("1045810")
