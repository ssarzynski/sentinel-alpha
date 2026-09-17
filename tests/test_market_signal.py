from datetime import datetime, timezone

import pytest

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.evidence_roles import EvidenceRole
from sentinel_alpha.market_signal import (
    MARKET_SIGNAL_RULE_VERSION,
    MarketBaseline,
    classify_daily_bar,
)
from sentinel_alpha.provenance import independent_confirmation_keys

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


def bar(close=102.0, volume=1_500_000):
    return DailyEquityBar(
        symbol="NVDA",
        observed_at=NOW,
        open=100.0,
        high=max(103.0, close),
        low=99.0,
        close=close,
        volume=volume,
    )


def test_rule_is_versioned():
    assert MARKET_SIGNAL_RULE_VERSION == "market-v1"


def test_market_signal_requires_momentum_and_volume():
    result = classify_daily_bar(bar(close=103.0, volume=1_600_000), MarketBaseline(100.0, 1_000_000))
    assert result.qualifies is True
    assert {item.role for item in result.evidence} == {EvidenceRole.SUPPORT}


def test_momentum_without_volume_remains_context():
    result = classify_daily_bar(bar(close=103.0, volume=1_200_000), MarketBaseline(100.0, 1_000_000))
    assert result.qualifies is False
    assert {item.role for item in result.evidence} == {EvidenceRole.CONTEXT}


def test_volume_without_momentum_remains_context():
    result = classify_daily_bar(bar(close=101.0, volume=2_000_000), MarketBaseline(100.0, 1_000_000))
    assert result.qualifies is False
    assert {item.role for item in result.evidence} == {EvidenceRole.CONTEXT}


def test_price_and_volume_still_count_as_one_provider_confirmation():
    result = classify_daily_bar(bar(close=103.0, volume=2_000_000), MarketBaseline(100.0, 1_000_000))
    support = [item.record for item in result.evidence if item.role is EvidenceRole.SUPPORT]
    assert independent_confirmation_keys(support) == {"alpha_vantage"}


def test_threshold_boundary_is_deterministic():
    result = classify_daily_bar(bar(close=102.0, volume=1_500_000), MarketBaseline(100.0, 1_000_000))
    assert result.qualifies is True


@pytest.mark.parametrize(
    "baseline",
    [MarketBaseline(0.0, 1_000_000), MarketBaseline(100.0, 0.0), MarketBaseline(-1.0, 1.0)],
)
def test_invalid_baseline_fails_closed(baseline):
    with pytest.raises(ValueError):
        classify_daily_bar(bar(), baseline)
