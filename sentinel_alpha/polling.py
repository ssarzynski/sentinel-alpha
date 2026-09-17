"""Controlled polling loop for watchlist SEC ingestion."""

from dataclasses import dataclass
from threading import Event
from time import monotonic
from typing import Callable, Protocol

from .provenance import NormalizedRecord
from .sec_ingestion import SecEdgarClient
from .watchlist import Deduplicator, WatchAsset, ingest_sec_watchlist


class WatchlistProvider(Protocol):
    def active_assets(self) -> list[WatchAsset]:
        ...


@dataclass(frozen=True)
class PollResult:
    records: tuple[NormalizedRecord, ...]
    duration_seconds: float


class SecPollingService:
    """Runs SEC ingestion cycles using the current active watchlist."""

    def __init__(
        self,
        client: SecEdgarClient,
        assets: list[WatchAsset] | None,
        deduplicator: Deduplicator,
        on_records: Callable[[list[NormalizedRecord]], None] | None = None,
        watchlist_provider: WatchlistProvider | None = None,
    ) -> None:
        if not assets and watchlist_provider is None:
            raise ValueError("at least one watchlist asset or provider is required")
        self.client = client
        self.assets = list(assets or [])
        self.deduplicator = deduplicator
        self.on_records = on_records
        self.watchlist_provider = watchlist_provider

    def _current_assets(self) -> list[WatchAsset]:
        if self.watchlist_provider is not None:
            return self.watchlist_provider.active_assets()
        return list(self.assets)

    def poll_once(self) -> PollResult:
        started = monotonic()
        assets = self._current_assets()
        records = (
            ingest_sec_watchlist(self.client, assets, self.deduplicator) if assets else []
        )
        if records and self.on_records is not None:
            self.on_records(records)
        return PollResult(tuple(records), monotonic() - started)

    def run(self, interval_seconds: float, stop_event: Event) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be at least 1")
        while not stop_event.is_set():
            self.poll_once()
            stop_event.wait(interval_seconds)
