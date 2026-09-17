import json
from urllib.error import HTTPError, URLError

import pytest

from sentinel_alpha.sec_ingestion import SEC_MAX_ATTEMPTS, SecEdgarClient


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


def test_consecutive_requests_are_paced():
    times = iter([0.0, 0.0, 0.05, 0.20])
    sleeps = []

    def clock():
        return next(times)

    def opener(request, timeout):
        return FakeResponse(json.dumps({"cik": "1045810"}).encode())

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener, sleeper=sleeps.append, clock=clock)
    client.fetch_submissions("1045810")
    client.fetch_submissions("1045810")
    assert sleeps == [pytest.approx(0.15)]


def test_retryable_http_error_uses_bounded_backoff_then_succeeds():
    attempts = 0
    sleeps = []

    def opener(request, timeout):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise HTTPError(request.full_url, 503, "busy", {}, None)
        return FakeResponse(json.dumps({"cik": "1045810"}).encode())

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener, sleeper=sleeps.append, clock=lambda: 1.0)
    payload = client.fetch_submissions("1045810")
    assert payload["cik"] == "1045810"
    assert attempts == 3
    assert 1.0 in sleeps and 2.0 in sleeps


def test_retry_exhaustion_fails_closed():
    attempts = 0

    def opener(request, timeout):
        nonlocal attempts
        attempts += 1
        raise URLError("offline")

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener, sleeper=lambda _: None, clock=lambda: 1.0)
    with pytest.raises(URLError):
        client.fetch_submissions("1045810")
    assert attempts == SEC_MAX_ATTEMPTS


def test_non_retryable_http_error_is_not_retried():
    attempts = 0

    def opener(request, timeout):
        nonlocal attempts
        attempts += 1
        raise HTTPError(request.full_url, 404, "missing", {}, None)

    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=opener, sleeper=lambda _: None, clock=lambda: 1.0)
    with pytest.raises(HTTPError):
        client.fetch_submissions("1045810")
    assert attempts == 1


def test_non_object_json_is_rejected():
    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=lambda request, timeout: FakeResponse(b"[]"))
    with pytest.raises(ValueError, match="JSON object"):
        client.fetch_submissions("1045810")


def test_malformed_json_is_not_silently_accepted():
    client = SecEdgarClient("SentinelAlpha contact@example.com", opener=lambda request, timeout: FakeResponse(b"not-json"))
    with pytest.raises(json.JSONDecodeError):
        client.fetch_submissions("1045810")
