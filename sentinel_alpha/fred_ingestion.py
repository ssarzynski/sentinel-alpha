"""FRED macro-series ingestion with explicit provenance and no embedded secrets."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .macro_regime import MacroInput

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Series choices are explicit so changing macro semantics requires code review.
FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "treasury_2y": "DGS2",
    "treasury_10y": "DGS10",
    "inflation_yoy": "CPIAUCSL",
    "unemployment_rate": "UNRATE",
    "volatility_index": "VIXCLS",
}

DEFAULT_MAX_AGES = {
    "fed_funds_rate": timedelta(days=45),
    "treasury_2y": timedelta(days=5),
    "treasury_10y": timedelta(days=5),
    "inflation_yoy": timedelta(days=45),
    "unemployment_rate": timedelta(days=45),
    "volatility_index": timedelta(days=5),
}


@dataclass(frozen=True)
class FredObservation:
    series_id: str
    date: datetime
    value: float


class FredClient:
    """Small FRED v1 client; callers supply the registered API key at runtime."""

    def __init__(self, api_key: str, *, opener: Callable = urlopen, timeout: float = 10.0):
        if not api_key.strip():
            raise ValueError("FRED API key is required")
        self.api_key = api_key.strip()
        self.opener = opener
        self.timeout = timeout

    def latest(self, series_id: str, *, units: str = "lin") -> FredObservation:
        params = urlencode({
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 24,
            "units": units,
        })
        request = Request(f"{FRED_BASE_URL}?{params}", headers={"User-Agent": "sentinel-alpha/0.1"})
        with self.opener(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for row in payload.get("observations", []):
            value = row.get("value")
            if value not in (None, "."):
                observed = datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc)
                return FredObservation(series_id, observed, float(value))
        raise ValueError(f"FRED returned no numeric observations for {series_id}")


def load_macro_inputs(client: FredClient) -> dict[str, MacroInput]:
    """Load the regime's six required inputs from FRED.

    CPI uses FRED's percent-change-from-year-ago transformation so the regime
    consumes an inflation rate rather than the CPI index level.
    """
    result: dict[str, MacroInput] = {}
    for metric, series_id in FRED_SERIES.items():
        units = "pc1" if metric == "inflation_yoy" else "lin"
        observation = client.latest(series_id, units=units)
        result[metric] = MacroInput(
            metric=metric,
            value=observation.value,
            observed_at=observation.date,
            source=f"fred:{series_id}",
            max_age=DEFAULT_MAX_AGES[metric],
        )
    return result
