"""Browser authentication transport using secure cookies and CSRF tokens."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .auth import AccountStore
from .auth_service import AuthenticationService
from .auth import Role
from .mfa import AdminMfaStore
from .security_audit import SecurityAuditLog
from .sessions import SessionStore, change_password

router = APIRouter(prefix="/v1/auth", tags=["auth"])
SESSION_COOKIE = "__Host-sentinel_session"
CSRF_COOKIE = "__Host-sentinel_csrf"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


def _service() -> tuple[AuthenticationService, SessionStore]:
    database = os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db")
    accounts = AccountStore(database)
    sessions = SessionStore(database)
    audit = SecurityAuditLog(database)
    return AuthenticationService(accounts, sessions, audit), sessions


def _csrf_for_session(token: str) -> str:
    """Bind the browser-visible CSRF value to the opaque server session token."""
    nonce = secrets.token_urlsafe(24)
    binding = hashlib.sha256(f"{token}:{nonce}".encode("utf-8")).hexdigest()
    return f"{nonce}.{binding}"


def _csrf_matches_session(token: str, csrf: str) -> bool:
    try:
        nonce, supplied = csrf.split(".", 1)
    except ValueError:
        return False
    expected = hashlib.sha256(f"{token}:{nonce}".encode("utf-8")).hexdigest()
    return secrets.compare_digest(expected, supplied)


def _set_auth_cookies(response: Response, token: str, csrf: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, secure=True, httponly=True, samesite="strict", path="/"
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, secure=True, httponly=False, samesite="strict", path="/"
    )


def require_trusted_origin(request: Request) -> None:
    """Reject cross-origin browser mutations when an Origin header is present.

    Production may pin one or more exact origins with SENTINEL_TRUSTED_ORIGINS.
    Non-browser clients without Origin remain usable; cookie-authenticated state
    changes still require CSRF everywhere except login.
    """
    origin = request.headers.get("origin")
    if not origin:
        return
    configured = {
        item.strip().rstrip("/")
        for item in os.getenv("SENTINEL_TRUSTED_ORIGINS", "").split(",")
        if item.strip()
    }
    if configured:
        trusted = origin.rstrip("/") in configured
    else:
        trusted = origin.rstrip("/") == str(request.base_url).rstrip("/")
    if not trusted:
        raise HTTPException(status_code=403, detail="untrusted request origin")


def require_csrf(
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> None:
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    if not session_token or not _csrf_matches_session(session_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    require_trusted_origin(request)
    auth, sessions = _service()
    source = request.client.host if request.client else None
    result = auth.login(
        payload.username, payload.password, source=source,
        request_id=request.state.request_id,
    )
    if result.session is None:
        raise HTTPException(
            status_code=429 if result.retry_after_seconds else 401,
            detail="Invalid username or password.",
            headers={"Retry-After": str(result.retry_after_seconds)}
            if result.retry_after_seconds else None,
        )
    csrf = _csrf_for_session(result.session.token)
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
    require_csrf(csrf_cookie, csrf_header, session_token)
    if session_token:
        auth, sessions = _service()
        account = sessions.validate(session_token, allow_password_change_only=True)
        if account is not None:
            sessions.revoke_all(account.user_id)
            auth.audit.append("LOGOUT", success=True, actor_user_id=account.user_id)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=True, httponly=False, samesite="strict")
    return {"logged_out": True}


class MfaChallenge(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class MfaRecoveryChallenge(BaseModel):
    code: str = Field(min_length=32, max_length=32, pattern=r"^[0-9a-fA-F]{32}$")


def _recovery_attempt_allowed(auth: AuthenticationService, user_id: int, session_token: str, source: str | None) -> tuple[bool, int]:
    now = datetime.now(timezone.utc)
    session_fp = hashlib.sha256(session_token.encode()).hexdigest()[:16]
    source_fp = auth._source_fingerprint(source)
    with auth.accounts._connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS mfa_recovery_attempts (
            user_id INTEGER NOT NULL, session_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0,
            blocked_until TEXT, PRIMARY KEY(user_id,session_fingerprint,source_fingerprint)
        )""")
        row = connection.execute(
            "SELECT failures,blocked_until FROM mfa_recovery_attempts WHERE user_id=? AND session_fingerprint=? AND source_fingerprint=?",
            (user_id, session_fp, source_fp or "unknown"),
        ).fetchone()
    if row and row["blocked_until"]:
        until = datetime.fromisoformat(row["blocked_until"])
        if until > now:
            return False, max(1, int((until-now).total_seconds()))
    return True, 0


def _record_recovery_failure(auth: AuthenticationService, user_id: int, session_token: str, source: str | None) -> int:
    now = datetime.now(timezone.utc)
    session_fp = hashlib.sha256(session_token.encode()).hexdigest()[:16]
    source_fp = auth._source_fingerprint(source) or "unknown"
    with auth.accounts._connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS mfa_recovery_attempts (
            user_id INTEGER NOT NULL, session_fingerprint TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0,
            blocked_until TEXT, PRIMARY KEY(user_id,session_fingerprint,source_fingerprint)
        )""")
        row = connection.execute(
            "SELECT failures FROM mfa_recovery_attempts WHERE user_id=? AND session_fingerprint=? AND source_fingerprint=?",
            (user_id, session_fp, source_fp),
        ).fetchone()
        failures = (int(row["failures"]) if row else 0) + 1
        blocked = now + timedelta(minutes=15) if failures >= 5 else None
        connection.execute(
            """INSERT INTO mfa_recovery_attempts(user_id,session_fingerprint,source_fingerprint,failures,blocked_until)
            VALUES(?,?,?,?,?) ON CONFLICT(user_id,session_fingerprint,source_fingerprint)
            DO UPDATE SET failures=excluded.failures,blocked_until=excluded.blocked_until""",
            (user_id, session_fp, source_fp, failures, blocked.isoformat() if blocked else None),
        )
    return 900 if blocked else 0


def _clear_recovery_failures(auth: AuthenticationService, user_id: int, session_token: str, source: str | None) -> None:
    with auth.accounts._connect() as connection:
        connection.execute(
            "DELETE FROM mfa_recovery_attempts WHERE user_id=? AND session_fingerprint=? AND source_fingerprint=?",
            (user_id, hashlib.sha256(session_token.encode()).hexdigest()[:16], auth._source_fingerprint(source) or "unknown"),
        )


@router.post("/mfa/recovery/verify")
def verify_mfa_recovery(
    payload: MfaRecoveryChallenge,
    request: Request,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header, session_token)
    if not session_token:
        raise HTTPException(status_code=401, detail="authentication required")
    auth, sessions = _service()
    account = sessions.validate(session_token)
    if account is None or account.role is not Role.ADMIN:
        raise HTTPException(status_code=401, detail="authentication required")
    source = request.client.host if request.client else None
    allowed, retry = _recovery_attempt_allowed(auth, account.user_id, session_token, source)
    if not allowed:
        auth.audit.append("MFA_RECOVERY_RATE_LIMITED", success=False, actor_user_id=account.user_id)
        raise HTTPException(status_code=429, detail="MFA verification failed", headers={"Retry-After": str(retry)})
    mfa = AdminMfaStore(auth.accounts.database, auth.audit)
    if not mfa.enabled(account) or not mfa.verify_recovery_code(account, payload.code.casefold()):
        retry = _record_recovery_failure(auth, account.user_id, session_token, source)
        raise HTTPException(status_code=429 if retry else 401, detail="MFA verification failed", headers={"Retry-After": str(retry)} if retry else None)
    _clear_recovery_failures(auth, account.user_id, session_token, source)
    sessions.mark_mfa_verified(session_token, account.user_id)
    return {"mfa_verified": True, "factor": "recovery_code"}


@router.post("/mfa/verify")
def verify_mfa(
    payload: MfaChallenge,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header, session_token)
    if not session_token:
        raise HTTPException(status_code=401, detail="authentication required")
    auth, sessions = _service()
    account = sessions.validate(session_token)
    if account is None:
        raise HTTPException(status_code=401, detail="authentication required")
    if account.role is not Role.ADMIN:
        raise HTTPException(status_code=403, detail="administrator authorization required")
    mfa = AdminMfaStore(auth.accounts.database, auth.audit)
    if not mfa.verify(account, payload.code):
        raise HTTPException(status_code=401, detail="MFA verification failed")
    sessions.mark_mfa_verified(session_token, account.user_id)
    return {"mfa_verified": True}


@router.post("/password")
def update_password(
    payload: PasswordChangeRequest,
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header, session_token)
    if not session_token:
        raise HTTPException(status_code=401, detail="authentication required")
    if len(payload.new_password) < 12 or len(payload.new_password) > 1024:
        raise HTTPException(status_code=422, detail="new password must be 12 to 1024 characters")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=422, detail="new password must differ from current password")
    auth, sessions = _service()
    account = sessions.validate(session_token, allow_password_change_only=True)
    if account is None:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        change_password(
            auth.accounts, sessions, account=account,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as exc:
        auth.audit.append("PASSWORD_CHANGE_FAILED", success=False, actor_user_id=account.user_id)
        raise HTTPException(status_code=400, detail="password change failed") from exc
    refreshed = auth.accounts.authenticate(account.username, payload.new_password)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="password change could not establish a new session")
    new_session = sessions.create(refreshed)
    csrf = _csrf_for_session(new_session.token)
    _set_auth_cookies(response, new_session.token, csrf)
    auth.audit.append("PASSWORD_CHANGED", success=True, actor_user_id=account.user_id)
    mfa = AdminMfaStore(auth.accounts.database, auth.audit)
    mfa_enrolled = refreshed.role is Role.ADMIN and mfa.enabled(refreshed)
    return {
        "password_changed": True,
        "authenticated": True,
        "mfa_required": refreshed.role is Role.ADMIN,
        "mfa_enrolled": mfa_enrolled,
        "mfa_setup_required": refreshed.role is Role.ADMIN and not mfa_enrolled,
    }


def _admin_for_mfa(session_token: str | None) -> tuple[AuthenticationService, SessionStore, object]:
    if not session_token:
        raise HTTPException(status_code=401, detail="authentication required")
    auth, sessions = _service()
    account = sessions.validate(session_token)
    if account is None:
        raise HTTPException(status_code=401, detail="authentication required")
    if account.role is not Role.ADMIN:
        raise HTTPException(status_code=403, detail="administrator authorization required")
    return auth, sessions, account


@router.post("/mfa/enroll")
def enroll_mfa(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header, session_token)
    auth, sessions, account = _admin_for_mfa(session_token)
    mfa = AdminMfaStore(auth.accounts.database, auth.audit)
    if mfa.enabled(account):
        raise HTTPException(status_code=409, detail="MFA is already enabled")
    enrollment = mfa.begin_enrollment(account)
    return {
        "secret": enrollment.secret,
        "provisioning_uri": enrollment.provisioning_uri,
        "instructions": [
            "Add Sentinel Alpha to your authenticator app.",
            "Enter the current 6-digit code to confirm setup.",
            "Keep this setup screen private.",
        ],
    }


@router.post("/mfa/recovery/generate")
def generate_mfa_recovery_codes(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header, session_token)
    auth, sessions, account = _admin_for_mfa(session_token)
    if not sessions.mfa_verified(session_token):
        raise HTTPException(status_code=403, detail="administrator MFA verification required")
    codes = AdminMfaStore(auth.accounts.database, auth.audit).generate_recovery_codes(account)
    return {"recovery_codes": codes, "display_once": True}


@router.post("/mfa/confirm")
def confirm_mfa(
    payload: MfaChallenge,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> dict:
    require_csrf(csrf_cookie, csrf_header, session_token)
    auth, sessions, account = _admin_for_mfa(session_token)
    mfa = AdminMfaStore(auth.accounts.database, auth.audit)
    if not mfa.confirm_enrollment(account, payload.code):
        raise HTTPException(status_code=400, detail="That verification code was not accepted. Try the current code.")
    sessions.mark_mfa_verified(session_token, account.user_id)
    return {
        "mfa_enabled": True,
        "mfa_verified": True,
        "next_step": "dashboard",
    }
