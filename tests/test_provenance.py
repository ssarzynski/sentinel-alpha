from datetime import datetime, timezone

import pytest

from sentinel_alpha.provenance import (
    SourceIdentity,
    independent_confirmation_keys,
    normalize_mapping,
    normalize_record,
)


def test_normalize_record_canonicalizes_asset_metric_and_quality():
    now = datetime.now(timezone.utc)
    source = SourceIdentity(source_id="sec-8k", provider="SEC", channel="filings")
    record = normalize_record(
        asset=" nvda ",
        metric=" MATERIAL_EVENT ",
        value=True,
        source=source,
        observed_at=now,
        statement="8-K filed",
        quality=" HIGH ",
    )
    assert record.observation.asset == "NVDA"
    assert record.observation.metric == "material_event"
    assert record.observation.quality == "high"
    assert record.source.independence_key == "sec:filings"


def test_same_provider_channel_counts_once_even_with_multiple_records():
    now = datetime.now(timezone.utc)
    source_a = SourceIdentity(source_id="messari-news", provider="Messari", channel="research")
    source_b = SourceIdentity(source_id="messari-feed", provider="Messari", channel="research")
    records = [
        normalize_record(
            asset="BTC",
            metric="sentiment",
            value=1,
            source=source_a,
            observed_at=now,
            statement="positive",
        ),
        normalize_record(
            asset="BTC",
            metric="volume",
            value=2,
            source=source_b,
            observed_at=now,
            statement="volume increased",
        ),
    ]
    assert independent_confirmation_keys(records) == {"messari:research"}


def test_different_provider_channels_count_independently():
    now = datetime.now(timezone.utc)
    records = [
        normalize_mapping(
            {"asset": "NVDA", "metric": "filing", "statement": "8-K"},
            source=SourceIdentity("sec", "SEC", "filings"),
            observed_at=now,
        ),
        normalize_mapping(
            {"asset": "NVDA", "metric": "market", "statement": "screen signal"},
            source=SourceIdentity("finviz", "Finviz", "screening"),
            observed_at=now,
        ),
    ]
    assert len(independent_confirmation_keys(records)) == 2


def test_incomplete_source_identity_is_rejected():
    with pytest.raises(ValueError, match="complete source identity"):
        normalize_record(
            asset="ETH",
            metric="price",
            value=1,
            source=SourceIdentity("", "Messari", "market"),
            observed_at=datetime.now(timezone.utc),
            statement="price observation",
        )
