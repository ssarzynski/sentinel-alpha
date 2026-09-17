"""Browser authentication transport using secure cookies and CSRF tokens."""

import hashlib
import os
import secrets

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from pydantic import BaseModel

from .auth import AccountStore
from .auth_service import AuthenticationService
from .security_audit import SecurityAuditLog
from .sessions import SessionStore

router = APIRouter(prefix="/v1/auth", tags=["auth"])
SESSION_COOKIE = "__Host-sentinel_session"
CSRF_COOKIE = "__Host-sentinel_csrf"


class LoginRequest(BaseModel):
    username: str
    password: str


def _service() -> tuple[AuthenticationService, SessionStore]:
    database = os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db")
    accounts = AccountStore(database)
    sessions = SessionStore(database)
    audit = SecurityAuditLog(database)
    return AuthenticationService(accounts, sessions, audit), sessions


def _set_auth_cookies(response: Response, token: str, csrf: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, secure=True, httponly=True, samesite="strict", path="/"
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, secure=True, httponly=False, samesite="strict", path="/"
    )


def require_csrf(
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    auth, sessions = _service()
    source = request.client.host if request.client else None
    result = auth.login(
        payload.username, payload.password, source=source,
        request_id=request.headers.get("X-Request-ID"),
    )
    if result.session is None:
        raise HTTPException(
            status_code=429 if result.retry_after_seconds else 401,
            detail="Invalid username or password.",
            headers={"Retry-After": str(result.retry_after_seconds)}
            if result.retry_after_seconds else None,
        )
    csrf = secrets.token_urlsafe(32)
    _set_auth_cookies(response, result.session.token, csrf)
    return {
        "authenticated": True,
        "password_change_required": result.session.restricted_to_password_change,
    }


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header)
    if session_token:
        auth, sessions = _service()
        account = sessions.validate(session_token, allow_password_change_only=True)
        if account is not None:
            sessions.revoke_all(account.user_id)
            auth.audit.append("LOGOUT", success=True, actor_user_id=account.user_id)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=True, httponly=False, samesite="strict")
    return {"logged_out": True}
