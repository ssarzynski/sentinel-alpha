from pathlib import Path
JS=(Path(__file__).parents[1]/"sentinel_alpha"/"static"/"app.js").read_text()

def test_pending_admin_actions_are_confirmed_and_csrf_protected():
    assert 'data-action="approve"' in JS
    assert 'data-action="reject"' in JS
    assert 'window.confirm' in JS
    assert '"X-CSRF-Token"' in JS
    assert '"/v1/admin/users/"' in JS
    assert "No success is assumed." in JS
