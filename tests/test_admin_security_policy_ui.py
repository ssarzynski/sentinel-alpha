from pathlib import Path
JS=(Path(__file__).parents[1]/"sentinel_alpha"/"static"/"app.js").read_text()

def test_admin_security_policy_and_events_are_protected():
    assert "/v1/admin/password-policy" in JS
    assert "/v1/admin/security-events?limit=20" in JS
    assert 'id="passwordPolicyDays"' in JS
    assert "[30,60,90]" in JS
    assert 'window.confirm("Change password expiration policy' in JS
    assert '"X-CSRF-Token"' in JS
    assert "No success is assumed." in JS
