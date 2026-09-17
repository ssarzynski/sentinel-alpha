import json
from urllib.parse import parse_qs, urlparse

import pytest

from sentinel_alpha.alpha_vantage_ingestion import (
    AlphaVantageClient,
    daily_bar_to_records,
)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def payload():
    return {
        "Meta Data": {"2. Symbol": "NVDA"},
        "Time Series (Daily)": {
            "2026-09-17": {
                "1. open": "180.00",
                "2. high": "185.00",
                "3. low": "179.00",
                "4. close": "184.25",
                "5. volume": "123456789",
            }
        },
    }


def test_api_key_is_required_before_network_access():
    with pytest.raises(ValueError, match="API_KEY"):
        AlphaVantageClient("  ")


def test_daily_request_uses_documented_endpoint_and_symbol():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return Response(payload())

    bar = AlphaVantageClient("secret", opener=opener).latest_daily("nvda")
    query = parse_qs(urlparse(seen["url"]).query)
    assert query["function"] == ["TIME_SERIES_DAILY"]
    assert query["symbol"] == ["NVDA"]
    assert query["outputsize"] == ["compact"]
    assert query["apikey"] == ["secret"]
    assert bar.symbol == "NVDA"
    assert bar.close == 184.25
    assert bar.volume == 123456789


def test_price_and_volume_share_one_market_independence_group():
    client = AlphaVantageClient("secret", opener=lambda *_args, **_kwargs: Response(payload()))
    records = daily_bar_to_records(client.latest_daily("NVDA"))
    assert {r.observation.metric for r in records} == {"daily_close", "daily_volume"}
    assert {r.source.independence_key for r in records} == {"alpha_vantage"}


@pytest.mark.parametrize(
    "bad_payload, error",
    [
        ({"Note": "rate limit"}, RuntimeError),
        ({"Information": "service unavailable"}, RuntimeError),
        ({"Error Message": "bad symbol"}, ValueError),
        ({}, ValueError),
    ],
)
def test_provider_failures_fail_closed(bad_payload, error):
    client = AlphaVantageClient(
        "secret", opener=lambda *_args, **_kwargs: Response(bad_payload)
    )
    with pytest.raises(error):
        client.latest_daily("NVDA")
