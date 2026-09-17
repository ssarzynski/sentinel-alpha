"""SQLite-backed tamper-evident evaluation audit journal."""

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .pipeline import EvaluationResult

GENESIS_HASH = "0" * 64


def _entry_hash(previous_hash: str, evaluation_id: str, created_at: str, asset: str, payload: str) -> str:
    material = "|".join((previous_hash, evaluation_id, created_at, asset, payload)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class EvaluationJournal:
    def __init__(self, database: str | Path = "sentinel_alpha.db") -> None:
        self.database = str(database)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluation_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL UNIQUE
                )
                """
            )

    def append(self, result: EvaluationResult) -> str:
        evaluation_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(result), default=str, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            previous = connection.execute(
                "SELECT entry_hash FROM evaluations ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous["entry_hash"] if previous else GENESIS_HASH
            entry_hash = _entry_hash(
                previous_hash, evaluation_id, created_at, result.signal.asset, payload
            )
            connection.execute(
                """INSERT INTO evaluations
                (evaluation_id, created_at, asset, payload, previous_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (evaluation_id, created_at, result.signal.asset, payload, previous_hash, entry_hash),
            )
        return evaluation_id

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        return {
            "evaluation_id": row["evaluation_id"],
            "created_at": row["created_at"],
            "asset": row["asset"],
            "result": json.loads(row["payload"]),
            "previous_hash": row["previous_hash"],
            "entry_hash": row["entry_hash"],
        }

    def get(self, evaluation_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM evaluations WHERE evaluation_id = ?", (evaluation_id,)
            ).fetchone()
        return None if row is None else self._row(row)

    def recent(self, limit: int = 50) -> list[dict]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM evaluations ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row(row) for row in rows]

    def verify_integrity(self) -> bool:
        """Verify every link and content hash in the journal chain."""
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM evaluations ORDER BY sequence ASC").fetchall()
        expected_previous = GENESIS_HASH
        for row in rows:
            if row["previous_hash"] != expected_previous:
                return False
            expected_hash = _entry_hash(
                expected_previous,
                row["evaluation_id"],
                row["created_at"],
                row["asset"],
                row["payload"],
            )
            if row["entry_hash"] != expected_hash:
                return False
            expected_previous = row["entry_hash"]
        return True
