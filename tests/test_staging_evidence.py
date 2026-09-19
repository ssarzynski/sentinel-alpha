import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "staging_acceptance.py"
SPEC = importlib.util.spec_from_file_location("staging_acceptance_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_evidence_record_is_machine_readable_and_preserves_failures():
    results = [("health", True, "HTTP 200"), ("audit_chain", False, "integrity_failure")]
    with patch.object(MODULE.platform, "node", return_value="staging-host"), patch.object(
        MODULE.platform, "python_version", return_value="3.12.0"
    ):
        record = MODULE.evidence(results, "http://127.0.0.1:8000", "abc123")
    assert record["schema_version"] == 1
    assert record["host"] == "staging-host"
    assert record["python"] == "3.12.0"
    assert record["commit"] == "abc123"
    assert record["passed"] is False
    assert record["checks"][1]["passed"] is False


def test_write_evidence_creates_json_record(tmp_path):
    destination = tmp_path / "private-evidence" / "acceptance.json"
    record = {"schema_version": 1, "passed": True, "checks": []}
    MODULE.write_evidence(str(destination), record)
    assert json.loads(destination.read_text(encoding="utf-8")) == record
