"""Verified SQLite backup and restore helpers for launch recovery readiness."""

import sqlite3
from pathlib import Path


class BackupVerificationError(RuntimeError):
    pass


def _integrity_check(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise BackupVerificationError(f"SQLite integrity check failed for {database}")


def create_verified_backup(source: str | Path, destination: str | Path) -> Path:
    """Create a transactionally consistent SQLite backup and verify its integrity."""
    source_path = Path(source)
    destination_path = Path(destination)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        raise FileExistsError(destination_path)

    with sqlite3.connect(source_path) as source_db:
        with sqlite3.connect(destination_path) as backup_db:
            source_db.backup(backup_db)

    try:
        _integrity_check(destination_path)
    except Exception:
        destination_path.unlink(missing_ok=True)
        raise
    return destination_path


def restore_verified_backup(backup: str | Path, destination: str | Path) -> Path:
    """Verify a backup before restoring it to a new database path."""
    backup_path = Path(backup)
    destination_path = Path(destination)
    if not backup_path.is_file():
        raise FileNotFoundError(backup_path)
    if destination_path.exists():
        raise FileExistsError(destination_path)

    _integrity_check(backup_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(backup_path) as backup_db:
        with sqlite3.connect(destination_path) as restored_db:
            backup_db.backup(restored_db)
    try:
        _integrity_check(destination_path)
    except Exception:
        destination_path.unlink(missing_ok=True)
        raise
    return destination_path
