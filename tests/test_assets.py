from sentinel_alpha.assets import MVP_ASSETS


def test_mvp_asset_universe_has_15_assets() -> None:
    assert len(MVP_ASSETS) == 15


def test_mvp_asset_symbols_are_unique() -> None:
    symbols = [asset.symbol for asset in MVP_ASSETS]
    assert len(symbols) == len(set(symbols))


def test_required_anchor_assets_exist() -> None:
    symbols = {asset.symbol for asset in MVP_ASSETS}
    assert {"NVDA", "BTC", "ETH"}.issubset(symbols)
