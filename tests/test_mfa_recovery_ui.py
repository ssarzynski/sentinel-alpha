from pathlib import Path

ROOT=Path(__file__).parents[1]/"sentinel_alpha"/"static"

def test_recovery_ui_is_present_and_uses_protected_endpoint():
    html=(ROOT/"index.html").read_text()
    js=(ROOT/"app.js").read_text()
    assert 'id="recoveryForm"' in html
    assert 'pattern="[0-9a-fA-F]{32}"' in html
    assert "/v1/auth/mfa/recovery/verify" in js
    assert '"X-CSRF-Token"' in js
    assert "Use recovery code" in html
