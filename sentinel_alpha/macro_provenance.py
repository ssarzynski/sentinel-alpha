"""Bridge macro observations into Sentinel Alpha canonical provenance records."""

from dataclasses import dataclass
from typing import Mapping

from .macro_regime import MacroInput
from .provenance import NormalizedRecord, SourceIdentity, normalize_record

MACRO_ASSET = "MACRO"


@dataclass(frozen=True)
class MacroSourcePolicy:
    provider: str
    channel: str
    independent_group: str


FRED_SERIES_POLICIES = {
    "DGS2": MacroSourcePolicy(
        "Federal Reserve Bank of St. Louis", "fred", "federal_reserve_board"
    ),
    "DGS10": MacroSourcePolicy(
        "Federal Reserve Bank of St. Louis", "fred", "federal_reserve_board"
    ),
    "FEDFUNDS": MacroSourcePolicy(
        "Federal Reserve Bank of St. Louis", "fred", "federal_reserve_board"
    ),
    "CPIAUCSL": MacroSourcePolicy("Federal Reserve Bank of St. Louis", "fred", "bls"),
    "UNRATE": MacroSourcePolicy("Federal Reserve Bank of St. Louis", "fred", "bls"),
    "VIXCLS": MacroSourcePolicy("Federal Reserve Bank of St. Louis", "fred", "cboe"),
}
TREASURY_POLICY = MacroSourcePolicy(
    "U.S. Department of the Treasury",
    "daily_treasury_yield_curve",
    "us_treasury",
)


def source_identity_for_macro_input(item: MacroInput) -> SourceIdentity:
    source = item.source.strip()
    if source.startswith("fred:"):
        series = source.removeprefix("fred:")
        try:
            policy = FRED_SERIES_POLICIES[series]
        except KeyError as exc:
            raise ValueError(f"unsupported FRED macro series: {series}") from exc
    elif source == "treasury:daily_treasury_yield_curve":
        policy = TREASURY_POLICY
    else:
        raise ValueError(f"unsupported macro source: {item.source}")
    return SourceIdentity(
        source_id=source,
        provider=policy.provider,
        channel=policy.channel,
        independent_group=policy.independent_group,
    )


def normalize_macro_input(item: MacroInput) -> NormalizedRecord:
    source = source_identity_for_macro_input(item)
    return normalize_record(
        asset=MACRO_ASSET,
        metric=item.metric,
        value=item.value,
        source=source,
        observed_at=item.observed_at,
        statement=f"{item.metric}={item.value}",
        reference=item.source,
        quality="authoritative",
    )


def normalize_macro_inputs(inputs: Mapping[str, MacroInput]) -> list[NormalizedRecord]:
    records: list[NormalizedRecord] = []
    for metric, item in inputs.items():
        if metric != item.metric:
            raise ValueError(
                f"macro metric key {metric!r} does not match input metric "
                f"{item.metric!r}"
            )
        records.append(normalize_macro_input(item))
    return records
