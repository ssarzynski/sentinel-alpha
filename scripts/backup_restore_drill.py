"""Non-destructive backup/restore drill with machine-readable evidence."""

import argparse
import json
import hashlib
import platform
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sentinel_alpha.backup import create_verified_backup, restore_verified_backup


def table_counts(database: Path) -> dict[str, int]:
    with sqlite3.connect(database) as connection:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            name: connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            for name in names
        }



def database_content_fingerprint(database: Path) -> str:
    """Hash logical schema and row content without exposing values in evidence."""
    digest = hashlib.sha256()
    with sqlite3.connect(database) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            digest.update(b"T\0" + table.encode("utf-8") + b"\0")
            columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            for column in columns:
                digest.update(
                    json.dumps(column, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
                    + b"\n"
                )
            rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            for row in rows:
                encoded = []
                for value in row:
                    if isinstance(value, bytes):
                        encoded.append({"blob_sha256": hashlib.sha256(value).hexdigest(), "length": len(value)})
                    else:
                        encoded.append({"type": type(value).__name__, "value": value})
                digest.update(
                    json.dumps(encoded, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
                    + b"\n"
                )
    return digest.hexdigest()

def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_drill(source: Path, backup: Path, restored: Path, drill_id: str = "", commit: str = "") -> dict:
    record = {
        "schema_version": 2,
        "drill_id": drill_id,
        "commit": commit,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "python": platform.python_version(),
        "source": str(source),
        "backup": str(backup),
        "restored": str(restored),
        "passed": False,
        "checks": [],
    }
    try:
        before = table_counts(source)
        source_content_sha256 = database_content_fingerprint(source)
        create_verified_backup(source, backup)
        record["backup_sha256"] = file_sha256(backup)
        record["checks"].append({"name": "backup_integrity", "passed": True})
        restore_verified_backup(backup, restored)
        record["restored_sha256"] = file_sha256(restored)
        record["checks"].append({"name": "restore_integrity", "passed": True})
        after = table_counts(restored)
        restored_content_sha256 = database_content_fingerprint(restored)
        record["source_content_sha256"] = source_content_sha256
        record["restored_content_sha256"] = restored_content_sha256
        content_preserved = source_content_sha256 == restored_content_sha256
        record["checks"].append({"name": "logical_content_preserved", "passed": content_preserved})
        preserved = before == after
        record["checks"].append(
            {"name": "table_row_counts_preserved", "passed": preserved}
        )
        record["passed"] = all(check["passed"] for check in record["checks"])
    except Exception as exc:
        record["checks"].append(
            {"name": "drill_exception", "passed": False, "detail": type(exc).__name__}
        )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--restored", required=True)
    parser.add_argument("--evidence-file", required=True)
    parser.add_argument("--drill-id", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    record = run_drill(Path(args.source), Path(args.backup), Path(args.restored), args.drill_id, args.commit)
    destination = Path(args.evidence_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{'PASS' if record['passed'] else 'FAIL'} backup_restore_drill")
    print(f"EVIDENCE {destination}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
