import pytest

from app.worker import parse_watchlist


def test_parse_watchlist_normalizes_and_deduplicates():
    items = parse_watchlist("nvda:1045810, MSFT:789019,nvda:1045810")
    assert [(x.ticker, x.cik) for x in items] == [
        ("NVDA", "0001045810"), ("MSFT", "0000789019")
    ]


def test_invalid_or_empty_watchlist_fails_closed():
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_watchlist(" , ")
    with pytest.raises(ValueError, match="TICKER:CIK"):
        parse_watchlist("NVDA")
    with pytest.raises(ValueError, match="invalid watchlist"):
        parse_watchlist("NVDA:not-a-cik")
