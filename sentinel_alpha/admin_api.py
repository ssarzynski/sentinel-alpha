"""Protected HTTP administrator API for Sentinel Alpha."""

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .admin_accounts import AdminAccountService
from .auth import AccountStatus, AccountStore, Role, UserAccount, require_admin
from .security_audit import SecurityAuditLog
from .sessions import SessionStore

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _stores() -> tuple[AccountStore, SessionStore, SecurityAuditLog]:
    database = os.getenv("SENTINEL_DB_PATH", "sentinel_alpha.db")
    return AccountStore(database), SessionStore(database), SecurityAuditLog(database)


def authenticated_admin(authorization: str | None = Header(default=None)) -> UserAccount:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization.removeprefix("Bearer ").strip()
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
def approve(user_id: int, actor: UserAccount = Depends(authenticated_admin)) -> dict:
    return _status_action(actor, user_id, AccountStatus.ACTIVE, "ACCOUNT_APPROVED")


@router.post("/users/{user_id}/reject")
def reject(user_id: int, actor: UserAccount = Depends(authenticated_admin)) -> dict:
    return _status_action(actor, user_id, AccountStatus.REJECTED, "ACCOUNT_REJECTED")


@router.post("/users/{user_id}/disable")
def disable(user_id: int, actor: UserAccount = Depends(authenticated_admin)) -> dict:
    return _status_action(actor, user_id, AccountStatus.DISABLED, "ACCOUNT_DISABLED")


@router.post("/users/{user_id}/lock")
def lock(user_id: int, actor: UserAccount = Depends(authenticated_admin)) -> dict:
    return _status_action(actor, user_id, AccountStatus.LOCKED, "ACCOUNT_LOCKED")


@router.post("/users/{user_id}/role")
def change_role(user_id: int, request: RoleChange, actor: UserAccount = Depends(authenticated_admin)) -> dict:
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
