"""Tamper-evident security audit event journal."""

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class SecurityEvent:
    event_id: str
    created_at: str
    event_type: str
    success: bool
    actor_user_id: int | None = None
    target_user_id: int | None = None
    request_id: str | None = None
    metadata: dict[str, str] | None = None


class SecurityAuditLog:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS security_audit_log (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_user_id INTEGER,
                    target_user_id INTEGER,
                    success INTEGER NOT NULL,
                    request_id TEXT,
                    payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL UNIQUE
                )"""
            )

    @staticmethod
    def _hash(previous_hash: str, payload: str) -> str:
        return hashlib.sha256((previous_hash + payload).encode()).hexdigest()

    def append(
        self,
        event_type: str,
        *,
        success: bool,
        actor_user_id: int | None = None,
        target_user_id: int | None = None,
        request_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            success=success,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            request_id=request_id,
            metadata=metadata,
        )
        payload = json.dumps(asdict(event), sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT entry_hash FROM security_audit_log ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous = row["entry_hash"] if row else GENESIS_HASH
            entry_hash = self._hash(previous, payload)
            connection.execute(
                """INSERT INTO security_audit_log
                (event_id,created_at,event_type,actor_user_id,target_user_id,success,request_id,
                 payload,previous_hash,entry_hash) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (event.event_id, event.created_at, event.event_type, event.actor_user_id,
                 event.target_user_id, int(event.success), event.request_id, payload,
                 previous, entry_hash),
            )
        return event

    def verify_integrity(self) -> bool:
        previous = GENESIS_HASH
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload,previous_hash,entry_hash FROM security_audit_log ORDER BY sequence"
            ).fetchall()
        for row in rows:
            if row["previous_hash"] != previous:
                return False
            if row["entry_hash"] != self._hash(previous, row["payload"]):
                return False
            previous = row["entry_hash"]
        return True

    def recent(self, limit: int = 50) -> list[SecurityEvent]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM security_audit_log ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        return [SecurityEvent(**json.loads(row["payload"])) for row in rows]
