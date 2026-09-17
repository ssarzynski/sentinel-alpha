from datetime import datetime, timedelta, timezone

import pytest

from app.portfolio import PositionInput, analyze_portfolio


NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)


def position(asset: str, asset_class: str, value: float, age_minutes: int = 5) -> PositionInput:
    return PositionInput(
        asset=asset,
        asset_class=asset_class,
        market_value=value,
        price_observed_at=NOW - timedelta(minutes=age_minutes),
    )


def test_long_only_nav_weights_and_concentration():
    result = analyze_portfolio(
        [
            position("NVDA", "equity", 600.0),
            position("MSFT", "equity", 300.0),
            position("BTC", "crypto", 100.0),
        ],
        as_of=NOW,
    )

    assert result.nav == pytest.approx(1000.0)
    assert result.gross_exposure == pytest.approx(1000.0)
    assert result.net_exposure == pytest.approx(1000.0)
    assert result.largest_position_weight == pytest.approx(0.6)
    assert result.herfindahl_index == pytest.approx(0.46)
    assert result.asset_class_exposure == {"crypto": 100.0, "equity": 900.0}
    assert [row.asset for row in result.positions] == ["NVDA", "MSFT", "BTC"]


def test_long_short_book_uses_absolute_weight_for_concentration():
    result = analyze_portfolio(
        [position("NVDA", "equity", 600.0), position("QQQ", "equity", -200.0)],
        as_of=NOW,
    )

    assert result.nav == pytest.approx(400.0)
    assert result.gross_exposure == pytest.approx(800.0)
    assert result.net_exposure == pytest.approx(400.0)
    assert result.largest_position_weight == pytest.approx(0.75)
    assert result.herfindahl_index == pytest.approx(0.625)
    assert result.asset_class_exposure == {"equity": 400.0}


def test_stale_prices_are_explicit_and_boundary_is_not_stale():
    result = analyze_portfolio(
        [
            position("NVDA", "equity", 100.0, age_minutes=30),
            position("BTC", "crypto", 100.0, age_minutes=31),
        ],
        as_of=NOW,
        stale_after=timedelta(minutes=30),
    )

    assert result.stale_assets == ("BTC",)
    by_asset = {row.asset: row for row in result.positions}
    assert by_asset["NVDA"].stale_price is False
    assert by_asset["BTC"].stale_price is True


def test_empty_portfolio_is_well_defined():
    result = analyze_portfolio([], as_of=NOW)
    assert result.nav == 0.0
    assert result.gross_exposure == 0.0
    assert result.largest_position_weight == 0.0
    assert result.herfindahl_index == 0.0
    assert result.asset_class_exposure == {}
    assert result.positions == ()


def test_naive_price_timestamp_is_interpreted_as_utc():
    result = analyze_portfolio(
        [
            PositionInput(
                asset="NVDA",
                asset_class="equity",
                market_value=100.0,
                price_observed_at=(NOW - timedelta(minutes=5)).replace(tzinfo=None),
            )
        ],
        as_of=NOW,
    )
    assert result.stale_assets == ()


def test_non_positive_staleness_window_is_rejected():
    with pytest.raises(ValueError, match="stale_after must be positive"):
        analyze_portfolio([], as_of=NOW, stale_after=timedelta(0))
