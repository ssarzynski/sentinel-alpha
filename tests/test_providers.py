from datetime import datetime, timezone

import pytest

from sentinel_alpha.providers import PROVIDERS, get_provider


def test_required_provider_adapters_are_registered():
    assert {"sec", "finviz", "messari", "invo"}.issubset(PROVIDERS)


def test_provider_normalizes_payload_with_stable_provenance():
    adapter = get_provider("SEC")
    record = adapter.normalize(
        {
            "asset": "nvda",
            "metric": "8k",
            "value": True,
            "statement": "material filing",
            "reference": "example-reference",
            "quality": "high",
        },
        datetime.now(timezone.utc),
    )
    assert record.observation.asset == "NVDA"
    assert record.source.independence_key == "sec:filings"
    assert record.evidence.reference == "example-reference"


def test_provider_sources_remain_independent():
    sec = get_provider("sec").source.independence_key
    finviz = get_provider("finviz").source.independence_key
    messari = get_provider("messari").source.independence_key
    invo = get_provider("invo").source.independence_key
    assert len({sec, finviz, messari, invo}) == 4


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="unknown provider"):
        get_provider("not-a-provider")
