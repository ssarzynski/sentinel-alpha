import importlib.util
from pathlib import Path
from unittest.mock import patch

_MODULE_PATH = Path(__file__).parents[1] / "scripts" / "staging_acceptance.py"
_SPEC = importlib.util.spec_from_file_location("staging_acceptance", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
check = _MODULE.check


def test_acceptance_checker_requires_safety_invariants():
    responses = {
        "/health": (200, {"status": "ok", "service": "sentinel-alpha"}),
        "/v1/rules": (
            200,
            {
                "minimum_independent_confirmations": 2,
                "maximum_new_entries_per_week": 2,
                "options_allowed": False,
                "leverage_allowed": False,
                "human_approval_required": True,
                "automatic_trading": False,
            },
        ),
        "/v1/audit/verify": (200, {"valid": True, "status": "verified"}),
        "/v1/dashboard/summary": (
            200,
            {
                "automatic_trading": False,
                "human_approval_required": True,
                "audit_chain_valid": True,
                "paper_ledger_valid": True,
            },
        ),
    }

    def fake_fetch(_base_url, path):
        return responses[path]

    with patch.object(_MODULE, "fetch_json", side_effect=fake_fetch):
        results = check("http://127.0.0.1:8000")
    assert results
    assert all(item[1] for item in results)


def test_acceptance_checker_fails_if_automatic_trading_is_reported_enabled():
    responses = {
        "/health": (200, {"status": "ok", "service": "sentinel-alpha"}),
        "/v1/rules": (
            200,
            {
                "minimum_independent_confirmations": 2,
                "maximum_new_entries_per_week": 2,
                "options_allowed": False,
                "leverage_allowed": False,
                "human_approval_required": True,
                "automatic_trading": True,
            },
        ),
        "/v1/audit/verify": (200, {"valid": True}),
        "/v1/dashboard/summary": (
            200,
            {
                "automatic_trading": False,
                "human_approval_required": True,
                "audit_chain_valid": True,
                "paper_ledger_valid": True,
            },
        ),
    }

    def fake_fetch(_base_url, path):
        return responses[path]

    with patch.object(_MODULE, "fetch_json", side_effect=fake_fetch):
        results = check("http://127.0.0.1:8000")
    by_name = {name: passed for name, passed, _ in results}
    assert by_name["financial_safety_rules"] is False


def test_acceptance_checker_fails_if_paper_ledger_is_invalid():
    responses = {
        "/health": (200, {"status": "ok", "service": "sentinel-alpha"}),
        "/v1/rules": (
            200,
            {
                "minimum_independent_confirmations": 2,
                "maximum_new_entries_per_week": 2,
                "options_allowed": False,
                "leverage_allowed": False,
                "human_approval_required": True,
                "automatic_trading": False,
            },
        ),
        "/v1/audit/verify": (200, {"valid": True}),
        "/v1/dashboard/summary": (
            200,
            {
                "automatic_trading": False,
                "human_approval_required": True,
                "audit_chain_valid": True,
                "paper_ledger_valid": False,
            },
        ),
    }

    def fake_fetch(_base_url, path):
        return responses[path]

    with patch.object(_MODULE, "fetch_json", side_effect=fake_fetch):
        results = check("http://127.0.0.1:8000")
    by_name = {name: passed for name, passed, _ in results}
    assert by_name["dashboard_safety"] is False
