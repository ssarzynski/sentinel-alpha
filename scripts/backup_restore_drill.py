"""Non-destructive backup/restore drill with machine-readable evidence."""

import argparse
import json
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


def run_drill(source: Path, backup: Path, restored: Path) -> dict:
    record = {
        "schema_version": 1,
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
        create_verified_backup(source, backup)
        record["checks"].append({"name": "backup_integrity", "passed": True})
        restore_verified_backup(backup, restored)
        record["checks"].append({"name": "restore_integrity", "passed": True})
        after = table_counts(restored)
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
    args = parser.parse_args()

    record = run_drill(Path(args.source), Path(args.backup), Path(args.restored))
    destination = Path(args.evidence_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{'PASS' if record['passed'] else 'FAIL'} backup_restore_drill")
    print(f"EVIDENCE {destination}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
