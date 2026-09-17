"""Messari crypto asset and price-timeseries ingestion for Sentinel Alpha."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .provenance import NormalizedRecord
from .providers import MESSARI_MARKET, MESSARI_RESEARCH

MESSARI_ASSETS_URL = "https://api.messari.io/metrics/v2/assets"


@dataclass(frozen=True)
class MessariAsset:
    asset_id: str
    name: str
    symbol: str
    slug: str
    rank: int | None
    has_market_data: bool


@dataclass(frozen=True)
class PriceCandle:
    observed_at: datetime
    open: float
    high: float
    low: float
    close: float

    @property
    def return_pct(self) -> float:
        if self.open == 0:
            raise ValueError("price candle open cannot be zero")
        return ((self.close - self.open) / self.open) * 100.0


def parse_assets(payload: dict[str, Any]) -> list[MessariAsset]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("Messari assets response must contain a data list")
    assets: list[MessariAsset] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Messari asset entries must be objects")
        symbol = str(item.get("symbol", "")).strip().upper()
        asset_id = str(item.get("id", "")).strip()
        if not symbol or not asset_id:
            raise ValueError("Messari asset requires id and symbol")
        assets.append(
            MessariAsset(
                asset_id=asset_id,
                name=str(item.get("name", "")).strip(),
                symbol=symbol,
                slug=str(item.get("slug", "")).strip(),
                rank=item.get("rank") if isinstance(item.get("rank"), int) else None,
                has_market_data=item.get("hasMarketData") is True,
            )
        )
    return assets


def parse_price_timeseries(payload: dict[str, Any]) -> list[PriceCandle]:
    data = payload.get("data")
    points = data.get("points") if isinstance(data, dict) else None
    if not isinstance(points, list):
        raise ValueError("Messari price response must contain data.points")
    candles: list[PriceCandle] = []
    for point in points:
        if not isinstance(point, list) or len(point) < 5:
            raise ValueError("Messari price point must contain timestamp and OHLC values")
        timestamp, open_price, high, low, close = point[:5]
        if not isinstance(timestamp, (int, float)):
            raise ValueError("Messari price timestamp must be numeric")
        try:
            values = tuple(float(value) for value in (open_price, high, low, close))
        except (TypeError, ValueError) as exc:
            raise ValueError("Messari OHLC values must be numeric") from exc
        candles.append(
            PriceCandle(
                observed_at=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
            )
        )
    return candles


def asset_to_record(asset: MessariAsset, observed_at: datetime | None = None) -> NormalizedRecord:
    observed_at = observed_at or datetime.now(timezone.utc)
    return MESSARI_RESEARCH.normalize(
        {
            "asset": asset.symbol,
            "metric": "market_data_coverage",
            "value": asset.has_market_data,
            "statement": f"Messari market-data coverage for {asset.symbol}",
            "reference": f"messari:asset:{asset.asset_id}",
            "quality": "high",
        },
        observed_at,
    )


def price_candle_to_record(symbol: str, asset_identifier: str, candle: PriceCandle, granularity: str) -> NormalizedRecord:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol is required")
    direction = "up" if candle.close > candle.open else "down" if candle.close < candle.open else "flat"
    return MESSARI_MARKET.normalize(
        {
            "asset": normalized,
            "metric": f"price_return_{granularity}",
            "value": {
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "return_pct": candle.return_pct,
                "direction": direction,
            },
            "statement": f"Messari {granularity} price candle for {normalized}",
            "reference": f"messari:price:{asset_identifier}:{granularity}:{int(candle.observed_at.timestamp())}",
            "quality": "high",
        },
        candle.observed_at,
    )


class MessariClient:
    """Authenticated client for documented Messari v2 asset endpoints."""

    def __init__(self, api_key: str, opener: Callable[..., Any] = urlopen) -> None:
        if not api_key.strip():
            raise ValueError("Messari API key is required")
        self.api_key = api_key.strip()
        self.opener = opener

    def _request_json(self, url: str) -> dict[str, Any]:
        request = Request(url, headers={"X-Messari-API-Key": self.api_key, "Accept": "application/json"})
        with self.opener(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Messari response must be a JSON object")
        if payload.get("error"):
            raise ValueError(f"Messari API error: {payload['error']}")
        return payload

    def list_assets(self, *, search: str | None = None, limit: int = 10, page: int = 1) -> list[MessariAsset]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if page < 1:
            raise ValueError("page must be positive")
        params: dict[str, str | int] = {"limit": limit, "page": page, "hasMarketData": "true"}
        if search and search.strip():
            params["search"] = search.strip()
        return parse_assets(self._request_json(f"{MESSARI_ASSETS_URL}?{urlencode(params)}"))

    def price_timeseries(
        self,
        asset_identifier: str,
        *,
        granularity: str = "1h",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PriceCandle]:
        identifier = asset_identifier.strip()
        if not identifier:
            raise ValueError("asset_identifier is required")
        if granularity not in {"1h", "1d"}:
            raise ValueError("asset price granularity must be 1h or 1d")
        params: dict[str, str] = {}
        if start is not None:
            params["start"] = _iso_utc(start)
        if end is not None:
            params["end"] = _iso_utc(end)
        url = f"{MESSARI_ASSETS_URL}/{identifier}/metrics/price/time-series/{granularity}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return parse_price_timeseries(self._request_json(url))

    def price_records(
        self,
        symbol: str,
        asset_identifier: str,
        *,
        granularity: str = "1h",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[NormalizedRecord]:
        return [
            price_candle_to_record(symbol, asset_identifier, candle, granularity)
            for candle in self.price_timeseries(asset_identifier, granularity=granularity, start=start, end=end)
        ]

    def market_coverage_record(self, symbol: str) -> NormalizedRecord:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")
        matches = self.list_assets(search=normalized, limit=10)
        exact = next((asset for asset in matches if asset.symbol == normalized), None)
        if exact is None:
            raise ValueError(f"Messari asset not found: {normalized}")
        return asset_to_record(exact)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
