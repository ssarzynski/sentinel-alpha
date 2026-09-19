import importlib.util
from pathlib import Path
from unittest.mock import patch

_MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify_restored_instance.py"
_SPEC = importlib.util.spec_from_file_location("verify_restored_instance", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def responses(paper_valid=True):
    return {
        "/health": (200, {"status": "ok", "service": "sentinel-alpha"}),
        "/v1/audit/verify": (200, {"valid": True}),
        "/v1/evaluations?limit=1": (200, []),
        "/v1/paper-decisions?limit=1": (200, []),
        "/v1/dashboard/summary": (
            200,
            {
                "audit_chain_valid": True,
                "paper_ledger_valid": paper_valid,
                "automatic_trading": False,
                "human_approval_required": True,
            },
        ),
    }


def test_restored_instance_verifier_is_read_only_and_accepts_valid_state():
    data = responses()
    requested = []

    def fake_fetch(_base_url, path):
        requested.append(path)
        return data[path]

    with patch.object(_MODULE, "fetch_json", side_effect=fake_fetch):
        results = _MODULE.check("http://127.0.0.1:8000")
    assert all(item[1] for item in results)
    assert requested == [
        "/health",
        "/v1/audit/verify",
        "/v1/evaluations?limit=1",
        "/v1/paper-decisions?limit=1",
        "/v1/dashboard/summary",
    ]


def test_restored_instance_verifier_fails_on_paper_integrity_failure():
    data = responses(paper_valid=False)

    with patch.object(_MODULE, "fetch_json", side_effect=lambda _base, path: data[path]):
        results = _MODULE.check("http://127.0.0.1:8000")
    by_name = {name: passed for name, passed, _ in results}
    assert by_name["dashboard_reads"] is False
