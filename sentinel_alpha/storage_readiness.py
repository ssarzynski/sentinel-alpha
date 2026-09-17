"""SQLite operational readiness checks and safe online backups."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class DatabaseReadiness:
    integrity_ok: bool
    journal_mode: str
    foreign_keys: bool
    checked_at: str


def configure_connection(connection: sqlite3.Connection) -> None:
    """Apply conservative runtime settings to an open SQLite connection."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")


def readiness(database: str | Path) -> DatabaseReadiness:
    path = str(database)
    with sqlite3.connect(path, timeout=30) as connection:
        configure_connection(connection)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
    return DatabaseReadiness(
        integrity_ok=integrity == "ok",
        journal_mode=str(journal_mode).lower(),
        foreign_keys=foreign_keys,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


def online_backup(database: str | Path, destination: str | Path) -> Path:
    """Create a transactionally consistent SQLite backup without mutating source."""
    source_path = Path(database)
    destination_path = Path(destination)
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("backup destination must differ from source database")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path, timeout=30) as source:
        configure_connection(source)
        with sqlite3.connect(destination_path, timeout=30) as target:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError("backup integrity check failed")
    return destination_path
