from datetime import datetime, timezone

import pytest

from sentinel_alpha.market_features import MarketFeatures
from sentinel_alpha.market_outcomes import ForwardOutcome
from sentinel_alpha.market_research import summarize_outcomes
from sentinel_alpha.research_examples import ResearchExample

NOW = datetime(2020, 1, 1, tzinfo=timezone.utc)


def example(ret5, ret20=None, trend=0.1):
    features = MarketFeatures("NVDA", NOW, 10, 100.0, 0.01, 0.05, 0.2, 0.1, trend)
    outcomes = [ForwardOutcome("NVDA", NOW, 100.0, 5, NOW if ret5 is not None else None, None, ret5)]
    if ret20 is not None:
        outcomes.append(ForwardOutcome("NVDA", NOW, 100.0, 20, NOW, None, ret20))
    return ResearchExample("NVDA", NOW, NOW, NOW, features, tuple(outcomes))


def test_summary_reports_sample_size_center_hit_rate_and_uncertainty():
    result = summarize_outcomes([example(0.10), example(-0.05), example(0.20)])
    five = result[0]
    assert five.horizon == 5
    assert five.sample_size == 3
    assert five.mean_return == pytest.approx((0.10 - 0.05 + 0.20) / 3)
    assert five.median_return == pytest.approx(0.10)
    assert five.positive_rate == pytest.approx(2 / 3)
    assert five.standard_deviation is not None
    assert five.standard_error == pytest.approx(five.standard_deviation / (3 ** 0.5))


def test_condition_filters_examples_without_rewriting_labels():
    result = summarize_outcomes(
        [example(0.10, trend=0.2), example(-0.10, trend=-0.2)],
        condition=lambda item: item.features.trend_5 is not None and item.features.trend_5 > 0,
    )
    assert result[0].sample_size == 1
    assert result[0].mean_return == pytest.approx(0.10)
    assert result[0].standard_error is None


def test_missing_future_labels_are_not_counted_as_zero():
    result = summarize_outcomes([example(None), example(0.05)])
    assert result[0].sample_size == 1
    assert result[0].mean_return == pytest.approx(0.05)
