"""Controlled polling loop for watchlist SEC ingestion."""

from dataclasses import dataclass
from threading import Event
from time import monotonic
from typing import Callable

from .provenance import NormalizedRecord
from .sec_ingestion import SecEdgarClient
from .watchlist import Deduplicator, WatchAsset, ingest_sec_watchlist


@dataclass(frozen=True)
class PollResult:
    records: tuple[NormalizedRecord, ...]
    duration_seconds: float


class SecPollingService:
    """Runs one or repeated SEC ingestion cycles; scheduling remains caller-controlled."""

    def __init__(
        self,
        client: SecEdgarClient,
        assets: list[WatchAsset],
        deduplicator: Deduplicator,
        on_records: Callable[[list[NormalizedRecord]], None] | None = None,
    ) -> None:
        if not assets:
            raise ValueError("at least one watchlist asset is required")
        self.client = client
        self.assets = list(assets)
        self.deduplicator = deduplicator
        self.on_records = on_records

    def poll_once(self) -> PollResult:
        started = monotonic()
        records = ingest_sec_watchlist(self.client, self.assets, self.deduplicator)
        if records and self.on_records is not None:
            self.on_records(records)
        return PollResult(tuple(records), monotonic() - started)

    def run(self, interval_seconds: float, stop_event: Event) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be at least 1")
        while not stop_event.is_set():
            self.poll_once()
            stop_event.wait(interval_seconds)
