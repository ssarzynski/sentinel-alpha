"""Authentication account model and deny-by-default authorization foundation."""

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path


class Role(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class AccountStatus(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class UserAccount:
    user_id: int
    username: str
    role: Role
    status: AccountStatus
    must_change_password: bool
    password_expires_at: str


def normalize_username(username: str) -> str:
    value = username.strip().casefold()
    if not 3 <= len(value) <= 64 or not all(c.isalnum() or c in "._-" for c in value):
        raise ValueError("invalid username")
    return value


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Memory-hard stdlib foundation; Argon2id migration follows."""
    if len(password) < 12:
        raise ValueError("password must contain at least 12 characters")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=32
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class AccountStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS password_policy (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    expiration_days INTEGER NOT NULL CHECK(expiration_days IN (30, 60, 90)),
                    updated_at TEXT NOT NULL,
                    updated_by INTEGER
                )"""
            )
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "INSERT OR IGNORE INTO password_policy(id, expiration_days, updated_at) VALUES(1,90,?)",
                (now,),
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('ADMIN','USER')),
                    status TEXT NOT NULL CHECK(status IN
                      ('PENDING_APPROVAL','ACTIVE','DISABLED','LOCKED','REJECTED')),
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    password_changed_at TEXT NOT NULL,
                    password_expires_at TEXT NOT NULL,
                    failed_login_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )

    def create_user(
        self, username: str, password: str, *, role: Role = Role.USER,
        status: AccountStatus = AccountStatus.PENDING_APPROVAL,
        must_change_password: bool = False,
    ) -> int:
        normalized = normalize_username(username)
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            days = connection.execute(
                "SELECT expiration_days FROM password_policy WHERE id=1"
            ).fetchone()[0]
            cursor = connection.execute(
                """INSERT INTO users
                (username,password_hash,role,status,must_change_password,password_changed_at,
                 password_expires_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (normalized, hash_password(password), role.value, status.value,
                 int(must_change_password), now.isoformat(),
                 (now + timedelta(days=days)).isoformat(), now.isoformat(), now.isoformat()),
            )
            return int(cursor.lastrowid)

    def authenticate(self, username: str, password: str) -> UserAccount | None:
        try:
            normalized = normalize_username(username)
        except ValueError:
            return None
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE username=?", (normalized,)).fetchone()
            if row is None or not verify_password(password, row["password_hash"]):
                if row is not None:
                    connection.execute(
                        "UPDATE users SET failed_login_count=failed_login_count+1 WHERE id=?",
                        (row["id"],),
                    )
                return None
            if row["status"] != AccountStatus.ACTIVE.value:
                return None
            connection.execute("UPDATE users SET failed_login_count=0 WHERE id=?", (row["id"],))
            return UserAccount(
                row["id"], row["username"], Role(row["role"]), AccountStatus(row["status"]),
                bool(row["must_change_password"]), row["password_expires_at"]
            )


def require_admin(account: UserAccount) -> None:
    if account.status is not AccountStatus.ACTIVE or account.role is not Role.ADMIN:
        raise PermissionError("administrator authorization required")
