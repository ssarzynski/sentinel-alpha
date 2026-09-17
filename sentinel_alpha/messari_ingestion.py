"""Messari crypto market-coverage ingestion for Sentinel Alpha."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .provenance import NormalizedRecord
from .providers import MESSARI_RESEARCH

MESSARI_ASSETS_URL = "https://api.messari.io/metrics/v2/assets"


@dataclass(frozen=True)
class MessariAsset:
    asset_id: str
    name: str
    symbol: str
    slug: str
    rank: int | None
    has_market_data: bool


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


class MessariClient:
    """Small authenticated client for Messari's documented v2 assets endpoint."""

    def __init__(self, api_key: str, opener: Callable[..., Any] = urlopen) -> None:
        if not api_key.strip():
            raise ValueError("Messari API key is required")
        self.api_key = api_key.strip()
        self.opener = opener

    def list_assets(self, *, search: str | None = None, limit: int = 10, page: int = 1) -> list[MessariAsset]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if page < 1:
            raise ValueError("page must be positive")
        params: dict[str, str | int] = {"limit": limit, "page": page, "hasMarketData": "true"}
        if search and search.strip():
            params["search"] = search.strip()
        request = Request(
            f"{MESSARI_ASSETS_URL}?{urlencode(params)}",
            headers={"X-Messari-API-Key": self.api_key, "Accept": "application/json"},
        )
        with self.opener(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Messari response must be a JSON object")
        if payload.get("error"):
            raise ValueError(f"Messari API error: {payload['error']}")
        return parse_assets(payload)

    def market_coverage_record(self, symbol: str) -> NormalizedRecord:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")
        matches = self.list_assets(search=normalized, limit=10)
        exact = next((asset for asset in matches if asset.symbol == normalized), None)
        if exact is None:
            raise ValueError(f"Messari asset not found: {normalized}")
        return asset_to_record(exact)
