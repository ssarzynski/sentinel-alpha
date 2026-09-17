import pytest

from sentinel_alpha.watchlist import WatchAsset
from sentinel_alpha.watchlist_store import WatchlistStore


def test_watchlist_persists_across_instances(tmp_path):
    database = tmp_path / "sentinel.db"
    store = WatchlistStore(database)
    store.upsert(WatchAsset("nvda", "1045810"))
    restarted = WatchlistStore(database)
    assert restarted.active_assets() == [WatchAsset("NVDA", "1045810")]


def test_upsert_updates_existing_symbol_without_duplicate(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    store.upsert(WatchAsset("NVDA", "1045810"))
    store.upsert(WatchAsset("nvda", "999999"))
    assert store.active_assets() == [WatchAsset("NVDA", "999999")]


def test_inactive_asset_is_excluded_from_polling_list(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    store.upsert(WatchAsset("NVDA", "1045810"))
    store.upsert(WatchAsset("AAPL", "320193"), active=False)
    assert store.active_assets() == [WatchAsset("NVDA", "1045810")]


def test_asset_can_be_disabled_and_reenabled(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    store.upsert(WatchAsset("NVDA", "1045810"))
    assert store.set_active("nvda", False) is True
    assert store.active_assets() == []
    assert store.set_active("NVDA", True) is True
    assert store.active_assets() == [WatchAsset("NVDA", "1045810")]


def test_unknown_symbol_activation_returns_false(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    assert store.set_active("MISSING", False) is False


def test_invalid_cik_is_rejected(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    with pytest.raises(ValueError, match="digits only"):
        store.upsert(WatchAsset("NVDA", "not-a-cik"))
