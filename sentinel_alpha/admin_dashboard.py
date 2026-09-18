"""Read models for the protected administrator dashboard."""

from collections import Counter
from dataclasses import asdict

from .admin_accounts import AdminAccountService
from .auth import AccountStatus, AccountStore, UserAccount, require_admin
from .security_audit import SecurityAuditLog
from .sessions import SessionStore


class AdminDashboardService:
    def __init__(
        self, accounts: AccountStore, sessions: SessionStore, audit: SecurityAuditLog
    ) -> None:
        self.accounts = accounts
        self.sessions = sessions
        self.audit = audit

    def summary(self, actor: UserAccount) -> dict:
        require_admin(actor)
        users = AdminAccountService(self.accounts, self.sessions).list_users(actor)
        status_counts = Counter(item.status.value for item in users)
        recent = self.audit.recent(25)
        failures = sum(not event.success for event in recent)
        return {
            "users_total": len(users),
            "pending_accounts": status_counts[AccountStatus.PENDING_APPROVAL.value],
            "active_users": status_counts[AccountStatus.ACTIVE.value],
            "locked_users": status_counts[AccountStatus.LOCKED.value],
            "disabled_users": status_counts[AccountStatus.DISABLED.value],
            "recent_security_failures": failures,
            "audit_integrity": self.audit.verify_integrity(),
        }

    def security_events(self, actor: UserAccount, limit: int = 50) -> list[dict]:
        require_admin(actor)
        return [asdict(event) for event in self.audit.recent(limit)]
