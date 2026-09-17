"""SQLite-backed append-only evaluation audit journal."""

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .pipeline import EvaluationResult


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
                    evaluation_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def append(self, result: EvaluationResult) -> str:
        evaluation_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(result), default=str, sort_keys=True)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO evaluations (evaluation_id, created_at, asset, payload) VALUES (?, ?, ?, ?)",
                (evaluation_id, created_at, result.signal.asset, payload),
            )
        return evaluation_id

    def get(self, evaluation_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT evaluation_id, created_at, asset, payload FROM evaluations WHERE evaluation_id = ?",
                (evaluation_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "evaluation_id": row["evaluation_id"],
            "created_at": row["created_at"],
            "asset": row["asset"],
            "result": json.loads(row["payload"]),
        }

    def recent(self, limit: int = 50) -> list[dict]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT evaluation_id, created_at, asset, payload "
                "FROM evaluations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "evaluation_id": row["evaluation_id"],
                "created_at": row["created_at"],
                "asset": row["asset"],
                "result": json.loads(row["payload"]),
            }
            for row in rows
        ]
