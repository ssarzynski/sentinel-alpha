import json
import sqlite3

from sentinel_alpha.journal import EvaluationJournal, GENESIS_HASH


def test_legacy_evaluations_table_is_migrated_and_backfilled(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE evaluations (
                evaluation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                asset TEXT NOT NULL,
                payload TEXT NOT NULL
            )"""
        )
        connection.execute(
            "INSERT INTO evaluations VALUES (?, ?, ?, ?)",
            ("old-1", "2026-01-01T00:00:00+00:00", "NVDA", json.dumps({"old": 1})),
        )
        connection.execute(
            "INSERT INTO evaluations VALUES (?, ?, ?, ?)",
            ("old-2", "2026-01-02T00:00:00+00:00", "AAPL", json.dumps({"old": 2})),
        )

    journal = EvaluationJournal(database)
    assert journal.verify_integrity() is True
    rows = journal.recent(10)
    assert len(rows) == 2
    oldest = journal.get("old-1")
    newest = journal.get("old-2")
    assert oldest["previous_hash"] == GENESIS_HASH
    assert newest["previous_hash"] == oldest["entry_hash"]


def test_existing_current_schema_is_left_intact(tmp_path):
    database = tmp_path / "current.db"
    journal = EvaluationJournal(database)
    assert journal.verify_integrity() is True
    restarted = EvaluationJournal(database)
    assert restarted.verify_integrity() is True


def test_unknown_legacy_schema_fails_closed(tmp_path):
    database = tmp_path / "unknown.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE evaluations (mystery TEXT)")

    try:
        EvaluationJournal(database)
    except RuntimeError as exc:
        assert "manual migration required" in str(exc)
    else:
        raise AssertionError("unsupported schema must not be silently replaced")
