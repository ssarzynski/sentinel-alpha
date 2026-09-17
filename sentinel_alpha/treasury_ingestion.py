"""Direct U.S. Treasury par-yield ingestion and FRED cross-validation."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .macro_regime import MacroInput

TREASURY_XML_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
TREASURY_SOURCE = "treasury:daily_treasury_yield_curve"


@dataclass(frozen=True)
class TreasuryYieldObservation:
    observed_at: datetime
    treasury_2y: float
    treasury_10y: float


@dataclass(frozen=True)
class YieldCrossCheck:
    metric: str
    primary_value: float
    comparison_value: float
    absolute_difference: float
    within_tolerance: bool


class TreasuryClient:
    """Read Treasury's documented daily par-yield XML feed."""

    def __init__(self, *, opener: Callable = urlopen, timeout: float = 10.0):
        self.opener = opener
        self.timeout = timeout

    def latest(self, *, year: int | None = None) -> TreasuryYieldObservation:
        year = year or datetime.now(timezone.utc).year
        params = urlencode({
            "data": "daily_treasury_yield_curve",
            "field_tdr_date_value": str(year),
        })
        request = Request(
            f"{TREASURY_XML_URL}?{params}",
            headers={"User-Agent": "sentinel-alpha/0.1"},
        )
        with self.opener(request, timeout=self.timeout) as response:
            root = ET.fromstring(response.read())

        observations: list[TreasuryYieldObservation] = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            props = entry.find(".//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties")
            if props is None:
                continue
            values = {node.tag.rsplit("}", 1)[-1]: node.text for node in props}
            date_text = values.get("NEW_DATE")
            y2 = values.get("BC_2YEAR")
            y10 = values.get("BC_10YEAR")
            if not date_text or not y2 or not y10:
                continue
            observed = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            observations.append(TreasuryYieldObservation(observed, float(y2), float(y10)))
        if not observations:
            raise ValueError("Treasury returned no complete 2Y/10Y yield observations")
        return max(observations, key=lambda item: item.observed_at)


def treasury_macro_inputs(observation: TreasuryYieldObservation, *, max_age) -> dict[str, MacroInput]:
    return {
        "treasury_2y": MacroInput(
            metric="treasury_2y", value=observation.treasury_2y,
            observed_at=observation.observed_at, source=TREASURY_SOURCE, max_age=max_age,
        ),
        "treasury_10y": MacroInput(
            metric="treasury_10y", value=observation.treasury_10y,
            observed_at=observation.observed_at, source=TREASURY_SOURCE, max_age=max_age,
        ),
    }


def cross_validate_yields(
    primary: Mapping[str, MacroInput], comparison: Mapping[str, MacroInput], *, tolerance: float = 0.05
) -> list[YieldCrossCheck]:
    """Compare 2Y/10Y values without silently replacing the primary source."""
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    checks: list[YieldCrossCheck] = []
    for metric in ("treasury_2y", "treasury_10y"):
        if metric not in primary or metric not in comparison:
            raise ValueError(f"missing {metric} for yield cross-validation")
        difference = abs(float(primary[metric].value) - float(comparison[metric].value))
        checks.append(YieldCrossCheck(
            metric=metric,
            primary_value=float(primary[metric].value),
            comparison_value=float(comparison[metric].value),
            absolute_difference=difference,
            within_tolerance=difference <= tolerance,
        ))
    return checks
