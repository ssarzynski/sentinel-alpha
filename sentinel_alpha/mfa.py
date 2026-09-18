"""Mandatory TOTP second factor for administrator accounts."""

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pyotp

from .auth import Role, UserAccount
from .security_audit import SecurityAuditLog


@dataclass(frozen=True)
class MfaEnrollment:
    secret: str
    provisioning_uri: str


class AdminMfaStore:
    def __init__(self, database: str | Path, audit: SecurityAuditLog) -> None:
        self.database = str(database)
        self.audit = audit
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS admin_mfa (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    totp_secret TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0
                )"""
            )

    def begin_enrollment(self, account: UserAccount) -> MfaEnrollment:
        if account.role is not Role.ADMIN:
            raise PermissionError("administrator role required")
        secret = pyotp.random_base32()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO admin_mfa(user_id,totp_secret,enabled) VALUES(?,?,0)
                ON CONFLICT(user_id) DO UPDATE SET totp_secret=excluded.totp_secret,enabled=0""",
                (account.user_id, secret),
            )
        issuer = os.getenv("SENTINEL_MFA_ISSUER", "Sentinel Alpha")
        return MfaEnrollment(secret, pyotp.TOTP(secret).provisioning_uri(account.username, issuer))

    def confirm_enrollment(self, account: UserAccount, code: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT totp_secret FROM admin_mfa WHERE user_id=?", (account.user_id,)
            ).fetchone()
            if row is None or not pyotp.TOTP(row["totp_secret"]).verify(code, valid_window=1):
                self.audit.append("MFA_ENROLLMENT_FAILED", success=False, actor_user_id=account.user_id)
                return False
            connection.execute("UPDATE admin_mfa SET enabled=1 WHERE user_id=?", (account.user_id,))
        self.audit.append("MFA_ENABLED", success=True, actor_user_id=account.user_id)
        return True

    def verify(self, account: UserAccount, code: str) -> bool:
        if account.role is not Role.ADMIN:
            return True
        with self._connect() as connection:
            row = connection.execute(
                "SELECT totp_secret,enabled FROM admin_mfa WHERE user_id=?", (account.user_id,)
            ).fetchone()
        if row is None or not row["enabled"]:
            return False
        valid = pyotp.TOTP(row["totp_secret"]).verify(code, valid_window=1)
        self.audit.append(
            "MFA_CHALLENGE", success=valid, actor_user_id=account.user_id,
            metadata={"factor": "totp"},
        )
        return valid

    def enabled(self, account: UserAccount) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT enabled FROM admin_mfa WHERE user_id=?", (account.user_id,)
            ).fetchone()
        return bool(row and row["enabled"])
