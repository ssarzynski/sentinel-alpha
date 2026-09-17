import sqlite3
from datetime import datetime, timezone

from sentinel_alpha.journal import GENESIS_HASH, EvaluationJournal
from sentinel_alpha.pipeline import evaluate_records
from sentinel_alpha.provenance import SourceIdentity, normalize_record
from sentinel_alpha.risk_gate import TradeProposal


def evaluation():
    now = datetime.now(timezone.utc)
    records = [
        normalize_record(
            asset="NVDA",
            metric="signal",
            value=True,
            source=SourceIdentity("sec", "SEC", "filings"),
            observed_at=now,
            statement="SEC confirmation",
        ),
        normalize_record(
            asset="NVDA",
            metric="signal",
            value=True,
            source=SourceIdentity("finviz", "Finviz", "screening"),
            observed_at=now,
            statement="Finviz confirmation",
        ),
    ]
    return evaluate_records(
        asset="NVDA",
        status="confirmed",
        records=records,
        proposal=TradeProposal(asset="NVDA", stop_loss_defined=True),
        new_entries_this_week=0,
    )


def test_first_entry_links_to_genesis_hash(tmp_path):
    journal = EvaluationJournal(tmp_path / "journal.db")
    evaluation_id = journal.append(evaluation())
    assert journal.get(evaluation_id)["previous_hash"] == GENESIS_HASH
    assert journal.verify_integrity() is True


def test_second_entry_links_to_first(tmp_path):
    journal = EvaluationJournal(tmp_path / "journal.db")
    first = journal.append(evaluation())
    second = journal.append(evaluation())
    assert journal.get(second)["previous_hash"] == journal.get(first)["entry_hash"]
    assert journal.verify_integrity() is True


def test_payload_tampering_is_detected(tmp_path):
    database = tmp_path / "journal.db"
    journal = EvaluationJournal(database)
    evaluation_id = journal.append(evaluation())
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE evaluations SET asset = ? WHERE evaluation_id = ?", ("TAMPERED", evaluation_id)
        )
    assert journal.verify_integrity() is False


def test_hash_tampering_is_detected(tmp_path):
    database = tmp_path / "journal.db"
    journal = EvaluationJournal(database)
    evaluation_id = journal.append(evaluation())
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE evaluations SET entry_hash = ? WHERE evaluation_id = ?", ("bad-hash", evaluation_id)
        )
    assert journal.verify_integrity() is False
