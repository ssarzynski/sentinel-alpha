"""Authentication service with generic failures, audit events and brute-force backoff."""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .auth import AccountStore, normalize_username
from .security_audit import SecurityAuditLog
from .sessions import Session, SessionStore


@dataclass(frozen=True)
class LoginResult:
    session: Session | None
    retry_after_seconds: int = 0


class AuthenticationService:
    def __init__(
        self,
        accounts: AccountStore,
        sessions: SessionStore,
        audit: SecurityAuditLog,
        *,
        max_failures: int = 5,
        lock_minutes: int = 15,
    ) -> None:
        self.accounts = accounts
        self.sessions = sessions
        self.audit = audit
        self.max_failures = max_failures
        self.lock_minutes = lock_minutes
        self._initialize()

    def _initialize(self) -> None:
        with self.accounts._connect() as connection:
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "login_blocked_until" not in columns:
                connection.execute("ALTER TABLE users ADD COLUMN login_blocked_until TEXT")

    @staticmethod
    def _source_fingerprint(source: str | None) -> str | None:
        if not source:
            return None
        return hashlib.sha256(source.encode()).hexdigest()[:16]

    def login(
        self, username: str, password: str, *, source: str | None = None, request_id: str | None = None
    ) -> LoginResult:
        try:
            normalized = normalize_username(username)
        except ValueError:
            normalized = ""
        now = datetime.now(timezone.utc)
        with self.accounts._connect() as connection:
            row = connection.execute(
                "SELECT id,failed_login_count,login_blocked_until FROM users WHERE username=?",
                (normalized,),
            ).fetchone()
        metadata = {}
        fingerprint = self._source_fingerprint(source)
        if fingerprint:
            metadata["source_fingerprint"] = fingerprint
        if row is not None and row["login_blocked_until"]:
            blocked_until = datetime.fromisoformat(row["login_blocked_until"])
            if blocked_until > now:
                retry = max(1, int((blocked_until - now).total_seconds()))
                self.audit.append(
                    "LOGIN_FAILURE", success=False, target_user_id=row["id"],
                    request_id=request_id, metadata={**metadata, "reason": "temporarily_blocked"},
                )
                return LoginResult(None, retry)

        account = self.accounts.authenticate(username, password)
        if account is None:
            if row is not None:
                failures = int(row["failed_login_count"]) + 1
                if failures >= self.max_failures:
                    blocked_until = now + timedelta(minutes=self.lock_minutes)
                    with self.accounts._connect() as connection:
                        connection.execute(
                            "UPDATE users SET login_blocked_until=? WHERE id=?",
                            (blocked_until.isoformat(), row["id"]),
                        )
            self.audit.append(
                "LOGIN_FAILURE", success=False,
                target_user_id=row["id"] if row else None,
                request_id=request_id, metadata={**metadata, "reason": "invalid_credentials"},
            )
            return LoginResult(None)

        with self.accounts._connect() as connection:
            connection.execute(
                "UPDATE users SET login_blocked_until=NULL,failed_login_count=0 WHERE id=?",
                (account.user_id,),
            )
        session = self.sessions.create(account)
        self.audit.append(
            "LOGIN_SUCCESS", success=True, actor_user_id=account.user_id,
            request_id=request_id, metadata=metadata or None,
        )
        return LoginResult(session)

    def logout(self, token: str, account_id: int | None = None) -> None:
        # Revocation is server-side; callers resolve account_id before discarding the session.
        if account_id is not None:
            self.sessions.revoke_all(account_id)
        self.audit.append("LOGOUT", success=True, actor_user_id=account_id)
