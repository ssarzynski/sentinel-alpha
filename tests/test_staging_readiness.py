from pathlib import Path


def test_staging_environment_template_preserves_execution_boundary():
    env = Path(".env.example").read_text(encoding="utf-8")
    assert "SENTINEL_AUTOMATIC_TRADING=false" in env
    assert "SENTINEL_HUMAN_APPROVAL_REQUIRED=true" in env


def test_staging_runbook_keeps_public_exposure_as_separate_gate():
    runbook = Path("docs/SELF-HOSTED-STAGING.md").read_text(encoding="utf-8")
    assert "unsupported Windows host" in runbook
    assert "Private-LAN success does not authorize Internet exposure." in runbook
    assert "Public exposure is a separate approval gate." in runbook
    assert "restore it to a **new** path" in runbook
