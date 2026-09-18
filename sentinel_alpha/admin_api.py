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
