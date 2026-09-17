from sentinel_alpha.polling import SecPollingService
from sentinel_alpha.sec_ingestion import SecFiling
from sentinel_alpha.watchlist import FilingDeduplicator, WatchAsset
from sentinel_alpha.watchlist_store import WatchlistStore


class FakeSecClient:
    def recent_watched_filings(self, cik):
        return [
            SecFiling(
                cik=str(cik).zfill(10),
                accession_number=f"filing-{cik}",
                form="8-K",
                filing_date="2026-09-17",
                primary_document="filing.htm",
            )
        ]


def test_polling_reads_current_active_assets_each_cycle(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    store.upsert(WatchAsset("NVDA", "1045810"))
    service = SecPollingService(
        FakeSecClient(), None, FilingDeduplicator(), watchlist_provider=store
    )
    first = service.poll_once()
    assert [record.observation.asset for record in first.records] == ["NVDA"]

    store.set_active("NVDA", False)
    store.upsert(WatchAsset("AAPL", "320193"))
    second = service.poll_once()
    assert [record.observation.asset for record in second.records] == ["AAPL"]


def test_empty_dynamic_watchlist_is_safe(tmp_path):
    store = WatchlistStore(tmp_path / "sentinel.db")
    service = SecPollingService(
        FakeSecClient(), None, FilingDeduplicator(), watchlist_provider=store
    )
    assert service.poll_once().records == ()
