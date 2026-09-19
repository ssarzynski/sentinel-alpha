import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify_recovery_evidence_bundle.py"
_SPEC = importlib.util.spec_from_file_location("verify_recovery_bundle", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def records():
    digest = "a" * 64
    backup = {
        "schema_version": 2, "drill_id": "drill-1", "commit": "abc123",
        "passed": True, "backup_sha256": digest, "restored_sha256": digest,
    }
    restored = {
        "schema_version": 2, "drill_id": "drill-1", "commit": "abc123",
        "passed": True, "mode": "restored_instance_read_only",
    }
    acceptance = {
        "schema_version": 2, "drill_id": "drill-1", "commit": "abc123", "passed": True,
    }
    return backup, restored, acceptance


def result_map(backup, restored, acceptance):
    return dict(_MODULE.verify_bundle(backup, restored, acceptance))


def test_bundle_accepts_correlated_passing_evidence():
    assert all(result_map(*records()).values())


def test_bundle_fails_mismatched_commit():
    backup, restored, acceptance = records()
    acceptance["commit"] = "different"
    assert result_map(backup, restored, acceptance)["commit_present_and_equal"] is False


def test_bundle_fails_mismatched_drill_id():
    backup, restored, acceptance = records()
    restored["drill_id"] = "other"
    assert result_map(backup, restored, acceptance)["drill_id_present_and_equal"] is False


def test_bundle_fails_failed_stage_or_artifact_digest():
    backup, restored, acceptance = records()
    restored["passed"] = False
    backup["restored_sha256"] = "b" * 64
    result = result_map(backup, restored, acceptance)
    assert result["all_stages_passed"] is False
    assert result["recovery_artifact_digest_match"] is False
