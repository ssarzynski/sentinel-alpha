"""Cross-check Sentinel Alpha recovery evidence records."""

import argparse
import json
import sys
from pathlib import Path


def load_record(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evidence must be a JSON object")
    return value


def verify_bundle(backup: dict, restored: dict, acceptance: dict) -> list[tuple[str, bool]]:
    records = (backup, restored, acceptance)
    drill_ids = {record.get("drill_id") for record in records}
    commits = {record.get("commit") for record in records}
    digests_match = (
        isinstance(backup.get("backup_sha256"), str)
        and isinstance(backup.get("restored_sha256"), str)
        and len(backup["backup_sha256"]) == 64
        and backup["backup_sha256"] == backup["restored_sha256"]
    )
    return [
        ("schema_v2", all(record.get("schema_version") == 2 for record in records)),
        ("drill_id_present_and_equal", len(drill_ids) == 1 and "" not in drill_ids and None not in drill_ids),
        ("commit_present_and_equal", len(commits) == 1 and "" not in commits and None not in commits),
        ("all_stages_passed", all(record.get("passed") is True for record in records)),
        ("recovery_artifact_digest_match", digests_match),
        ("restored_instance_mode", restored.get("mode") == "restored_instance_read_only"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-evidence", required=True)
    parser.add_argument("--restored-evidence", required=True)
    parser.add_argument("--acceptance-evidence", required=True)
    args = parser.parse_args()
    try:
        backup = load_record(Path(args.backup_evidence))
        restored = load_record(Path(args.restored_evidence))
        acceptance = load_record(Path(args.acceptance_evidence))
        checks = verify_bundle(backup, restored, acceptance)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL evidence_bundle: {type(exc).__name__}")
        return 1
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
