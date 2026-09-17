import json
from datetime import datetime, timezone

import pytest

from sentinel_alpha.messari_ingestion import MessariClient, parse_price_timeseries, price_candle_to_record


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_parse_price_timeseries_ohlc():
    candles = parse_price_timeseries({"error": None, "data": {"points": [[1748736000, 100, 110, 95, 105]]}})
    assert len(candles) == 1
    assert candles[0].open == 100.0
    assert candles[0].close == 105.0
    assert candles[0].return_pct == 5.0


def test_price_timeseries_uses_documented_v2_endpoint_and_auth_header():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["key"] = request.headers["X-messari-api-key"]
        captured["timeout"] = timeout
        return FakeResponse({"error": None, "data": {"points": [[1748736000, 100, 110, 95, 105]]}})

    client = MessariClient("secret", opener=opener)
    candles = client.price_timeseries(
        "bitcoin",
        granularity="1h",
        start=datetime(2026, 9, 17, 16, tzinfo=timezone.utc),
        end=datetime(2026, 9, 17, 18, tzinfo=timezone.utc),
    )
    assert len(candles) == 1
    assert "/metrics/v2/assets/bitcoin/metrics/price/time-series/1h" in captured["url"]
    assert "start=2026-09-17T16%3A00%3A00Z" in captured["url"]
    assert captured["key"] == "secret"
    assert captured["timeout"] == 15


def test_price_record_has_market_provenance_and_direction():
    candle = parse_price_timeseries({"data": {"points": [[1748736000, 100, 110, 95, 105]]}})[0]
    record = price_candle_to_record("btc", "bitcoin", candle, "1h")
    assert record.observation.asset == "BTC"
    assert record.observation.metric == "price_return_1h"
    assert record.observation.value["direction"] == "up"
    assert record.observation.value["return_pct"] == 5.0
    assert record.source.provider == "Messari"
    assert record.source.channel == "market"
    assert record.source.independence_key == "messari"


def test_invalid_granularity_is_rejected_without_network_call():
    client = MessariClient("secret", opener=lambda *args, **kwargs: pytest.fail("network should not be called"))
    with pytest.raises(ValueError, match="1h or 1d"):
        client.price_timeseries("bitcoin", granularity="5m")


def test_malformed_price_point_fails_closed():
    with pytest.raises(ValueError, match="timestamp and OHLC"):
        parse_price_timeseries({"data": {"points": [[1748736000, 100]]}})
