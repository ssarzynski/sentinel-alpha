"""Watchlist-driven SEC ingestion and filing deduplication."""

from dataclasses import dataclass

from .provenance import NormalizedRecord
from .sec_ingestion import SecEdgarClient, filing_to_record


@dataclass(frozen=True)
class WatchAsset:
    symbol: str
    cik: str


class FilingDeduplicator:
    """In-memory accession-number deduplicator for one ingestion process."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def accept(self, accession_number: str) -> bool:
        if accession_number in self._seen:
            return False
        self._seen.add(accession_number)
        return True


def ingest_sec_watchlist(
    client: SecEdgarClient,
    assets: list[WatchAsset],
    deduplicator: FilingDeduplicator | None = None,
) -> list[NormalizedRecord]:
    """Fetch watched filings for configured assets and normalize unseen filings."""
    deduplicator = deduplicator or FilingDeduplicator()
    records: list[NormalizedRecord] = []
    for asset in assets:
        symbol = asset.symbol.strip().upper()
        if not symbol:
            raise ValueError("watchlist symbol is required")
        for filing in client.recent_watched_filings(asset.cik):
            if deduplicator.accept(filing.accession_number):
                records.append(filing_to_record(filing, symbol))
    return records
