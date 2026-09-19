"""Read-only application verification for a restored Sentinel Alpha staging instance."""

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request


def fetch_json(base_url: str, path: str) -> tuple[int, object]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path, headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def check(base_url: str) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    endpoints = (
        ("health", "/health", lambda body: body == {"status": "ok", "service": "sentinel-alpha"}),
        ("audit_chain", "/v1/audit/verify", lambda body: isinstance(body, dict) and body.get("valid") is True),
        ("journal_reads", "/v1/evaluations?limit=1", lambda body: isinstance(body, list)),
        ("paper_history_reads", "/v1/paper-decisions?limit=1", lambda body: isinstance(body, list)),
        (
            "dashboard_reads",
            "/v1/dashboard/summary",
            lambda body: (
                isinstance(body, dict)
                and body.get("audit_chain_valid") is True
                and body.get("paper_ledger_valid") is True
                and body.get("automatic_trading") is False
                and body.get("human_approval_required") is True
            ),
        ),
    )
    for name, path, validator in endpoints:
        try:
            status, body = fetch_json(base_url, path)
            checks.append((name, status == 200 and validator(body), f"HTTP {status}"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            checks.append((name, False, type(exc).__name__))
    return checks


def evidence(results: list[tuple[str, bool, str]], base_url: str, commit: str) -> dict:
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "commit": commit,
        "host": platform.node(),
        "python": platform.python_version(),
        "mode": "restored_instance_read_only",
        "checks": [
            {"name": name, "passed": passed, "detail": detail}
            for name, passed, detail in results
        ],
        "passed": bool(results) and all(item[1] for item in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--evidence-file", required=True)
    args = parser.parse_args()
    results = check(args.base_url)
    record = evidence(results, args.base_url, args.commit)
    destination = Path(args.evidence_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
    print(f"EVIDENCE {destination}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
