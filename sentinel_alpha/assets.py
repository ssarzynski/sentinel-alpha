"""Initial Sentinel Alpha MVP asset universe."""

from .models import Asset


MVP_ASSETS: tuple[Asset, ...] = (
    Asset("NVDA", "equity"),
    Asset("AMD", "equity"),
    Asset("TSM", "equity"),
    Asset("AVGO", "equity"),
    Asset("ASML", "equity"),
    Asset("MSFT", "equity"),
    Asset("AAPL", "equity"),
    Asset("AMZN", "equity"),
    Asset("META", "equity"),
    Asset("GOOGL", "equity"),
    Asset("BTC", "crypto"),
    Asset("ETH", "crypto"),
    Asset("USDC", "stablecoin"),
    Asset("USDT", "stablecoin"),
    Asset("DAI", "stablecoin"),
)
