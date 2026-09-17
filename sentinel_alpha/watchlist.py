"""Watchlist-driven SEC ingestion and persistent filing deduplication."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .provenance import NormalizedRecord
from .sec_ingestion import SecEdgarClient, filing_to_record


@dataclass(frozen=True)
class WatchAsset:
    symbol: str
    cik: str


class Deduplicator(Protocol):
    def accept(self, accession_number: str) -> bool:
        ...


class FilingDeduplicator:
    """In-memory accession-number deduplicator for tests or ephemeral runs."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def accept(self, accession_number: str) -> bool:
        if accession_number in self._seen:
            return False
        self._seen.add(accession_number)
        return True


class SqliteFilingDeduplicator:
    """Persistent accession-number deduplicator that survives process restarts."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_sec_filings (
                    accession_number TEXT PRIMARY KEY,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def accept(self, accession_number: str) -> bool:
        accession = accession_number.strip()
        if not accession:
            raise ValueError("accession_number is required")
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO processed_sec_filings (accession_number) VALUES (?)",
                (accession,),
            )
            return cursor.rowcount == 1


def ingest_sec_watchlist(
    client: SecEdgarClient,
    assets: list[WatchAsset],
    deduplicator: Deduplicator | None = None,
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
