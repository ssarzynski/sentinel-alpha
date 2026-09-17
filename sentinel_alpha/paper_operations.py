"""Read-only paper-operation ledger for Sentinel Alpha.

Paper decisions are observations of what a human-approved hypothetical action
would have been. This module has no broker, exchange, order, or execution path.
"""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .pipeline import EvaluationResult


@dataclass(frozen=True)
class PaperDecision:
    paper_id: str
    evaluation_id: str
    asset: str
    created_at: str
    approved_by_human: bool
    hypothetical_action: str
    notes: str


class PaperOperationLedger:
    def __init__(self, database: str | Path = "sentinel_alpha.db") -> None:
        self.database = str(database)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_decisions (
                    paper_id TEXT PRIMARY KEY,
                    evaluation_id TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    approved_by_human INTEGER NOT NULL,
                    hypothetical_action TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    snapshot TEXT NOT NULL
                )
                """
            )

    def record(
        self,
        *,
        evaluation_id: str,
        result: EvaluationResult,
        approved_by_human: bool,
        hypothetical_action: str,
        notes: str = "",
    ) -> str:
        action = hypothetical_action.strip().lower()
        if action not in {"observe", "paper_entry", "paper_skip"}:
            raise ValueError("unsupported hypothetical paper action")
        if action == "paper_entry" and not approved_by_human:
            raise ValueError("paper entry requires explicit human approval")
        if action == "paper_entry" and (result.decision.blocked or result.risk.blocked):
            raise ValueError("blocked evaluation cannot become a paper entry")

        paper_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        snapshot = json.dumps(asdict(result), default=str, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO paper_decisions
                (paper_id, evaluation_id, asset, created_at, approved_by_human,
                 hypothetical_action, notes, snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper_id,
                    evaluation_id,
                    result.signal.asset,
                    created_at,
                    int(approved_by_human),
                    action,
                    notes.strip(),
                    snapshot,
                ),
            )
        return paper_id

    def recent(self, limit: int = 50) -> list[PaperDecision]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM paper_decisions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            PaperDecision(
                paper_id=row["paper_id"],
                evaluation_id=row["evaluation_id"],
                asset=row["asset"],
                created_at=row["created_at"],
                approved_by_human=bool(row["approved_by_human"]),
                hypothetical_action=row["hypothetical_action"],
                notes=row["notes"],
            )
            for row in rows
        ]
