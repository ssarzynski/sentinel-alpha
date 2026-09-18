"""Server-managed authentication sessions with restricted password-change state."""

import hashlib
import os
import secrets
import urllib.error
import urllib.request
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .auth import AccountStatus, AccountStore, Role, UserAccount, hash_password, verify_password


def compromised_password_count(password: str) -> int | None:
    """Return HIBP prevalence count using k-anonymity, or None when unavailable."""
    if os.getenv("SENTINEL_PWNED_PASSWORDS_CHECK", "enabled").casefold() != "enabled":
        return None
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    request = urllib.request.Request(
        f"https://api.pwnedpasswords.com/range/{prefix}",
        headers={"User-Agent": "Sentinel-Alpha/0.1", "Add-Padding": "true"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            body = response.read().decode("utf-8")
    except (OSError, urllib.error.URLError, UnicodeError):
        return None
    for line in body.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.upper() == suffix:
            try:
                return int(count)
            except ValueError:
                return None
    return 0



@dataclass(frozen=True)
class Session:
    token: str
    user_id: int
    restricted_to_password_change: bool
    mfa_verified: bool
    expires_at: str


class SessionStore:
    def __init__(
        self, database: str | Path, *, idle_minutes: int = 30, absolute_hours: int = 12
    ) -> None:
        self.database = str(database)
        self.idle_minutes = idle_minutes
        self.absolute_hours = absolute_hours
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS auth_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_hash TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    restricted_to_password_change INTEGER NOT NULL,
                    mfa_verified INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )"""
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(auth_sessions)")}
            if "mfa_verified" not in columns:
                connection.execute(
                    "ALTER TABLE auth_sessions ADD COLUMN mfa_verified INTEGER NOT NULL DEFAULT 0"
                )

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, account: UserAccount) -> Session:
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        expires = now + timedelta(hours=self.absolute_hours)
        restricted = account.must_change_password or datetime.fromisoformat(
            account.password_expires_at
        ) <= now
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO auth_sessions
                (token_hash,user_id,created_at,last_seen_at,expires_at,restricted_to_password_change)
                VALUES(?,?,?,?,?,?)""",
                (self._digest(token), account.user_id, now.isoformat(), now.isoformat(),
                 expires.isoformat(), int(restricted)),
            )
        return Session(token, account.user_id, restricted, False, expires.isoformat())

    def validate(self, token: str, *, allow_password_change_only: bool = False) -> UserAccount | None:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            row = connection.execute(
                """SELECT s.*,u.username,u.role,u.status,u.must_change_password,u.password_expires_at
                FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?""",
                (self._digest(token),),
            ).fetchone()
            if row is None or row["revoked_at"] is not None:
                return None
            if row["status"] != AccountStatus.ACTIVE.value:
                return None
            if datetime.fromisoformat(row["expires_at"]) <= now:
                return None
            if datetime.fromisoformat(row["last_seen_at"]) + timedelta(minutes=self.idle_minutes) <= now:
                return None
            restricted = bool(row["restricted_to_password_change"])
            if restricted and not allow_password_change_only:
                return None
            connection.execute(
                "UPDATE auth_sessions SET last_seen_at=? WHERE id=?", (now.isoformat(), row["id"])
            )
            return UserAccount(
                row["user_id"], row["username"], Role(row["role"]), AccountStatus(row["status"]),
                bool(row["must_change_password"]), row["password_expires_at"]
            )

    def mark_mfa_verified(self, token: str, user_id: int) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE auth_sessions SET mfa_verified=1
                WHERE token_hash=? AND user_id=? AND revoked_at IS NULL""",
                (self._digest(token), user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("active session not found")

    def mfa_verified(self, token: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT mfa_verified FROM auth_sessions
                WHERE token_hash=? AND revoked_at IS NULL""",
                (self._digest(token),),
            ).fetchone()
        return bool(row and row["mfa_verified"])

    def active_sessions(self, user_id: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id,created_at,last_seen_at,expires_at,mfa_verified
                FROM auth_sessions WHERE user_id=? AND revoked_at IS NULL AND expires_at>? 
                ORDER BY created_at DESC""",
                (user_id, now.isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]

    def revoke_all_in_connection(self, connection: sqlite3.Connection, user_id: int) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "UPDATE auth_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
            (now, user_id),
        )
        return cursor.rowcount

    def revoke_all(self, user_id: int) -> int:
        with self._connect() as connection:
            return self.revoke_all_in_connection(connection, user_id)


def change_password(
    accounts: AccountStore,
    sessions: SessionStore,
    *,
    account: UserAccount,
    current_password: str,
    new_password: str,
) -> None:
    with accounts._connect() as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE id=?", (account.user_id,)).fetchone()
        if row is None or not verify_password(current_password, row["password_hash"]):
            raise ValueError("current password is invalid")
        previous_hashes = [row["password_hash"] for row in connection.execute(
            """SELECT password_hash FROM password_history
            WHERE user_id=? ORDER BY created_at DESC, id DESC LIMIT 4""",
            (account.user_id,),
        ).fetchall()]
        if verify_password(new_password, row["password_hash"]) or any(
            verify_password(new_password, previous) for previous in previous_hashes
        ):
            raise ValueError("new password was recently used")
        compromised_count = compromised_password_count(new_password)
        if compromised_count is not None and compromised_count > 0:
            raise ValueError("new password is known to be compromised")
        days = connection.execute(
            "SELECT expiration_days FROM password_policy WHERE id=1"
        ).fetchone()[0]
        now = datetime.now(timezone.utc)
        new_hash = hash_password(new_password)
        connection.execute(
            "INSERT INTO password_history(user_id,password_hash,created_at) VALUES(?,?,?)",
            (account.user_id, row["password_hash"], now.isoformat()),
        )
        connection.execute(
            """DELETE FROM password_history WHERE user_id=? AND id NOT IN (
                SELECT id FROM password_history WHERE user_id=?
                ORDER BY created_at DESC, id DESC LIMIT 4
            )""",
            (account.user_id, account.user_id),
        )
        connection.execute(
            """UPDATE users SET password_hash=?,must_change_password=0,password_changed_at=?,
            password_expires_at=?,updated_at=? WHERE id=?""",
            (new_hash, now.isoformat(), (now + timedelta(days=days)).isoformat(),
             now.isoformat(), account.user_id),
        )
    sessions.revoke_all(account.user_id)
