"""Bridge macro observations into Sentinel Alpha canonical provenance records."""

from dataclasses import dataclass
from typing import Mapping

from .macro_regime import MacroInput
from .provenance import NormalizedRecord, SourceIdentity, normalize_record

MACRO_ASSET = "MACRO"


@dataclass(frozen=True)
class MacroSourcePolicy:
    """Describe an upstream macro source without overstating independence."""

    provider: str
    channel: str
    independent_group: str


FRED_POLICY = MacroSourcePolicy(
    provider="Federal Reserve Bank of St. Louis",
    channel="fred",
    independent_group="fred",
)
TREASURY_POLICY = MacroSourcePolicy(
    provider="U.S. Department of the Treasury",
    channel="daily_treasury_yield_curve",
    independent_group="us_treasury",
)


def source_identity_for_macro_input(item: MacroInput) -> SourceIdentity:
    """Create a stable source identity from a macro input's provider reference."""
    source = item.source.strip()
    if source.startswith("fred:"):
        policy = FRED_POLICY
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
    """Normalize macro inputs and reject mismatched mapping labels."""
    records: list[NormalizedRecord] = []
    for metric, item in inputs.items():
        if metric != item.metric:
            raise ValueError(
                f"macro metric key {metric!r} does not match input metric "
                f"{item.metric!r}"
            )
        records.append(normalize_macro_input(item))
    return records
