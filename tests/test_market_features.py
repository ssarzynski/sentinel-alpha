from datetime import datetime, timedelta, timezone

import pytest

from app.models import MarketPriceObservation
from app.services.market_features import compute_market_features

BASE=datetime(2026,1,1,tzinfo=timezone.utc)


def rows(prices):
    return [MarketPriceObservation(id=i+1,asset="NVDA",observed_at=BASE+timedelta(days=i),price=p,currency="USD",source="TEST",source_family="MARKET",source_record_id=str(i),quality_status="accepted",metadata_json={}) for i,p in enumerate(prices)]


def test_feature_engine_calculates_multiple_horizons_and_trend():
    result=compute_market_features(rows([100+i for i in range(25)]))
    assert result.latest_price==124
    assert result.return_1==pytest.approx(124/123-1)
    assert result.return_5==pytest.approx(124/119-1)
    assert result.return_20==pytest.approx(124/104-1)
    assert result.trend_20=="up"
    assert result.volatility_20 is not None


def test_drawdown_is_measured_from_prior_observed_peak():
    result=compute_market_features(rows([100,120,110,90]))
    assert result.drawdown_from_peak==pytest.approx(90/120-1)


def test_short_history_does_not_invent_long_horizon_feature():
    result=compute_market_features(rows([100,101,102]))
    assert result.return_20 is None
    assert result.trend_20=="insufficient_history"


def test_mixed_assets_are_rejected():
    data=rows([100,101]);data[1].asset="BTC"
    with pytest.raises(ValueError,match="one asset"):
        compute_market_features(data)


def test_nonpositive_prices_are_rejected():
    with pytest.raises(ValueError,match="positive"):
        compute_market_features(rows([100,0,101]))
