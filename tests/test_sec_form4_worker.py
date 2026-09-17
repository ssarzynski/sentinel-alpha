import pytest

from app.workers.sec_form4_worker import _watchlist


def test_watchlist_parses_multiple_companies(monkeypatch):
    monkeypatch.setenv("SENTINEL_SEC_WATCHLIST", "1045810:nvda, 320193:AAPL")
    items = _watchlist()
    assert [(item.cik, item.ticker) for item in items] == [("1045810", "NVDA"), ("320193", "AAPL")]


def test_watchlist_has_safe_default(monkeypatch):
    monkeypatch.delenv("SENTINEL_SEC_WATCHLIST", raising=False)
    items = _watchlist()
    assert [(item.cik, item.ticker) for item in items] == [("1045810", "NVDA")]


def test_invalid_watchlist_fails_closed(monkeypatch):
    monkeypatch.setenv("SENTINEL_SEC_WATCHLIST", "NVDA")
    with pytest.raises(ValueError, match="CIK:TICKER"):
        _watchlist()


def test_empty_watchlist_fails_closed(monkeypatch):
    monkeypatch.setenv("SENTINEL_SEC_WATCHLIST", " , ")
    with pytest.raises(ValueError, match="cannot be empty"):
        _watchlist()
