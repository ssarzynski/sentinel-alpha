"""Protected HTTP administrator API for Sentinel Alpha."""

import os

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel

from .admin_accounts import AdminAccountService
from .admin_dashboard import AdminDashboardService
from .auth import AccountStatus, AccountStore, Role, UserAccount, require_admin
from .browser_auth import SESSION_COOKIE, require_csrf
from .mfa import AdminMfaStore
from .security_audit import SecurityAuditLog
from .sessions import SessionStore

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _stores() -> tuple[AccountStore, SessionStore, SecurityAuditLog]:
    database = os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db")
    return AccountStore(database), SessionStore(database), SecurityAuditLog(database)


def authenticated_admin(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> UserAccount:
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    accounts, sessions, audit = _stores()
    account = sessions.validate(token)
    if account is None:
        audit.append("ADMIN_ACCESS_DENIED", success=False)
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        require_admin(account)
    except PermissionError as exc:
        audit.append("ADMIN_ACCESS_DENIED", success=False, actor_user_id=account.user_id)
        raise HTTPException(status_code=403, detail="administrator authorization required") from exc
    mfa = AdminMfaStore(accounts.database, audit)
    if not mfa.enabled(account) or not sessions.mfa_verified(token):
        audit.append("ADMIN_MFA_REQUIRED", success=False, actor_user_id=account.user_id)
        raise HTTPException(status_code=403, detail="administrator MFA required")
    return account


class RoleChange(BaseModel):
    role: Role


class PasswordPolicyChange(BaseModel):
    expiration_days: int


@router.get("/users")
def users(actor: UserAccount = Depends(authenticated_admin)) -> list[dict]:
    accounts, sessions, audit = _stores()
    service = AdminAccountService(accounts, sessions)
    return [
        {"user_id": item.user_id, "username": item.username, "role": item.role, "status": item.status}
        for item in service.list_users(actor)
    ]


@router.get("/pending")
def pending(actor: UserAccount = Depends(authenticated_admin)) -> list[dict]:
    accounts, sessions, audit = _stores()
    service = AdminAccountService(accounts, sessions)
    return [
        {"user_id": item.user_id, "username": item.username, "role": item.role, "status": item.status}
        for item in service.list_users(actor, status=AccountStatus.PENDING_APPROVAL)
    ]


def _status_action(actor: UserAccount, user_id: int, status: AccountStatus, event: str) -> dict:
    accounts, sessions, audit = _stores()
    service = AdminAccountService(accounts, sessions)
    try:
        if status is AccountStatus.ACTIVE:
            service.approve(actor, user_id)
        elif status is AccountStatus.REJECTED:
            service.reject(actor, user_id)
        else:
            service.set_status(actor, user_id, status)
    except (ValueError, LookupError) as exc:
        audit.append(event, success=False, actor_user_id=actor.user_id, target_user_id=user_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.append(event, success=True, actor_user_id=actor.user_id, target_user_id=user_id)
    return {"user_id": user_id, "status": status}


@router.post("/users/{user_id}/approve")
def approve(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    return _status_action(actor, user_id, AccountStatus.ACTIVE, "ACCOUNT_APPROVED")


@router.post("/users/{user_id}/reject")
def reject(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    return _status_action(actor, user_id, AccountStatus.REJECTED, "ACCOUNT_REJECTED")


@router.post("/users/{user_id}/disable")
def disable(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    return _status_action(actor, user_id, AccountStatus.DISABLED, "ACCOUNT_DISABLED")


@router.post("/users/{user_id}/lock")
def lock(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    return _status_action(actor, user_id, AccountStatus.LOCKED, "ACCOUNT_LOCKED")


@router.post("/users/{user_id}/role")
def change_role(
    user_id: int,
    request: RoleChange,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    accounts, sessions, audit = _stores()
    service = AdminAccountService(accounts, sessions)
    try:
        service.set_role(actor, user_id, request.role)
    except (ValueError, LookupError) as exc:
        audit.append("ROLE_CHANGED", success=False, actor_user_id=actor.user_id, target_user_id=user_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.append(
        "ROLE_CHANGED", success=True, actor_user_id=actor.user_id,
        target_user_id=user_id, metadata={"role": request.role.value},
    )
    return {"user_id": user_id, "role": request.role}


@router.get("/dashboard")
def dashboard(actor: UserAccount = Depends(authenticated_admin)) -> dict:
    accounts, sessions, audit = _stores()
    return AdminDashboardService(accounts, sessions, audit).summary(actor)


@router.get("/security-events")
def security_events(
    limit: int = 50,
    actor: UserAccount = Depends(authenticated_admin),
) -> list[dict]:
    accounts, sessions, audit = _stores()
    try:
        return AdminDashboardService(accounts, sessions, audit).security_events(actor, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _recovery_action(actor: UserAccount, user_id: int, action: str) -> dict:
    accounts, sessions, audit = _stores()
    service = AdminAccountService(accounts, sessions)
    try:
        if action == "enable":
            service.enable(actor, user_id)
            status = AccountStatus.ACTIVE
            event = "ACCOUNT_ENABLED"
        else:
            service.unlock(actor, user_id)
            status = AccountStatus.ACTIVE
            event = "ACCOUNT_UNLOCKED"
    except (ValueError, LookupError) as exc:
        audit.append("ACCOUNT_RECOVERY_FAILED", success=False, actor_user_id=actor.user_id, target_user_id=user_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.append(event, success=True, actor_user_id=actor.user_id, target_user_id=user_id)
    return {"user_id": user_id, "status": status}


@router.post("/users/{user_id}/enable")
def enable(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    return _recovery_action(actor, user_id, "enable")


@router.post("/users/{user_id}/unlock")
def unlock(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    return _recovery_action(actor, user_id, "unlock")


@router.get("/password-policy")
def password_policy(actor: UserAccount = Depends(authenticated_admin)) -> dict:
    accounts, sessions, audit = _stores()
    with accounts._connect() as connection:
        row = connection.execute(
            "SELECT expiration_days,updated_at,updated_by FROM password_policy WHERE id=1"
        ).fetchone()
    return {
        "expiration_days": row["expiration_days"],
        "allowed_expiration_days": [30, 60, 90],
        "updated_at": row["updated_at"],
        "updated_by": row["updated_by"],
    }


@router.put("/password-policy")
def update_password_policy(
    request: PasswordPolicyChange,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    if request.expiration_days not in {30, 60, 90}:
        raise HTTPException(status_code=422, detail="expiration_days must be 30, 60, or 90")
    accounts, sessions, audit = _stores()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with accounts._connect() as connection:
        connection.execute(
            """UPDATE password_policy SET expiration_days=?,updated_at=?,updated_by=? WHERE id=1""",
            (request.expiration_days, now, actor.user_id),
        )
    audit.append(
        "PASSWORD_POLICY_CHANGED", success=True, actor_user_id=actor.user_id,
        metadata={"expiration_days": str(request.expiration_days)},
    )
    return {
        "expiration_days": request.expiration_days,
        "allowed_expiration_days": [30, 60, 90],
        "applies_to_new_password_changes": True,
    }

@router.get("/users/{user_id}/sessions")
def user_sessions(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
) -> list[dict]:
    accounts, sessions, audit = _stores()
    # Never expose session tokens or token hashes to the administrator UI.
    with accounts._connect() as connection:
        target = connection.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if target is None:
        raise HTTPException(status_code=404, detail="account not found")
    return sessions.active_sessions(user_id)


@router.post("/users/{user_id}/sessions/revoke")
def revoke_user_sessions(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    if user_id == actor.user_id:
        raise HTTPException(status_code=409, detail="use logout to end your own administrator session")
    accounts, sessions, audit = _stores()
    with accounts._connect() as connection:
        target = connection.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if target is None:
        raise HTTPException(status_code=404, detail="account not found")
    sessions.revoke_all(user_id)
    audit.append("SESSIONS_REVOKED", success=True, actor_user_id=actor.user_id, target_user_id=user_id)
    return {"user_id": user_id, "sessions_revoked": True}

@router.post("/users/{user_id}/require-password-change")
def require_password_change(
    user_id: int,
    actor: UserAccount = Depends(authenticated_admin),
    _: None = Depends(require_csrf),
) -> dict:
    accounts, sessions, audit = _stores()
    service = AdminAccountService(accounts, sessions)
    try:
        service.require_password_change(actor, user_id)
    except (ValueError, LookupError) as exc:
        audit.append("PASSWORD_RESET_REQUIRED", success=False, actor_user_id=actor.user_id, target_user_id=user_id)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit.append("PASSWORD_RESET_REQUIRED", success=True, actor_user_id=actor.user_id, target_user_id=user_id)
    return {"user_id": user_id, "must_change_password": True, "sessions_revoked": True}
