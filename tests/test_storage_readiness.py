import sqlite3

import pytest

from sentinel_alpha.storage_readiness import online_backup, readiness


def test_readiness_checks_database_integrity(tmp_path):
    database = tmp_path / "sentinel.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES ('ok')")
    status = readiness(database)
    assert status.integrity_ok is True
    assert status.foreign_keys is True
    assert status.journal_mode in {"delete", "wal", "truncate", "persist", "memory", "off"}


def test_online_backup_is_readable_and_preserves_data(tmp_path):
    database = tmp_path / "sentinel.db"
    backup = tmp_path / "backups" / "sentinel.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('preserved')")
    online_backup(database, backup)
    with sqlite3.connect(backup) as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "preserved"
    assert readiness(backup).integrity_ok is True


def test_backup_refuses_source_overwrite(tmp_path):
    database = tmp_path / "sentinel.db"
    with sqlite3.connect(database):
        pass
    with pytest.raises(ValueError, match="must differ"):
        online_backup(database, database)
