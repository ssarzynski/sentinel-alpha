import io
import json

import pytest

from sentinel_alpha.alpha_vantage_ingestion import AlphaVantageClient
from sentinel_alpha.resource_budget import ResourceBudget
from sentinel_alpha.resource_metrics import ResourceMetrics


class Response:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self):
        return json.dumps({"Time Series (Daily)":{"2026-09-18":{"1. open":"1","2. high":"2","3. low":"1","4. close":"2","5. volume":"10"}}}).encode()


def test_provider_budget_blocks_request_before_network():
    network_calls=[]
    def opener(request, timeout):
        network_calls.append(request.full_url)
        return Response()

    metrics=ResourceMetrics()
    budget=ResourceBudget(max_provider_calls_per_run=2)
    client=AlphaVantageClient("secret-test-key",opener=opener,metrics=metrics,budget=budget)
    client.latest_daily("NVDA")
    client.latest_daily("NVDA")
    with pytest.raises(RuntimeError,match="budget exhausted"):
        client.latest_daily("NVDA")
    assert len(network_calls)==2
    assert client.provider_calls==2
    assert metrics.provider_calls==2


def test_failed_network_attempt_is_still_counted():
    def opener(request, timeout):
        raise OSError("network unavailable")
    metrics=ResourceMetrics()
    client=AlphaVantageClient("secret-test-key",opener=opener,metrics=metrics)
    with pytest.raises(OSError):
        client.latest_daily("NVDA")
    assert client.provider_calls==1
    assert metrics.provider_calls==1


def test_metrics_do_not_expose_api_key():
    metrics=ResourceMetrics()
    client=AlphaVantageClient("super-secret-key",opener=lambda request,timeout: Response(),metrics=metrics)
    client.latest_daily("NVDA")
    assert "super-secret-key" not in repr(metrics.snapshot())
