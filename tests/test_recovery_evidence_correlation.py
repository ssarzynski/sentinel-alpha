import importlib.util
import sqlite3
from pathlib import Path

_MODULE_PATH = Path(__file__).parents[1] / "scripts" / "backup_restore_drill.py"
_SPEC = importlib.util.spec_from_file_location("backup_restore_drill_corr", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_backup_drill_evidence_carries_correlation_and_digests(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('alpha')")

    record = _MODULE.run_drill(
        source, backup, restored, drill_id="drill-123", commit="abc123"
    )

    assert record["passed"] is True
    assert record["schema_version"] == 2
    assert record["drill_id"] == "drill-123"
    assert record["commit"] == "abc123"
    assert len(record["backup_sha256"]) == 64
    assert len(record["restored_sha256"]) == 64
    assert record["backup_sha256"] == record["restored_sha256"]
