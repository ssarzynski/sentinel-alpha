"""Human-approved, tamper-evident paper-operation boundary for Sentinel Alpha.

Paper decisions are hypothetical observations only. This module has no broker,
exchange, order-routing, or real execution path.
"""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .paper_ledger import PaperLedger
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
    lifecycle_event_id: str | None = None


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
                    snapshot TEXT NOT NULL,
                    lifecycle_event_id TEXT
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(paper_decisions)").fetchall()
            }
            if "lifecycle_event_id" not in columns:
                connection.execute("ALTER TABLE paper_decisions ADD COLUMN lifecycle_event_id TEXT")

    def record(
        self,
        *,
        evaluation_id: str,
        result: EvaluationResult,
        approved_by_human: bool,
        hypothetical_action: str,
        notes: str = "",
        price: float | None = None,
        quantity: float | None = None,
    ) -> str:
        action = hypothetical_action.strip().lower()
        if action not in {"observe", "paper_entry", "paper_exit", "paper_skip"}:
            raise ValueError("unsupported hypothetical paper action")
        lifecycle_action = {"paper_entry": "ENTRY", "paper_exit": "EXIT"}.get(action)
        if lifecycle_action and not approved_by_human:
            raise ValueError(f"{action.replace('_', ' ')} requires explicit human approval")
        if lifecycle_action and (result.decision.blocked or result.risk.blocked):
            raise ValueError("blocked evaluation cannot become a paper lifecycle event")
        if lifecycle_action and (price is None or quantity is None):
            raise ValueError("paper entry and exit require price and quantity")

        paper_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        snapshot = json.dumps(asdict(result), default=str, sort_keys=True, separators=(",", ":"))
        lifecycle_event_id = None
        lifecycle_ledger = PaperLedger(self.database) if lifecycle_action else None

        # Lifecycle event and decision are committed as one SQLite transaction.
        # Any failure rolls both writes back, preventing orphan paper events.
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            if lifecycle_action:
                lifecycle_event_id = lifecycle_ledger.append_with_connection(
                    connection,
                    evaluation_id=evaluation_id,
                    asset=result.signal.asset,
                    action=lifecycle_action,
                    price=price,
                    quantity=quantity,
                )
            connection.execute(
                """INSERT INTO paper_decisions
                (paper_id, evaluation_id, asset, created_at, approved_by_human,
                 hypothetical_action, notes, snapshot, lifecycle_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper_id,
                    evaluation_id,
                    result.signal.asset,
                    created_at,
                    int(approved_by_human),
                    action,
                    notes.strip(),
                    snapshot,
                    lifecycle_event_id,
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
                lifecycle_event_id=row["lifecycle_event_id"],
            )
            for row in rows
        ]

    def verify_integrity(self) -> bool:
        """Verify the authoritative paper ENTRY/EXIT hash chain."""
        return PaperLedger(self.database).verify_integrity()
