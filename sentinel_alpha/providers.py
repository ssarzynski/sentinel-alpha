"""Provider adapter contracts and registry for Sentinel Alpha."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol

from .provenance import NormalizedRecord, SourceIdentity, normalize_mapping


class ProviderAdapter(Protocol):
    """Contract implemented by external data-source adapters."""

    source: SourceIdentity

    def normalize(self, payload: Mapping[str, Any], observed_at: datetime) -> NormalizedRecord:
        ...


@dataclass(frozen=True)
class MappingProviderAdapter:
    """Safe normalization-only adapter; network retrieval is intentionally separate."""

    source: SourceIdentity

    def normalize(self, payload: Mapping[str, Any], observed_at: datetime) -> NormalizedRecord:
        return normalize_mapping(payload, source=self.source, observed_at=observed_at)


SEC_FILINGS = MappingProviderAdapter(SourceIdentity("sec-filings", "SEC", "filings"))
FINVIZ_SCREENING = MappingProviderAdapter(SourceIdentity("finviz-screening", "Finviz", "screening"))
MESSARI_RESEARCH = MappingProviderAdapter(SourceIdentity("messari-research", "Messari", "research"))
MESSARI_MARKET = MappingProviderAdapter(SourceIdentity("messari-market", "Messari", "market"))
INVO_MARKET = MappingProviderAdapter(SourceIdentity("invo-market", "Invo", "market"))


PROVIDERS: dict[str, MappingProviderAdapter] = {
    "sec": SEC_FILINGS,
    "finviz": FINVIZ_SCREENING,
    "messari": MESSARI_RESEARCH,
    "messari_market": MESSARI_MARKET,
    "invo": INVO_MARKET,
}


def get_provider(name: str) -> MappingProviderAdapter:
    """Return a registered adapter using a stable lower-case provider key."""
    key = name.strip().lower()
    try:
        return PROVIDERS[key]
    except KeyError as exc:
        raise ValueError(f"unknown provider: {name}") from exc
