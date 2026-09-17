import pytest

from sentinel_alpha.watchlist import SqliteFilingDeduplicator


def test_accession_is_accepted_only_once(tmp_path):
    dedupe = SqliteFilingDeduplicator(tmp_path / "sentinel.db")
    assert dedupe.accept("0001045810-26-000001") is True
    assert dedupe.accept("0001045810-26-000001") is False


def test_deduplication_survives_new_instance(tmp_path):
    database = tmp_path / "sentinel.db"
    first_process = SqliteFilingDeduplicator(database)
    assert first_process.accept("0001045810-26-000002") is True
    restarted_process = SqliteFilingDeduplicator(database)
    assert restarted_process.accept("0001045810-26-000002") is False


def test_distinct_accessions_are_independent(tmp_path):
    dedupe = SqliteFilingDeduplicator(tmp_path / "sentinel.db")
    assert dedupe.accept("filing-a") is True
    assert dedupe.accept("filing-b") is True


def test_blank_accession_is_rejected(tmp_path):
    dedupe = SqliteFilingDeduplicator(tmp_path / "sentinel.db")
    with pytest.raises(ValueError, match="accession_number is required"):
        dedupe.accept("   ")
