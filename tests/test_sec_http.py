import httpx
import pytest

from app.ingestion.sec_http import SecHttpClient, SecHttpConfig, SecHttpError


def config(**overrides):
    values = dict(user_agent="SentinelAlpha/0.1 research@example.com", timeout_seconds=1, max_attempts=3, min_interval_seconds=0, backoff_seconds=0)
    values.update(overrides)
    return SecHttpConfig(**values)


def test_user_agent_requires_contact_email():
    with pytest.raises(ValueError, match="contact email"):
        SecHttpConfig(user_agent="SentinelAlpha")


def test_successful_sec_request_sends_identifying_user_agent():
    seen = {}
    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, text="<xml />")
    with SecHttpClient(config(), transport=httpx.MockTransport(handler)) as client:
        assert client.get_text("https://www.sec.gov/example.xml") == "<xml />"
    assert "research@example.com" in seen["ua"]


def test_non_sec_domain_is_rejected_before_transport():
    called = False
    def handler(_request):
        nonlocal called; called = True
        return httpx.Response(200, text="bad")
    with SecHttpClient(config(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="HTTPS SEC domains"):
            client.get_text("https://example.com/form4.xml")
    assert called is False


def test_429_is_retried_then_succeeds():
    attempts = 0
    def handler(_request):
        nonlocal attempts; attempts += 1
        return httpx.Response(429 if attempts < 3 else 200, text="ok")
    with SecHttpClient(config(), transport=httpx.MockTransport(handler)) as client:
        assert client.get_text("https://data.sec.gov/submissions/test.json") == "ok"
    assert attempts == 3


def test_500_exhaustion_fails_closed():
    with SecHttpClient(config(max_attempts=2), transport=httpx.MockTransport(lambda _: httpx.Response(503, text="busy"))) as client:
        with pytest.raises(SecHttpError, match="503"):
            client.get_text("https://www.sec.gov/test")


def test_timeout_is_retried_and_fails_closed():
    attempts = 0
    def handler(request):
        nonlocal attempts; attempts += 1
        raise httpx.ReadTimeout("timeout", request=request)
    with SecHttpClient(config(max_attempts=2), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SecHttpError, match="after 2 attempts"):
            client.get_text("https://www.sec.gov/test")
    assert attempts == 2


def test_empty_success_response_is_rejected():
    with SecHttpClient(config(), transport=httpx.MockTransport(lambda _: httpx.Response(200, text="  "))) as client:
        with pytest.raises(SecHttpError, match="empty response"):
            client.get_text("https://www.sec.gov/test")


def test_rate_limiter_waits_between_requests():
    times = iter([0.0, 0.0, 0.05, 0.05])
    sleeps = []
    client = SecHttpClient(
        config(min_interval_seconds=0.1),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="ok")),
        clock=lambda: next(times), sleep=sleeps.append,
    )
    try:
        client.get_text("https://www.sec.gov/a")
        client.get_text("https://www.sec.gov/b")
    finally:
        client.close()
    assert sleeps == [pytest.approx(0.05)]
