"""Deny-by-default administrator account approval and lifecycle service."""

from dataclasses import dataclass
from datetime import datetime, timezone

from .auth import AccountStatus, AccountStore, Role, UserAccount, require_admin
from .sessions import SessionStore


@dataclass(frozen=True)
class ManagedUser:
    user_id: int
    username: str
    role: Role
    status: AccountStatus


class AdminAccountService:
    def __init__(self, accounts: AccountStore, sessions: SessionStore) -> None:
        self.accounts = accounts
        self.sessions = sessions

    def list_users(self, actor: UserAccount, *, status: AccountStatus | None = None) -> list[ManagedUser]:
        require_admin(actor)
        query = "SELECT id,username,role,status FROM users"
        params: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status=?"
            params = (status.value,)
        query += " ORDER BY id ASC"
        with self.accounts._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            ManagedUser(row["id"], row["username"], Role(row["role"]), AccountStatus(row["status"]))
            for row in rows
        ]

    def set_status(
        self, actor: UserAccount, target_user_id: int, status: AccountStatus
    ) -> None:
        require_admin(actor)
        if actor.user_id == target_user_id and status is not AccountStatus.ACTIVE:
            raise ValueError("administrator cannot deactivate own active session account")
        if status is not AccountStatus.ACTIVE:
            with self.accounts._connect() as connection:
                target = connection.execute("SELECT role,status FROM users WHERE id=?", (target_user_id,)).fetchone()
                if target is not None and target["role"] == Role.ADMIN.value and target["status"] == AccountStatus.ACTIVE.value:
                    remaining = connection.execute(
                        "SELECT COUNT(*) AS count FROM users WHERE role=? AND status=? AND id<>?",
                        (Role.ADMIN.value, AccountStatus.ACTIVE.value, target_user_id),
                    ).fetchone()["count"]
                    if remaining == 0:
                        raise ValueError("cannot deactivate the last active administrator")
        allowed = {
            AccountStatus.ACTIVE,
            AccountStatus.DISABLED,
            AccountStatus.LOCKED,
            AccountStatus.REJECTED,
        }
        if status not in allowed:
            raise ValueError("unsupported administrative status transition")
        now = datetime.now(timezone.utc).isoformat()
        with self.accounts._connect() as connection:
            row = connection.execute("SELECT id FROM users WHERE id=?", (target_user_id,)).fetchone()
            if row is None:
                raise LookupError("target user not found")
            connection.execute(
                "UPDATE users SET status=?,updated_at=? WHERE id=?",
                (status.value, now, target_user_id),
            )
        if status is not AccountStatus.ACTIVE:
            self.sessions.revoke_all(target_user_id)

    def approve(self, actor: UserAccount, target_user_id: int) -> None:
        require_admin(actor)
        with self.accounts._connect() as connection:
            row = connection.execute("SELECT status FROM users WHERE id=?", (target_user_id,)).fetchone()
        if row is None:
            raise LookupError("target user not found")
        if row["status"] != AccountStatus.PENDING_APPROVAL.value:
            raise ValueError("only pending accounts can be approved")
        self.set_status(actor, target_user_id, AccountStatus.ACTIVE)

    def reject(self, actor: UserAccount, target_user_id: int) -> None:
        require_admin(actor)
        with self.accounts._connect() as connection:
            row = connection.execute("SELECT status FROM users WHERE id=?", (target_user_id,)).fetchone()
        if row is None:
            raise LookupError("target user not found")
        if row["status"] != AccountStatus.PENDING_APPROVAL.value:
            raise ValueError("only pending accounts can be rejected")
        self.set_status(actor, target_user_id, AccountStatus.REJECTED)

    def set_role(self, actor: UserAccount, target_user_id: int, role: Role) -> None:
        require_admin(actor)
        if actor.user_id == target_user_id and role is not Role.ADMIN:
            raise ValueError("administrator cannot remove own administrator role")
        if role is not Role.ADMIN:
            with self.accounts._connect() as connection:
                target = connection.execute("SELECT role,status FROM users WHERE id=?", (target_user_id,)).fetchone()
                if target is not None and target["role"] == Role.ADMIN.value and target["status"] == AccountStatus.ACTIVE.value:
                    remaining = connection.execute(
                        "SELECT COUNT(*) AS count FROM users WHERE role=? AND status=? AND id<>?",
                        (Role.ADMIN.value, AccountStatus.ACTIVE.value, target_user_id),
                    ).fetchone()["count"]
                    if remaining == 0:
                        raise ValueError("cannot demote the last active administrator")
        now = datetime.now(timezone.utc).isoformat()
        with self.accounts._connect() as connection:
            row = connection.execute("SELECT id FROM users WHERE id=?", (target_user_id,)).fetchone()
            if row is None:
                raise LookupError("target user not found")
            connection.execute(
                "UPDATE users SET role=?,updated_at=? WHERE id=?",
                (role.value, now, target_user_id),
            )
        self.sessions.revoke_all(target_user_id)

    def enable(self, actor: UserAccount, target_user_id: int) -> None:
        require_admin(actor)
        with self.accounts._connect() as connection:
            row = connection.execute("SELECT status FROM users WHERE id=?", (target_user_id,)).fetchone()
        if row is None:
            raise LookupError("target user not found")
        if row["status"] != AccountStatus.DISABLED.value:
            raise ValueError("only disabled accounts can be enabled")
        self.set_status(actor, target_user_id, AccountStatus.ACTIVE)

    def unlock(self, actor: UserAccount, target_user_id: int) -> None:
        require_admin(actor)
        with self.accounts._connect() as connection:
            row = connection.execute("SELECT status FROM users WHERE id=?", (target_user_id,)).fetchone()
        if row is None:
            raise LookupError("target user not found")
        if row["status"] != AccountStatus.LOCKED.value:
            raise ValueError("only locked accounts can be unlocked")
        self.set_status(actor, target_user_id, AccountStatus.ACTIVE)

    def require_password_change(self, actor: UserAccount, target_user_id: int) -> None:
        require_admin(actor)
        if actor.user_id == target_user_id:
            raise ValueError("administrator must change own password through the password-change flow")
        now = datetime.now(timezone.utc).isoformat()
        with self.accounts._connect() as connection:
            row = connection.execute(
                "SELECT id,status FROM users WHERE id=?", (target_user_id,)
            ).fetchone()
            if row is None:
                raise LookupError("target user not found")
            if row["status"] != AccountStatus.ACTIVE.value:
                raise ValueError("password change can only be required for an active account")
            connection.execute(
                "UPDATE users SET must_change_password=1,updated_at=? WHERE id=?",
                (now, target_user_id),
            )
        self.sessions.revoke_all(target_user_id)
