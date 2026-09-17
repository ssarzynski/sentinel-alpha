from sentinel_alpha.sec_ingestion import SecFiling
from sentinel_alpha.watchlist import FilingDeduplicator, WatchAsset, ingest_sec_watchlist


class FakeSecClient:
    def __init__(self, filings_by_cik):
        self.filings_by_cik = filings_by_cik

    def recent_watched_filings(self, cik):
        return self.filings_by_cik.get(cik, [])


def filing(cik, accession, form="8-K"):
    return SecFiling(
        cik=cik,
        accession_number=accession,
        form=form,
        filing_date="2026-09-17",
        primary_document="filing.htm",
        accepted_at="2026-09-17T12:00:00Z",
    )


def test_watchlist_maps_cik_filings_to_symbol():
    client = FakeSecClient({"1045810": [filing("0001045810", "0001")]})
    records = ingest_sec_watchlist(client, [WatchAsset("nvda", "1045810")])
    assert len(records) == 1
    assert records[0].observation.asset == "NVDA"
    assert records[0].observation.metric == "material_filing"


def test_duplicate_accession_is_emitted_once_across_poll_cycles():
    client = FakeSecClient({"1045810": [filing("0001045810", "0001")]})
    dedupe = FilingDeduplicator()
    assets = [WatchAsset("NVDA", "1045810")]
    first = ingest_sec_watchlist(client, assets, dedupe)
    second = ingest_sec_watchlist(client, assets, dedupe)
    assert len(first) == 1
    assert second == []


def test_multiple_watchlist_assets_keep_correct_symbols():
    client = FakeSecClient(
        {
            "1045810": [filing("0001045810", "nvda-1")],
            "320193": [filing("0000320193", "aapl-1", "4")],
        }
    )
    records = ingest_sec_watchlist(
        client,
        [WatchAsset("NVDA", "1045810"), WatchAsset("AAPL", "320193")],
    )
    assert [record.observation.asset for record in records] == ["NVDA", "AAPL"]
    assert records[1].observation.metric == "insider_filing"


def test_blank_watchlist_symbol_is_rejected():
    client = FakeSecClient({"1045810": []})
    try:
        ingest_sec_watchlist(client, [WatchAsset(" ", "1045810")])
    except ValueError as exc:
        assert "symbol" in str(exc)
    else:
        raise AssertionError("expected blank symbol to be rejected")
