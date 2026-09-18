import sqlite3

import pytest

from sentinel_alpha.backup import create_verified_backup, restore_verified_backup


def test_backup_and_restore_preserve_database(tmp_path):
    source = tmp_path / "sentinel.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE signals(id INTEGER PRIMARY KEY, asset TEXT NOT NULL)")
        connection.execute("INSERT INTO signals(asset) VALUES('NVDA')")

    backup = create_verified_backup(source, tmp_path / "backups" / "sentinel.db")
    restored = restore_verified_backup(backup, tmp_path / "restored" / "sentinel.db")

    with sqlite3.connect(restored) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT asset FROM signals").fetchone()[0] == "NVDA"


def test_backup_refuses_to_overwrite_existing_file(tmp_path):
    source = tmp_path / "sentinel.db"
    destination = tmp_path / "backup.db"
    sqlite3.connect(source).close()
    destination.write_bytes(b"do-not-overwrite")

    with pytest.raises(FileExistsError):
        create_verified_backup(source, destination)
    assert destination.read_bytes() == b"do-not-overwrite"


def test_restore_rejects_corrupt_backup_without_creating_destination(tmp_path):
    backup = tmp_path / "corrupt.db"
    destination = tmp_path / "restored.db"
    backup.write_bytes(b"not a sqlite database")

    with pytest.raises(sqlite3.DatabaseError):
        restore_verified_backup(backup, destination)
    assert not destination.exists()
