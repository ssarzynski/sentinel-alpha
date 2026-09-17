"""Credential-gated Alpha Vantage daily equity market ingestion."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .provenance import NormalizedRecord, SourceIdentity, normalize_record

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
ALPHA_VANTAGE_MARKET = SourceIdentity(
    "alpha-vantage-daily", "Alpha Vantage", "equity-market", independent_group="alpha_vantage"
)


@dataclass(frozen=True)
class DailyEquityBar:
    symbol: str
    observed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class AlphaVantageClient:
    """Minimal TIME_SERIES_DAILY client. No key means no network request."""

    def __init__(
        self,
        api_key: str,
        *,
        opener: Callable = urlopen,
        timeout: float = 10.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("ALPHA_VANTAGE_API_KEY is required")
        self.api_key = api_key.strip()
        self.opener = opener
        self.timeout = timeout

    def latest_daily(self, symbol: str) -> DailyEquityBar:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        query = urlencode(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "datatype": "json",
                "apikey": self.api_key,
            }
        )
        request = Request(
            f"{ALPHA_VANTAGE_URL}?{query}",
            headers={"User-Agent": "sentinel-alpha/0.1"},
        )
        with self.opener(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if "Error Message" in payload:
            raise ValueError("Alpha Vantage rejected the symbol or request")
        if "Note" in payload or "Information" in payload:
            raise RuntimeError("Alpha Vantage request unavailable or rate limited")
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            raise ValueError("Alpha Vantage response contains no daily time series")

        date_text = max(series)
        row = series[date_text]
        try:
            observed_at = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)
            return DailyEquityBar(
                symbol=symbol,
                observed_at=observed_at,
                open=float(row["1. open"]),
                high=float(row["2. high"]),
                low=float(row["3. low"]),
                close=float(row["4. close"]),
                volume=int(row["5. volume"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid Alpha Vantage daily bar") from exc


def daily_bar_to_records(bar: DailyEquityBar) -> tuple[NormalizedRecord, NormalizedRecord]:
    """Normalize independent market price and volume observations."""
    price = normalize_record(
        asset=bar.symbol,
        metric="daily_close",
        value=bar.close,
        source=ALPHA_VANTAGE_MARKET,
        observed_at=bar.observed_at,
        statement=f"{bar.symbol} daily close {bar.close}",
    )
    volume = normalize_record(
        asset=bar.symbol,
        metric="daily_volume",
        value=bar.volume,
        source=ALPHA_VANTAGE_MARKET,
        observed_at=bar.observed_at,
        statement=f"{bar.symbol} daily volume {bar.volume}",
    )
    return price, volume
