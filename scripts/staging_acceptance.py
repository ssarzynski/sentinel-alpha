"""Offline staging acceptance checks for Sentinel Alpha.

This command is deliberately read-only with respect to financial actions. It checks
the local HTTP service and reports PASS/FAIL without enabling providers or execution.
"""

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request


def fetch_json(base_url: str, path: str) -> tuple[int, object]:
    url = base_url.rstrip("/") + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def check(base_url: str) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    try:
        status, health = fetch_json(base_url, "/health")
        ok = status == 200 and health == {"status": "ok", "service": "sentinel-alpha"}
        results.append(("health", ok, f"HTTP {status}"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return [("health", False, str(exc))]

    try:
        status, rules = fetch_json(base_url, "/v1/rules")
        required = {
            "minimum_independent_confirmations": 2,
            "maximum_new_entries_per_week": 2,
            "options_allowed": False,
            "leverage_allowed": False,
            "human_approval_required": True,
            "automatic_trading": False,
        }
        ok = status == 200 and isinstance(rules, dict) and all(
            rules.get(key) == value for key, value in required.items()
        )
        results.append(("financial_safety_rules", ok, f"HTTP {status}"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(("financial_safety_rules", False, str(exc)))

    try:
        status, audit = fetch_json(base_url, "/v1/audit/verify")
        ok = status == 200 and isinstance(audit, dict) and audit.get("valid") is True
        results.append(("audit_chain", ok, f"HTTP {status}"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(("audit_chain", False, str(exc)))

    try:
        status, summary = fetch_json(base_url, "/v1/dashboard/summary")
        ok = (
            status == 200
            and isinstance(summary, dict)
            and summary.get("automatic_trading") is False
            and summary.get("human_approval_required") is True
            and summary.get("audit_chain_valid") is True
        )
        results.append(("dashboard_safety", ok, f"HTTP {status}"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        results.append(("dashboard_safety", False, str(exc)))
    return results


def evidence(results: list[tuple[str, bool, str]], base_url: str, commit: str = "") -> dict:
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "commit": commit,
        "host": platform.node(),
        "python": platform.python_version(),
        "checks": [
            {"name": name, "passed": passed, "detail": detail}
            for name, passed, detail in results
        ],
        "passed": bool(results) and all(item[1] for item in results),
    }


def write_evidence(path: str, record: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--evidence-file",
        help="Optional JSON output path outside the repository for staging evidence.",
    )
    parser.add_argument("--commit", default="", help="Exact approved commit SHA under test.")
    args = parser.parse_args()
    results = check(args.base_url)
    record = evidence(results, args.base_url, args.commit)
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
    if args.evidence_file:
        write_evidence(args.evidence_file, record)
        print(f"EVIDENCE {args.evidence_file}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
