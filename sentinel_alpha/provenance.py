"""Source normalization and independent-confirmation provenance."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .models import Evidence, Observation


@dataclass(frozen=True)
class SourceIdentity:
    """Stable identity used to prevent duplicate-source confirmations."""

    source_id: str
    provider: str
    channel: str

    @property
    def independence_key(self) -> str:
        return f"{self.provider.strip().lower()}:{self.channel.strip().lower()}"


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
    if not source.source_id.strip() or not source.provider.strip() or not source.channel.strip():
        raise ValueError("complete source identity is required")

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
    """Return unique provider/channel identities represented by records."""
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
