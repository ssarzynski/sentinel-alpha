import json
from datetime import datetime, timezone

import pytest

from sentinel_alpha.messari_ingestion import MessariAsset, MessariClient, asset_to_record, parse_assets


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def asset_payload():
    return {
        "error": None,
        "data": [{
            "id": "btc-id",
            "name": "Bitcoin",
            "slug": "bitcoin",
            "symbol": "BTC",
            "rank": 1,
            "hasMarketData": True,
        }],
    }


def test_parse_assets():
    assets = parse_assets(asset_payload())
    assert assets == [MessariAsset("btc-id", "Bitcoin", "BTC", "bitcoin", 1, True)]


def test_client_uses_documented_api_key_header_and_filters_market_coverage():
    captured = {}

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(asset_payload())

    client = MessariClient("secret-key", opener=opener)
    assets = client.list_assets(search="BTC")
    headers = {key.lower(): value for key, value in captured["request"].header_items()}
    assert assets[0].symbol == "BTC"
    assert headers["x-messari-api-key"] == "secret-key"
    assert "search=BTC" in captured["request"].full_url
    assert "hasMarketData=true" in captured["request"].full_url
    assert captured["timeout"] == 15


def test_market_record_is_independent_from_sec_provider():
    record = asset_to_record(
        MessariAsset("btc-id", "Bitcoin", "BTC", "bitcoin", 1, True),
        datetime(2026, 9, 17, tzinfo=timezone.utc),
    )
    assert record.observation.asset == "BTC"
    assert record.source.provider == "Messari"
    assert record.source.independence_key == "messari"


def test_missing_exact_symbol_fails_closed():
    def opener(request, timeout):
        return FakeResponse(asset_payload())

    client = MessariClient("secret-key", opener=opener)
    with pytest.raises(ValueError, match="not found"):
        client.market_coverage_record("ETH")


def test_api_error_is_rejected():
    def opener(request, timeout):
        return FakeResponse({"error": "unauthorized", "data": []})

    client = MessariClient("secret-key", opener=opener)
    with pytest.raises(ValueError, match="Messari API error"):
        client.list_assets()
