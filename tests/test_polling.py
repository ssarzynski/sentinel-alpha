from threading import Event

import pytest

from sentinel_alpha.polling import SecPollingService
from sentinel_alpha.sec_ingestion import SecFiling
from sentinel_alpha.watchlist import FilingDeduplicator, WatchAsset


class FakeSecClient:
    def recent_watched_filings(self, cik):
        return [
            SecFiling(
                cik="0001045810",
                accession_number="0001",
                form="8-K",
                filing_date="2026-09-17",
                primary_document="filing.htm",
                accepted_at="2026-09-17T12:00:00Z",
            )
        ]


def test_poll_once_emits_new_records_to_callback():
    batches = []
    service = SecPollingService(
        FakeSecClient(),
        [WatchAsset("NVDA", "1045810")],
        FilingDeduplicator(),
        on_records=batches.append,
    )
    result = service.poll_once()
    assert len(result.records) == 1
    assert result.records[0].observation.asset == "NVDA"
    assert len(batches) == 1


def test_second_poll_does_not_reemit_duplicate():
    batches = []
    service = SecPollingService(
        FakeSecClient(),
        [WatchAsset("NVDA", "1045810")],
        FilingDeduplicator(),
        on_records=batches.append,
    )
    assert len(service.poll_once().records) == 1
    assert service.poll_once().records == ()
    assert len(batches) == 1


def test_empty_watchlist_is_rejected():
    with pytest.raises(ValueError, match="at least one watchlist"):
        SecPollingService(FakeSecClient(), [], FilingDeduplicator())


def test_invalid_interval_is_rejected():
    service = SecPollingService(
        FakeSecClient(), [WatchAsset("NVDA", "1045810")], FilingDeduplicator()
    )
    with pytest.raises(ValueError, match="at least 1"):
        service.run(0, Event())


def test_pre_set_stop_event_performs_no_poll():
    batches = []
    service = SecPollingService(
        FakeSecClient(),
        [WatchAsset("NVDA", "1045810")],
        FilingDeduplicator(),
        on_records=batches.append,
    )
    stopped = Event()
    stopped.set()
    service.run(1, stopped)
    assert batches == []
