from sentinel_alpha.nvda_slice import NVDA, NVDA_CIK, load_nvda_sec_evidence
from sentinel_alpha.sec_ingestion import SecFiling


class FixtureSecClient:
    def __init__(self, filings):
        self.filings = filings
        self.requested_cik = None

    def recent_watched_filings(self, cik):
        self.requested_cik = cik
        return self.filings


def filing(accession: str, form: str) -> SecFiling:
    return SecFiling(
        cik=NVDA_CIK,
        accession_number=accession,
        form=form,
        filing_date="2026-09-17",
        primary_document="fixture.htm",
        accepted_at="2026-09-17T12:00:00Z",
    )


def test_nvda_sec_loader_requests_nvidia_cik_and_normalizes_records():
    client = FixtureSecClient([filing("0001045810-26-000001", "8-K")])
    records = load_nvda_sec_evidence(client)
    assert client.requested_cik == NVDA_CIK
    assert len(records) == 1
    assert records[0].observation.asset == NVDA
    assert records[0].observation.metric == "material_filing"
    assert records[0].source.provider == "SEC"


def test_multiple_sec_filings_remain_one_independent_source_group():
    client = FixtureSecClient(
        [
            filing("0001045810-26-000001", "8-K"),
            filing("0001045810-26-000002", "4"),
        ]
    )
    records = load_nvda_sec_evidence(client)
    assert len(records) == 2
    assert {record.source.independence_key for record in records} == {"sec"}
    assert {record.observation.metric for record in records} == {
        "material_filing",
        "insider_filing",
    }


def test_empty_sec_result_returns_no_evidence_instead_of_synthetic_confirmation():
    client = FixtureSecClient([])
    assert load_nvda_sec_evidence(client) == ()
