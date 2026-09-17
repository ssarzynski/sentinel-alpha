from datetime import datetime, timedelta, timezone

import pytest

from app.market_data import PriceObservationInput, assess_cross_source_quality, build_aligned_returns, deduplicate_observations

T0 = datetime(2026, 9, 17, 16, 0, tzinfo=timezone.utc)


def obs(source: str, family: str, price: float, record: str = "1") -> PriceObservationInput:
    return PriceObservationInput("nvda", T0, price, "usd", source, family, record)


def test_normalization_dedupes_identical_provider_record():
    rows = deduplicate_observations([obs("ProviderA", "exchange", 100), obs("ProviderA", "exchange", 100)])
    assert len(rows) == 1
    assert rows[0].asset == "NVDA"
    assert rows[0].currency == "USD"


def test_conflicting_duplicate_provider_record_is_rejected():
    with pytest.raises(ValueError, match="conflicting duplicate"):
        deduplicate_observations([obs("ProviderA", "exchange", 100), obs("ProviderA", "exchange", 101)])


def test_cross_source_quality_accepts_independent_agreement():
    result = assess_cross_source_quality([obs("A", "exchange", 100), obs("B", "institutional", 100.5)])
    assert result.quality_status == "accepted"
    assert result.independent_source_families == 2
    assert result.consensus_price == pytest.approx(100.25)


def test_same_family_does_not_count_as_independent_confirmation():
    result = assess_cross_source_quality([obs("A", "aggregator", 100), obs("B", "aggregator", 100.1)])
    assert result.quality_status == "insufficient_independence"
    assert result.independent_source_families == 1


def test_large_cross_source_disagreement_is_flagged():
    result = assess_cross_source_quality([obs("A", "exchange", 100), obs("B", "institutional", 110)])
    assert result.quality_status == "source_disagreement"
    assert result.max_relative_deviation > 0.02


def test_invalid_price_is_rejected():
    with pytest.raises(ValueError, match="finite and positive"):
        deduplicate_observations([obs("A", "exchange", 0)])


def test_quality_comparison_requires_same_timestamp():
    other = PriceObservationInput("NVDA", T0 + timedelta(minutes=1), 100, "USD", "B", "institutional", "2")
    with pytest.raises(ValueError, match="one asset, timestamp and currency"):
        assess_cross_source_quality([obs("A", "exchange", 100), other])


def test_aligned_returns_use_only_shared_timestamps():
    t1, t2, t3 = T0, T0 + timedelta(days=1), T0 + timedelta(days=2)
    result = build_aligned_returns({
        "NVDA": [(t1, 100), (t2, 110), (t3, 121)],
        "BTC": [(t1, 200), (t2, 180), (t3, 198), (t3 + timedelta(hours=1), 205)],
    })
    assert result["NVDA"] == pytest.approx([0.1, 0.1])
    assert result["BTC"] == pytest.approx([-0.1, 0.1])


def test_aligned_returns_reject_insufficient_overlap():
    with pytest.raises(ValueError, match="two aligned"):
        build_aligned_returns({"A": [(T0, 100)], "B": [(T0, 200)]})
