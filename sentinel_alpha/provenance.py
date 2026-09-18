"""Source normalization and independent-confirmation provenance."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .models import Evidence, Observation


@dataclass(frozen=True)
class SourceIdentity:
    """Stable identity used to prevent duplicate/upstream-source confirmations."""

    source_id: str
    provider: str
    channel: str
    independent_group: str | None = None

    @property
    def independence_key(self) -> str:
        group = self.independent_group or self.provider
        return group.strip().lower()

    @property
    def uses_explicit_independence(self) -> bool:
        return self.independent_group is not None


@dataclass(frozen=True)
class NormalizedRecord:
    observation: Observation
    evidence: Evidence
    source: SourceIdentity


def normalize_record(
    *,
    asset: str,
    metric: str,
    value: Any,
    source: SourceIdentity,
    observed_at: datetime,
    statement: str,
    reference: str | None = None,
    quality: str = "unknown",
) -> NormalizedRecord:
    """Convert provider-specific input into Sentinel Alpha canonical models."""
    asset = asset.strip().upper()
    metric = metric.strip().lower()
    if not asset:
        raise ValueError("asset is required")
    if not metric:
        raise ValueError("metric is required")
    if (
        not source.source_id.strip()
        or not source.provider.strip()
        or not source.channel.strip()
    ):
        raise ValueError("complete source identity is required")
    if source.independent_group is not None and not source.independent_group.strip():
        raise ValueError("independent_group cannot be blank")

    observation = Observation(
        asset=asset,
        metric=metric,
        value=value,
        source=source.source_id,
        observed_at=observed_at,
        quality=quality.strip().lower(),
    )
    evidence = Evidence(
        source=source.source_id,
        statement=statement.strip(),
        observed_at=observed_at,
        reference=reference,
    )
    return NormalizedRecord(observation=observation, evidence=evidence, source=source)


def independent_confirmation_keys(records: list[NormalizedRecord]) -> set[str]:
    """Return unique upstream groups, failing closed for ambiguous provider aliases.

    Distinct provider labels are independent only when no provider is represented
    through an explicit upstream group. Once explicit lineage is present, every
    record in that confirmation set must declare its upstream group so aliases
    cannot manufacture a second confirmation.
    """
    if any(record.source.uses_explicit_independence for record in records):
        return {
            record.source.independence_key
            for record in records
            if record.source.uses_explicit_independence
        }
    return {record.source.independence_key for record in records}


def normalize_mapping(
    payload: Mapping[str, Any], *, source: SourceIdentity, observed_at: datetime
) -> NormalizedRecord:
    """Small adapter boundary for future SEC, Finviz, Messari, and other providers."""
    return normalize_record(
        asset=str(payload["asset"]),
        metric=str(payload["metric"]),
        value=payload.get("value"),
        source=source,
        observed_at=observed_at,
        statement=str(payload.get("statement", "")),
        reference=payload.get("reference"),
        quality=str(payload.get("quality", "unknown")),
    )
