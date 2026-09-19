import importlib.util
import sqlite3
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "backup_restore_drill.py"
SPEC = importlib.util.spec_from_file_location("backup_restore_drill", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_drill_preserves_tables_and_rows(tmp_path):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        connection.executemany("INSERT INTO sample(value) VALUES(?)", [("a",), ("b",)])

    record = MODULE.run_drill(
        source, tmp_path / "backup.db", tmp_path / "restored.db"
    )
    assert record["passed"] is True
    assert {check["name"] for check in record["checks"]} == {
        "backup_integrity",
        "restore_integrity",
        "table_row_counts_preserved",
    }


def test_drill_fails_closed_when_destination_exists(tmp_path):
    source = tmp_path / "source.db"
    sqlite3.connect(source).close()
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"existing")
    record = MODULE.run_drill(source, backup, tmp_path / "restored.db")
    assert record["passed"] is False
    assert record["checks"][-1]["name"] == "drill_exception"
