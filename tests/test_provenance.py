from datetime import datetime, timezone

import pytest

from sentinel_alpha.provenance import (
    SourceIdentity,
    independent_confirmation_keys,
    normalize_mapping,
    normalize_record,
)


def make_record(source: SourceIdentity, metric: str = "signal"):
    return normalize_record(
        asset="NVDA",
        metric=metric,
        value=True,
        source=source,
        observed_at=datetime.now(timezone.utc),
        statement="confirmation",
    )


def test_normalize_record_canonicalizes_asset_metric_and_quality():
    source = SourceIdentity(source_id="sec-8k", provider="SEC", channel="filings")
    record = normalize_record(
        asset=" nvda ",
        metric=" MATERIAL_EVENT ",
        value=True,
        source=source,
        observed_at=datetime.now(timezone.utc),
        statement="8-K filed",
        quality=" HIGH ",
    )
    assert record.observation.asset == "NVDA"
    assert record.observation.metric == "material_event"
    assert record.observation.quality == "high"
    assert record.source.independence_key == "sec"


def test_same_provider_different_channels_count_once_by_default():
    records = [
        make_record(SourceIdentity("messari-news", "Messari", "research"), "sentiment"),
        make_record(SourceIdentity("messari-market", "Messari", "market"), "volume"),
    ]
    assert independent_confirmation_keys(records) == {"messari"}


def test_different_providers_count_independently():
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
    assert independent_confirmation_keys(records) == {"sec", "finviz"}


def test_different_vendor_labels_same_upstream_group_count_once():
    records = [
        make_record(SourceIdentity("vendor-a", "VendorA", "market", "upstream-x")),
        make_record(SourceIdentity("vendor-b", "VendorB", "research", "upstream-x")),
    ]
    assert independent_confirmation_keys(records) == {"upstream-x"}


def test_blank_independent_group_is_rejected():
    with pytest.raises(ValueError, match="independent_group cannot be blank"):
        make_record(SourceIdentity("vendor", "Vendor", "market", "   "))


def test_incomplete_source_identity_is_rejected():
    with pytest.raises(ValueError, match="complete source identity"):
        make_record(SourceIdentity("", "Messari", "market"))


def test_mixed_explicit_and_implicit_lineage_fails_closed():
    records = [
        make_record(SourceIdentity("fred-series", "FRED", "macro", "federal-reserve")),
        make_record(SourceIdentity("macro-reseller", "VendorAlias", "macro")),
    ]
    assert independent_confirmation_keys(records) == {"federal-reserve"}


def test_explicit_distinct_upstream_groups_remain_independent():
    records = [
        make_record(SourceIdentity("sec", "SEC", "filings", "sec-edgar")),
        make_record(SourceIdentity("issuer", "NVIDIA", "investor-relations", "nvidia-ir")),
    ]
    assert independent_confirmation_keys(records) == {"sec-edgar", "nvidia-ir"}
