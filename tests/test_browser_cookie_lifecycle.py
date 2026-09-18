from fastapi import FastAPI
from fastapi.testclient import TestClient
from sentinel_alpha.browser_auth import BROWSER_SESSION_MAX_AGE, _set_auth_cookies

def test_auth_cookies_have_absolute_lifetime_and_security_flags():
    app=FastAPI()
    @app.get("/")
    def set_cookies(response):
        _set_auth_cookies(response,"opaque-session","bound-csrf")
        return {"ok":True}
    r=TestClient(app,base_url="https://testserver").get("/")
    values=r.headers.get_list("set-cookie")
    assert len(values)==2
    assert all(f"Max-Age={BROWSER_SESSION_MAX_AGE}" in v for v in values)
    assert all("Secure" in v and "SameSite=strict" in v and "Path=/" in v for v in values)
    session=next(v for v in values if "__Host-sentinel_session=" in v)
    csrf=next(v for v in values if "__Host-sentinel_csrf=" in v)
    assert "HttpOnly" in session
    assert "HttpOnly" not in csrf
