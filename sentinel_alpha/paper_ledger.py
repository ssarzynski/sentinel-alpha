"""Tamper-evident paper-decision ledger. This module cannot execute trades."""

import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

GENESIS_HASH = "0" * 64
VALID_ACTIONS = frozenset({"ENTRY", "EXIT"})


def _hash(previous_hash: str, event_id: str, created_at: str, asset: str, action: str, price: float, quantity: float, evaluation_id: str) -> str:
    material = json.dumps([previous_hash, event_id, created_at, asset, action, price, quantity, evaluation_id], separators=(",", ":")).encode()
    return hashlib.sha256(material).hexdigest()


class PaperLedger:
    def __init__(self, database: str | Path = "sentinel_alpha.db") -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("""CREATE TABLE IF NOT EXISTS paper_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                asset TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('ENTRY','EXIT')),
                price REAL NOT NULL CHECK(price > 0),
                quantity REAL NOT NULL CHECK(quantity > 0),
                evaluation_id TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL UNIQUE,
                FOREIGN KEY(evaluation_id) REFERENCES evaluations(evaluation_id)
            )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def append(self, *, evaluation_id: str, asset: str, action: str, price: float, quantity: float) -> str:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return self.append_with_connection(
                connection,
                evaluation_id=evaluation_id,
                asset=asset,
                action=action,
                price=price,
                quantity=quantity,
            )

    def append_with_connection(
        self,
        connection: sqlite3.Connection,
        *,
        evaluation_id: str,
        asset: str,
        action: str,
        price: float,
        quantity: float,
    ) -> str:
        asset = asset.strip().upper()
        action = action.strip().upper()
        if not asset:
            raise ValueError("asset is required")
        if action not in VALID_ACTIONS:
            raise ValueError("action must be ENTRY or EXIT")
        if not math.isfinite(price) or price <= 0 or not math.isfinite(quantity) or quantity <= 0:
            raise ValueError("price and quantity must be finite and greater than zero")
        event_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        evaluation = connection.execute("SELECT asset FROM evaluations WHERE evaluation_id = ?", (evaluation_id,)).fetchone()
        if evaluation is None:
            raise ValueError("paper event requires an existing evaluation")
        if evaluation["asset"].upper() != asset:
            raise ValueError("paper event asset must match its evaluation")
        if action == "EXIT":
            balance = connection.execute(
                    """SELECT COALESCE(SUM(CASE action WHEN 'ENTRY' THEN quantity ELSE -quantity END),0)
                       FROM paper_events WHERE asset = ?""", (asset,)
                ).fetchone()[0]
            if quantity > balance:
                raise ValueError("paper exit quantity exceeds open paper position")
        previous = connection.execute("SELECT entry_hash FROM paper_events ORDER BY sequence DESC LIMIT 1").fetchone()
        previous_hash = previous["entry_hash"] if previous else GENESIS_HASH
        entry_hash = _hash(previous_hash, event_id, created_at, asset, action, price, quantity, evaluation_id)
        connection.execute("""INSERT INTO paper_events
                (event_id,created_at,asset,action,price,quantity,evaluation_id,previous_hash,entry_hash)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (event_id,created_at,asset,action,price,quantity,evaluation_id,previous_hash,entry_hash))
        return event_id

    def verify_integrity(self) -> bool:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM paper_events ORDER BY sequence").fetchall()
        previous = GENESIS_HASH
        for row in rows:
            if row["previous_hash"] != previous:
                return False
            expected = _hash(previous,row["event_id"],row["created_at"],row["asset"],row["action"],row["price"],row["quantity"],row["evaluation_id"])
            if row["entry_hash"] != expected:
                return False
            previous = row["entry_hash"]
        return True
