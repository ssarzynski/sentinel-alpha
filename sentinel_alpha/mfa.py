"""Mandatory TOTP second factor for administrator accounts."""

import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pyotp
from cryptography.fernet import Fernet, InvalidToken

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
        key = os.getenv("SENTINEL_MFA_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("SENTINEL_MFA_ENCRYPTION_KEY is required for administrator MFA")
        try:
            self.cipher = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise RuntimeError("SENTINEL_MFA_ENCRYPTION_KEY is invalid") from exc
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
            connection.execute(
                """CREATE TABLE IF NOT EXISTS admin_mfa_recovery (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    code_hash TEXT NOT NULL,
                    used_at TEXT,
                    PRIMARY KEY(user_id, code_hash)
                )"""
            )

    def generate_recovery_codes(self, account: UserAccount, count: int = 8) -> list[str]:
        if account.role is not Role.ADMIN or not self.enabled(account):
            raise PermissionError("enabled administrator MFA required")
        codes = [secrets.token_hex(16) for _ in range(count)]
        hashes = [hashlib.sha256(code.encode()).hexdigest() for code in codes]
        with self._connect() as connection:
            connection.execute("DELETE FROM admin_mfa_recovery WHERE user_id=?", (account.user_id,))
            connection.executemany(
                "INSERT INTO admin_mfa_recovery(user_id,code_hash) VALUES(?,?)",
                [(account.user_id, value) for value in hashes],
            )
        self.audit.append("MFA_RECOVERY_CODES_GENERATED", success=True, actor_user_id=account.user_id)
        return codes

    def verify_recovery_code(self, account: UserAccount, code: str) -> bool:
        if account.role is not Role.ADMIN or not self.enabled(account):
            return False
        from datetime import datetime, timezone
        digest = hashlib.sha256(code.encode()).hexdigest()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE admin_mfa_recovery SET used_at=? WHERE user_id=? AND code_hash=? AND used_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), account.user_id, digest),
            )
            valid = cursor.rowcount == 1
        self.audit.append("MFA_RECOVERY_CHALLENGE", success=valid, actor_user_id=account.user_id)
        return valid

    def begin_enrollment(self, account: UserAccount) -> MfaEnrollment:
        if account.role is not Role.ADMIN:
            raise PermissionError("administrator role required")
        secret = pyotp.random_base32()
        with self._connect() as connection:
            connection.execute("DELETE FROM admin_mfa_recovery WHERE user_id=?", (account.user_id,))
            connection.execute(
                """INSERT INTO admin_mfa(user_id,totp_secret,enabled) VALUES(?,?,0)
                ON CONFLICT(user_id) DO UPDATE SET totp_secret=excluded.totp_secret,enabled=0""",
                (account.user_id, self.cipher.encrypt(secret.encode()).decode()),
            )
        issuer = os.getenv("SENTINEL_MFA_ISSUER", "Sentinel Alpha")
        return MfaEnrollment(secret, pyotp.TOTP(secret).provisioning_uri(account.username, issuer))

    def confirm_enrollment(self, account: UserAccount, code: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT totp_secret FROM admin_mfa WHERE user_id=?", (account.user_id,)
            ).fetchone()
            if row is None:
                self.audit.append("MFA_ENROLLMENT_FAILED", success=False, actor_user_id=account.user_id)
                return False
            try:
                secret = self.cipher.decrypt(row["totp_secret"].encode()).decode()
            except InvalidToken:
                self.audit.append("MFA_SECRET_DECRYPT_FAILED", success=False, actor_user_id=account.user_id)
                return False
            if not pyotp.TOTP(secret).verify(code, valid_window=1):
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
        try:
            secret = self.cipher.decrypt(row["totp_secret"].encode()).decode()
        except InvalidToken:
            self.audit.append("MFA_SECRET_DECRYPT_FAILED", success=False, actor_user_id=account.user_id)
            return False
        valid = pyotp.TOTP(secret).verify(code, valid_window=1)
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
