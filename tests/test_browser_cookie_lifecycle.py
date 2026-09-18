from fastapi import FastAPI, Response
from sentinel_alpha.browser_auth import BROWSER_SESSION_MAX_AGE, _set_auth_cookies

def test_auth_cookies_have_absolute_lifetime_and_security_flags():
    response = Response()
    _set_auth_cookies(response, "opaque-session", "bound-csrf")
    values = response.headers.getlist("set-cookie")
    assert len(values)==2
    assert all(f"Max-Age={BROWSER_SESSION_MAX_AGE}" in v for v in values)
    assert all("Secure" in v and "SameSite=strict" in v and "Path=/" in v for v in values)
    session=next(v for v in values if "__Host-sentinel_session=" in v)
    csrf=next(v for v in values if "__Host-sentinel_csrf=" in v)
    assert "HttpOnly" in session
    assert "HttpOnly" not in csrf
