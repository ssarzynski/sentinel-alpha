from pathlib import Path
JS=(Path(__file__).parents[1]/"sentinel_alpha"/"static"/"app.js").read_text()

def test_admin_security_controls_are_present():
    for action in ["disable","lock","enable","unlock","require-password-change","sessions/revoke"]:
        assert 'data-action="'+action+'"' in JS
    assert "Financial approvals are separate from account administration." in JS
    assert 'window.confirm' in JS
    assert '"X-CSRF-Token"' in JS
