from pathlib import Path
BROWSER=(Path(__file__).parents[1]/"sentinel_alpha"/"browser_auth.py").read_text()
JS=(Path(__file__).parents[1]/"sentinel_alpha"/"static"/"app.js").read_text()

def test_password_change_reports_and_routes_mfa_state():
    assert '"mfa_enrolled": mfa_enrolled' in BROWSER
    assert '"mfa_setup_required": refreshed.role is Role.ADMIN and not mfa_enrolled' in BROWSER
    assert "if(b.mfa_setup_required)" in JS
    assert "else if(b.mfa_enrolled)" in JS
    assert "Your MFA is already set up." in JS
